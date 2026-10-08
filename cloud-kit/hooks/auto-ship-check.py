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
                      r"|(^|/)(docs|tasks|handoffs)/[^\0]*\.md$", re.I)
NOT_DOCS = re.compile(r"(^|/)(skills|rules|commands|agents|prompts|hooks|\.claude)/|(^|/)(SKILL|CLAUDE|AGENTS|GEMINI)\.md$", re.I)
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


def is_doc(path):
    return bool(DOC_FILE.search(path)) and not NOT_DOCS.search(path)


REPO_ARG = re.compile(r"(?:\b(?:cd|pushd)|\s-C|--git-dir=?|--work-tree=?|\bGIT_(?:DIR|WORK_TREE)=)\s*(\S+)")


def repos_touched(cwd, cmds):
    """Directories the turn's commands moved into (cd / git -C / --git-dir / --work-tree), plus cwd.
    Returns None if one can't be resolved (variables, subshell tricks), meaning: assume code."""
    dirs = {cwd} if cwd else set()
    for cmd in cmds:
        for raw in REPO_ARG.findall(cmd):
            raw = raw.rstrip(";&|)")
            if "$" in raw or "`" in raw or not raw or raw == "''":
                return None
            d = os.path.expanduser(raw)
            d = d if os.path.isabs(d) else os.path.join(cwd or "", d)
            d = os.path.normpath(d[:-5] if d.endswith("/.git") else d)
            if not os.path.isdir(d):
                return None
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


def commits_docs_only(cwd, ts, pred=is_doc):
    """True if every commit in cwd's repo since the prompt touches only doc files; None if that repo
    has no commits since the prompt; False otherwise (or on any doubt)."""
    if not cwd or not ts:
        return False
    try:
        since = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
        out = subprocess.run(["git", "-C", cwd, "log", "--date-order", f"--since={since}", "-m", "--no-renames",
                              "--name-only", "-z", "--format=", "HEAD"],
                             capture_output=True, text=True, timeout=3)
        if out.returncode != 0:
            return False
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
                if fp and not fp.startswith(SKIP_PREFIXES) and not is_doc(fp):
                    changed = True
                    prose = prose and is_prose(fp)
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


try:
    main()
except Exception:
    sys.exit(0)
