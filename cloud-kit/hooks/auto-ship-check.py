#!/usr/bin/env python3
"""Stop hook: work that changed code must be ship-checked before the turn ends.

Since the last real (human) user prompt, if the assistant edited code (Edit/Write/NotebookEdit
outside ~/.claude, /tmp and the scratchpad), ran `git commit` / `gh pr create`, or a commit
landed in the session's repo during a turn that ran sub-agents (their edits live in their own transcripts),
and has not invoked ship-check AFTER the first such change, block the stop once and tell it
to run /ship-check. Allows the stop when the hook already fired this cycle (stop_hook_active)
or when the prompt itself was /ship-check. Founder 2026-10-01: "every single time you do some
sort of work I want you to ship check it". Silent on any error.

Docs-only work never triggers it: edits to .md/.mdx/.txt/.rst files (handoffs, notes,
progress files) and commits whose files are all docs are ignored. Founder 2026-10-01: the
hook re-prompted after a turn that only saved keys and updated a handoff file.

Prose-only work (every changed file is .md — rules, skills, agent files, commands) still
blocks, but asks for the LIGHT check only: confirm on main, run the repo's sync/manifest check,
one-line report. Founder 2026-10-08: a full ship-check for a 2-line rules edit was waste.

Knowledge repos (unleashed-memory, matched by origin URL or repo name, worktrees included) are
docs repos: .md/.mdx/.pdf under wiki/ or docs/, the root index/log/README.md and any non-code file
under raw/ count as docs (the repo's bin/, supabase/ and prompts stay code), so a research note
committed from a scratchpad worktree never blocks. Founder 2026-10-09. Such a commit is checked by
the sha the command printed (`[branch sha]`, or `git log -1 --format=%h` after `commit -q`), looked
up in the touched repos and the knowledge repos, so it survives `cd "$W"` paths and a worktree
removed before the turn ends. Each sha must be new since the prompt, its subject must appear in the
command, and the command must not loop or wrap git in another shell; otherwise the time-window
check below is the fallback. PDFs are docs in every repo.

Known gap: sub-agent edits that are neither committed in the session cwd's repo nor made by
this transcript (e.g. uncommitted work in another worktree) are not seen.
"""
import json, os, re, subprocess, sys
from datetime import datetime

HOME = os.path.expanduser("~")
SKIP_PREFIXES = (f"{HOME}/.claude/", "/tmp/", "/private/tmp/", "/var/folders/")
# Allowlist: only plain notes/handoffs/docs count as docs. Anything else (prompts, rules,
# skills, deployed content, dependency lists) is treated as code.
DOC_FILE = re.compile(r"(^|/)(README|CHANGELOG|HANDOFF|NOTES|TODO|PROGRESS|LESSONS)[^/]*\.(md|txt)$"
                      r"|(^|/)(docs|tasks|handoffs)/[^\0]*\.md$|\.pdf$", re.I)
NOT_DOCS = re.compile(r"(^|/)(skills|rules|commands|agents|prompts|hooks|\.claude)/|(^|/)(SKILL|CLAUDE|AGENTS|GEMINI)\.md$", re.I)
# Repos that are a knowledge base, not software: notes and raw research sources are docs there.
KNOWLEDGE_REPOS = {"unleashed-memory"}
KNOWLEDGE_PATHS = [f"{HOME}/Developer/{n}" for n in KNOWLEDGE_REPOS]
KNOWLEDGE_DOC = re.compile(r"^(wiki|docs)/[^\0]*\.(md|mdx|pdf)$|^(index|log|README)\.md$|^raw/", re.I)
KNOWLEDGE_NOT_DOCS = re.compile(r"(^|/)(skills|rules|commands|agents|prompts|hooks|\.claude|\.github)/"
                                r"|(^|/)(SKILL|CLAUDE|AGENTS|GEMINI)\.md$", re.I)
CODE_EXT = re.compile(r"\.(py|[cm]?[jt]sx?|sh|bash|zsh|rb|go|rs|swift|kt|java|sql|php|pl|lua|ya?ml|toml|ipynb)$", re.I)
COMMIT_SHA = re.compile(r"^\[[^\]\n]*?\s([0-9a-f]{7,40})\]", re.M)  # `git commit` summary line
BARE_SHA = re.compile(r"^([0-9a-f]{7,40})(?:[ \t].*)?$", re.M)  # `git log -1 --format='%h %s'`
PRINTS_HEAD = re.compile(r"\bgit\s+(?:log\s+[^|;&\n]*(?:-1|-n\s*1)\b[^|;&\n]*%[hH]|rev-parse\s+(?:--short\S*\s+)?HEAD\b)")
PERSISTED = re.compile(r"Full output saved to: (\S+)")
LOOPS = re.compile(r"\b(?:for|while|until|xargs)\b|\bfind\b.*\s-exec")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
GIT_CHANGE = re.compile(r"\bgit\s+(?:-[Cc]\s+\S+\s+|--(?:git-dir|work-tree|namespace)\s+\S+\s+|--[\w-]+(?:=\S+)?\s+)*commit\b|\bgh\s+pr\s+create\b")
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
# Commands that run a quoted string as shell code: bash -c "...", ssh host "...", eval "...", docker exec.
SHELL_WRAP = re.compile(r"\b(?:ba|z|da|k)?sh\s+(?:-\S+\s+)*-\w*c\b|\bssh\b|\beval\b|\bsu\b.*\s-c\b|\bdocker\s+exec\b")
SUBST = re.compile(r"\$\(|`")
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*\\?(['\"]?)([A-Za-z_]\w*)\1")
NOT_A_PROMPT = ("<task-notification", "<local-command", "[Request interrupted", "<system-reminder")
SHIP_CHECK_PROMPT = re.compile(r"^\s*/ship-check\b|<command-name>/?ship-check</command-name>")


def strip_heredocs(cmd):
    """Drop heredoc bodies (text fed to a command, never run by the shell itself)."""
    out, delim = [], None
    for line in cmd.splitlines():
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            delim = m.group(2)
    return "\n".join(out)


def runs_git_change(cmd):
    """True only if the shell itself runs git commit / gh pr create (not text in a heredoc or string)."""
    return bool(GIT_CHANGE.search(QUOTED.sub("''", strip_heredocs(cmd))))


def wrapped_git_change(cmd):
    """True if git commit / gh pr create runs inside a quoted string the shell executes
    (bash -c, ssh, eval, "$(...)"). Its repo can't be resolved, so it always counts as code."""
    cmd = strip_heredocs(cmd)
    wrapped = bool(SHELL_WRAP.search(QUOTED.sub("''", cmd)))
    for q in QUOTED.findall(cmd):
        if GIT_CHANGE.search(q[1:-1]) and (wrapped or (q[0] == '"' and SUBST.search(q))):
            return True
    return False


def is_real_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return not content.lstrip().startswith(NOT_A_PROMPT)
    if isinstance(content, list):
        blocks = [b for b in content if isinstance(b, dict)]
        if any(b.get("type") == "tool_result" for b in blocks):
            return False
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return any(t.strip() and not t.lstrip().startswith(NOT_A_PROMPT) for t in texts)
    return False


def prompt_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))


def is_doc(path, knowledge=False):
    """knowledge: path is relative to a knowledge repo's root (see KNOWLEDGE_REPOS)."""
    if knowledge and KNOWLEDGE_DOC.search(path) and not CODE_EXT.search(path) and not KNOWLEDGE_NOT_DOCS.search(path):
        return True
    return bool(DOC_FILE.search(path)) and not NOT_DOCS.search(path)


def git(d, *args):
    return subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, timeout=3)


_knowledge = {}


def is_knowledge_repo(d):
    """True if d is in a knowledge repo or one of its worktrees (by origin URL or main checkout name)."""
    if d not in _knowledge:
        try:
            url = git(d, "config", "--get", "remote.origin.url").stdout.strip().rstrip("/")
            common = git(d, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
            names = {re.sub(r"\.git$", "", re.split(r"[/:]", url)[-1]) if url else "",
                     os.path.basename(os.path.dirname(common)) if common else ""}
            _knowledge[d] = bool(names & KNOWLEDGE_REPOS)
        except Exception:
            _knowledge[d] = False
    return _knowledge[d]


def edit_is_doc(fp):
    """is_doc for an absolute file path, aware of knowledge repos."""
    if is_doc(fp):
        return True
    if CODE_EXT.search(fp) or not re.search(r"\.(md|mdx|pdf)$|/raw/", fp, re.I):
        return False  # can't be a knowledge-repo doc; skip the git lookups
    try:
        d = os.path.dirname(fp)
        while d and d != "/" and not os.path.isdir(d):
            d = os.path.dirname(d)
        top = git(d, "rev-parse", "--show-toplevel").stdout.strip()
        return bool(top) and is_knowledge_repo(top) and is_doc(
            os.path.relpath(os.path.realpath(fp), os.path.realpath(top)), True)
    except Exception:
        return False


def result_text(entries, tool_id):
    for e in entries:
        if e.get("type") != "user":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") == tool_id:
                c = b.get("content")
                text = c if isinstance(c, str) else "\n".join(
                    x.get("text", "") for x in c or [] if isinstance(x, dict))
                m = PERSISTED.search(text)  # large output is moved to a file; read its last 2 MB
                saved = os.path.realpath(m.group(1)) if m else ""
                if saved.startswith(os.path.realpath(f"{HOME}/.claude/projects") + "/") and os.path.isfile(saved):
                    try:
                        with open(saved, "rb") as f:
                            f.seek(max(0, os.path.getsize(saved) - 2_000_000))
                            text = f.read().decode(errors="ignore")
                    except OSError:
                        pass
                return text
    return ""


def commit_shas_docs_only(cmd, output, repos, ts):
    """True if the command's every git commit / gh pr create printed a commit sha (its `[branch sha]`
    line, or `git log -1 --format=%h` after `commit -q`), each sha exists in one of repos, was
    committed after the prompt (ts), has its subject in the command, and touches only docs.
    False on any doubt: loops, git run inside another shell, or a count mismatch."""
    shell = QUOTED.sub("''", strip_heredocs(cmd))
    if wrapped_git_change(cmd) or LOOPS.search(shell):
        return False
    shas = COMMIT_SHA.findall(output) or (BARE_SHA.findall(output) if PRINTS_HEAD.search(strip_heredocs(cmd)) else [])
    if not shas or len(shas) != len(GIT_CHANGE.findall(shell)):
        return False
    try:
        since = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        for sha in shas:
            for d in repos:
                full = git(d, "rev-parse", "--verify", "-q", sha + "^{commit}").stdout.strip()
                if full:
                    break
            else:
                return False
            when, _, subject = git(d, "show", "-s", "--format=%ct %s", full).stdout.strip().partition(" ")
            if int(when or 0) < since:
                return False  # an older commit (e.g. the push failed and log showed origin's tip)
            if len(subject) < 4 or subject not in cmd:
                return False  # the printed sha isn't the commit this command made
            out = git(d, "diff-tree", "--root", "--no-commit-id", "-r", "-m", "--name-only", "--no-renames", "-z", full)
            files = [f for f in out.stdout.split("\0") if f.strip()]
            if out.returncode or not files or not all(is_doc(f, is_knowledge_repo(d)) for f in files):
                return False
        return True
    except Exception:
        return False


REPO_ARG = re.compile(r"(?:\b(?:cd|pushd)|\s-C|--git-dir=?|--work-tree=?|\bGIT_(?:DIR|WORK_TREE)=)\s*(\S+)")


def repos_touched(cwd, cmds, strict=True):
    """Directories the turn's commands moved into (cd / git -C / --git-dir / --work-tree), plus cwd.
    Returns None if one can't be resolved (variables, subshell tricks), meaning: assume code.
    strict=False skips those instead (for looking commits up, never for proving their absence)."""
    dirs = {cwd} if cwd else set()
    for cmd in cmds:
        for raw in REPO_ARG.findall(cmd):
            raw = raw.rstrip(";&|)")
            if "$" in raw or "`" in raw or not raw or raw == "''":
                if strict:
                    return None
                continue
            d = os.path.expanduser(raw)
            d = d if os.path.isabs(d) else os.path.join(cwd or "", d)
            d = os.path.normpath(d[:-5] if d.endswith("/.git") else d)
            if not os.path.isdir(d):
                if strict:
                    return None
                continue
            dirs.add(d)
    return dirs


def all_commits_docs_only(dirs, ts):
    """True if every touched repo's commits since the prompt are docs-only and at least one exists."""
    seen = False
    for d in dirs:
        r = commits_docs_only(d, ts)
        if r is False:
            return False
        seen = seen or r is True
    return seen


def is_prose(path):
    # .txt is excluded: requirements.txt, CMakeLists.txt and prompt files are behaviour.
    return path.lower().endswith((".md", ".mdx"))


def commits_docs_only(cwd, ts, pred=None):
    """True if every commit in cwd's repo since the prompt touches only doc files; None if that repo
    has no commits since the prompt (or cwd is not a repo); False otherwise (or on any doubt)."""
    if not cwd or not ts:
        return False
    try:
        since = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
        out = subprocess.run(["git", "-C", cwd, "log", "--date-order", f"--since={since}", "-m", "--no-renames",
                              "--name-only", "-z", "--format=", "HEAD"],
                             capture_output=True, text=True, timeout=3)
        if out.returncode != 0:
            return None if "not a git repository" in out.stderr else False
        if pred is None:
            knowledge = is_knowledge_repo(cwd)
            pred = lambda f: is_doc(f, knowledge)
        files = [f.strip() for f in out.stdout.split("\0") if f.strip()]
        if not files:
            return None
        return all(pred(f) for f in files)
    except Exception:
        return False


def committed_since(cwd, ts):
    """True if the repo at cwd has a commit newer than the prompt timestamp (ISO 8601)."""
    if not cwd or not ts:
        return False
    try:
        since = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        out = subprocess.run(["git", "-C", cwd, "log", "-1", "--format=%ct"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        return bool(out) and int(out) > since
    except Exception:
        return False


def main():
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return
    path = payload.get("transcript_path") or ""
    if not os.path.exists(path):
        return
    with open(path, errors="ignore") as f:
        lines = f.readlines()
    # Walk back to the last real prompt; only the tail gets parsed.
    tail, start = [], None
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if is_real_prompt(e):
            start = e
            break
        tail.append(e)
    if start is None:
        return
    if SHIP_CHECK_PROMPT.search(prompt_text(start)):
        return
    tail.reverse()
    failed = {b.get("tool_use_id") for e in tail if e.get("type") == "user"
              for b in ((e.get("message") or {}).get("content") or [])
              if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error")}
    changed = shipped = delegated = False
    prose = True  # every changed file so far is prose (.md/.txt)
    cwd = payload.get("cwd")
    docs_only = None  # computed once, on the first commit seen
    bash_cmds = [QUOTED.sub("''", strip_heredocs(str((b.get("input") or {}).get("command", ""))))
                 for e in tail if e.get("type") == "assistant"
                 for b in (e.get("message") or {}).get("content") or []
                 if isinstance(b, dict) and b.get("name") == "Bash"]
    # where a printed commit sha is looked up: touched repos first, then the knowledge repos
    seen_repos = sorted(repos_touched(cwd, bash_cmds, strict=False))
    lookup_repos = seen_repos + KNOWLEDGE_PATHS
    for e in tail:
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            if name in ("Agent", "Task"):
                delegated = True
            if name in ("Skill", "SlashCommand") and "ship-check" in str(inp.get("skill") or inp.get("command") or ""):
                if changed:
                    return
                shipped = True
            elif b.get("id") in failed:
                continue
            elif name in EDIT_TOOLS:
                fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
                if fp and not fp.startswith(SKIP_PREFIXES) and not edit_is_doc(fp):
                    changed = True
                    prose = prose and is_prose(fp)
            elif name == "Bash" and GIT_CHANGE.search(str(inp.get("command", ""))) and commit_shas_docs_only(
                    str(inp.get("command", "")), result_text(tail, b.get("id")), lookup_repos,
                    start.get("timestamp") or "") and all(
                    commits_docs_only(d, start.get("timestamp")) is not False for d in seen_repos):
                continue  # and no code commit (an alias, a quiet one) landed in a repo this turn moved into
            elif name == "Bash" and wrapped_git_change(str(inp.get("command", ""))):
                changed = True
                prose = False
            elif name == "Bash" and runs_git_change(str(inp.get("command", ""))):
                if docs_only is None:
                    dirs = repos_touched(cwd, bash_cmds)
                    docs_only = dirs is not None and all_commits_docs_only(dirs, start.get("timestamp"))
                if not docs_only:
                    changed = True
                    prose = prose and dirs is not None and all(
                        commits_docs_only(d, start.get("timestamp"), is_prose) is not False for d in dirs)
    if not changed and not shipped and delegated and docs_only is None:
        changed = committed_since(cwd, start.get("timestamp")) and commits_docs_only(cwd, start.get("timestamp")) is not True
        prose = prose and commits_docs_only(cwd, start.get("timestamp"), is_prose) is True
    elif delegated and changed and prose and committed_since(cwd, start.get("timestamp")):
        # a sub-agent may have committed code next to this turn's .md edits
        prose = commits_docs_only(cwd, start.get("timestamp"), is_prose) is True
    if changed and prose:
        print(json.dumps({
            "decision": "block",
            "reason": "[auto-ship-check] Prose-only change (.md rules/skills/agents). Run the LIGHT check, not "
                      "the full /ship-check: confirm the commit is on origin/main, run the repo's sync/manifest "
                      "check if it has one, then report in one or two lines.",
        }))
    elif changed:
        print(json.dumps({
            "decision": "block",
            "reason": "[auto-ship-check] Code changed this turn and /ship-check has not run. "
                      "Run the ship-check skill now (it includes red-team), then end with the "
                      "Done / Remaining / Heads-up / Proof / Needs you summary (short by default, no line cap; omit nothing important).",
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
