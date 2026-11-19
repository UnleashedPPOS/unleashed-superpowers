#!/usr/bin/env python3
"""PreToolUse + PostToolUse hook: a prompt or model change ships with its eval score (council audit 2026-11-16).

Rule (skill llm-provider-chain, "Catalogue: eval per repo"): when a commit or PR in one of the product
repos listed in eval-gate.json changes an LLM prompt or a model choice, that repo's matching eval runs
first, and the PR body carries the score. The cloud runs the offline eval; a machine with `vault`
runs the live one too.

  PostToolUse Bash      a command matching an eval's `ran` regex is recorded in the state file
                        (EVAL_GATE_STATE, default ~/.claude/state/eval-gate.json) with the output tail.
  PreToolUse git commit the files about to be committed (staged; plus unstaged/untracked when the
                        command also runs `git add` or `commit -a`) are scanned. A prompt/model change
                        with no passing run of its eval since the files last changed gets a warning; the commit is never
                        blocked (the hard requirement is at PR time). Only a real `git commit` counts, not a
                        mention in echo/grep/log, and not commit-tree.
  PreToolUse PR create  `gh pr create` or a GitHub MCP create_pull_request: the branch diff against
                        its base is scanned the same way, and the body must carry one score line per
                        eval ("Eval (inbox-triage, offline): 47/50") or "Eval: none" with a reason
                        when no eval covers the change, or "Eval: skipped: <why>" when it could not run.
                        A failed or missing run blocks the PR.

What counts as a prompt or model change:
  - a changed path under a prompt location (prompts/ dirs, *_prompt.py, system_prompt files) or inside
    a registered eval's `paths` (which includes the eval's golden data), or
  - an added or removed line, outside tests and docs, with a model id, a model assignment or a prompt
    string (SYSTEM_PROMPT, role "system", "You are a ...").
  - a code file that builds a system prompt (an edit in the middle of a prompt string has no marker).

An eval "ran" only when a runner (npm, bun, deno, pytest, uv, vault ...) starts a simple command whose words
match the eval's `ran` regex; `eval && git commit` counts, a commit message or a grep naming it does not.

Unknown repos (anything not in eval-gate.json) are never touched. Fails OPEN on unreadable input or a
git error (a gate bug must not block every commit). Off switch for the founder: EVAL_GATE_OFF=1.
Tests: tests/hooks/test_eval_gate.py.
"""
import json, os, re, shlex, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.environ.get("EVAL_GATE_REGISTRY") or os.path.join(HERE, "eval-gate.json")
STATE = os.environ.get("EVAL_GATE_STATE") or os.path.expanduser("~/.claude/state/eval-gate.json")

PR_TOOL = re.compile(r"^mcp__.*github.*__create_pull_request$")
GIT_OPTS = r"\bgit(?:\s+(?:-[cC]\s+\S+|--[\w-]+(?:=\S+)?|-[a-zA-Z]))*\s+"  # git -c k=v --no-pager -C x
COMMIT = re.compile(GIT_OPTS + r"commit(?![\w-])")  # not commit-tree / commit-graph
PR_CREATE = re.compile(r"\bgh\s+pr\s+create(?![\w-])")  # only used on a real gh segment, see is_pr_create()
ADD = re.compile(GIT_OPTS + r"add\b")
# Programs that run an eval. A command counts as an eval run only when one of these starts a simple command
# whose words match the eval's `ran` regex (so `git commit -m "ran eval:triage"` or `grep eval:triage` don't).
RUNNERS = {"npm", "npx", "pnpm", "yarn", "bun", "bunx", "deno", "node", "tsx", "vitest", "jest", "pytest",
           "python", "python3", "uv", "make"}
WRAPPERS = {"time", "nice", "sudo", "env", "timeout", "nohup"}  # looked through: the next word is the program
# Wrapper flags whose value is the next word (`sudo -u me`, `nice -n 5`, `timeout -s KILL 60`).
WRAPPER_ARGS = {"sudo": ("-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t"), "nice": ("-n",), "timeout": ("-s", "-k"), "env": ("-u", "-C", "-S")}
SHELLS = {"bash", "sh", "zsh"}
COMMIT_ALL = re.compile(r"\bcommit(?![\w-])[^|;&]*\s(?:--all\b|-[a-zA-Z]*a[a-zA-Z]*\b)")

PROMPT_PATH = re.compile(
    r"(^|/)prompts?/"                                  # prompts/ directories
    r"|(^|/)[\w-]*[_-]prompts?\.(py|ts|js|md|txt|json|ya?ml)$"  # persona_prompt.py, system-prompt.ts
    r"|(^|/)prompts?\.(py|ts|js|md|txt|json|ya?ml)$"   # prompt.py
    r"|system[_-]?prompt", re.I)
TEST_DIR = re.compile(
    r"(^|/)(tests?|__tests__|__mocks__|docs?|fixtures)/|\.(test|spec)\.\w+$|_test\.\w+$|(^|/)test_[^/]*\.py$", re.I)
DOC_FILE = re.compile(
    r"\.(md|mdx|txt|rst|lock|snap)$|(^|/)(package-lock\.json|bun\.lockb?|uv\.lock|CHANGELOG[^/]*)$", re.I)
MODEL_ID = re.compile(
    r"claude-(?:opus|sonnet|haiku|fable|instant|\d)[\w.:-]*|anthropic[./]claude[\w.:-]*"
    r"|(?:openai[./])?gpt-(?:oss-\d+b|\d)[\w.:-]*|o[134]-(?:mini|preview)\b"
    r"|deepseek[/-][\w.-]+|mistral\.[\w.:-]+|ministral[\w.-]*|zai\.glm[\w.-]*|glm-\d[\w.-]*"
    r"|qwen\d?[\w.-]*\d[\w.-]*|(?:us\.)?amazon\.nova[\w.:-]*|gemini-[\w.-]+"
    r"|meta-llama/[\w.-]+|llama-?3[\w.-]*|moonshotai/[\w.-]+|kimi-k2[\w.-]*", re.I)
MODEL_ASSIGN = re.compile(
    # LLM_MODEL = "...", DEFAULT_MODEL: x, BEDROCK_FAST_MODEL=... (not DATA_MODEL_VERSION)
    r"\b(?:[A-Z]+_)*(?:LLM|AI|CHAT|DEFAULT|FALLBACK|PRIMARY|FAST|CHEAP|BEDROCK|GROQ|ANTHROPIC|OPENAI|OPENROUTER)"
    r"_MODEL(?:_ID)?\s*[:=]\s*['\"`\w]"
    r"|\bMODEL(?:_ID|_NAME)?\s*[:=]\s*['\"`]"                     # MODEL = "..."
    r"|\bmodel(?:_?[iI]d)?\s*[:=]\s*['\"`](?![A-Z][a-z]+['\"`])")  # model: 'x', model_id="..." (not model: "User")
STRONG_PROMPT = re.compile(
    r"\bSYSTEM_PROMPT\b|\bsystem_?[pP]rompt\b|['\"]role['\"]\s*:\s*['\"]system['\"]|\brole:\s*['\"]system['\"]")
YOU_ARE = re.compile(r"\bYou are (?:a|an|the)\b")
PROMPT_WORD = re.compile(r"(?i)system|role|prompt|persona|instruction")
LONG_YOU_ARE = re.compile(r"\bYou are (?:a|an|the)\b[^\n]{60,}")
SCORE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|/\s*\d+(?!\d|\s*/))")  # 47/50 or 94% (not a date 11/18/26)
NONE_LINE = re.compile(r"(?i)\beval\s*:\s*none\b[^\n]{8,}")
SKIPPED_LINE = re.compile(r"(?i)\beval\s*:\s*skipped\s*:\s*[^\n]{8,}")


def sh(args, cwd, timeout=3):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def load_registry():
    with open(REGISTRY) as f:
        return json.load(f)["repos"]


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE)


def repo_of(d):
    """(repo name, toplevel) for a directory, or (None, None)."""
    try:
        top = sh(["git", "rev-parse", "--show-toplevel"], d).strip()
        url = sh(["git", "remote", "get-url", "origin"], top).strip()
    except Exception:
        return None, None
    name = re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1])
    return name, top


def target_dir(cmd, cwd):
    """The directory a Bash command acts on: a `cd X &&` (also inside a subshell), then `git -C X`, else cwd."""
    d = cwd
    arg = r"(\"[^\"]+\"|'[^']+'|[^\s;&|()]+)"
    for pat in (r"(?:^|[(;&|]\s*)cd\s+" + arg + r"\s*(?:&&|;)",
                r"\bgit(?:\s+(?:-c\s+\S+|--[\w-]+(?:=\S+)?))*\s+-C\s+" + arg):
        m = re.search(pat, cmd)
        if m:
            p = os.path.expanduser(m.group(1).strip("'\""))
            d = p if os.path.isabs(p) else os.path.join(d, p)
    return d


def segments(cmd):
    """The simple commands in a shell line, as [(separator before it, [words])]; [] if it can't be parsed."""
    try:
        lx = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        toks = list(lx)
    except ValueError:
        return []
    out, cur, sep = [], [], None
    for t in toks:
        if t and set(t) <= set("();&|"):
            if cur:
                out.append((sep, cur))
            cur, sep = [], (t.strip("()") or sep or ";")
        else:
            cur.append(t)
    if cur:
        out.append((sep, cur))
    return out


def shell_c(words):
    """The script of `bash -c '...'` / `sh -lc '...'`, or None."""
    if words and os.path.basename(words[0]) in SHELLS:
        for i, x in enumerate(words[1:-1], 1):
            if re.fullmatch(r"-\w*c\w*", x):
                return words[i + 1]
    return None


def program(words):
    """The words from the real program on: past VAR=x, wrappers (time, sudo, timeout 900) and `vault run ... --`."""
    w = list(words)
    while w:
        if re.match(r"^\w+=", w[0]):
            w = w[1:]
        elif os.path.basename(w[0]) in WRAPPERS:
            takes_value = WRAPPER_ARGS.get(os.path.basename(w[0]), ())
            w = w[1:]
            while w and (w[0].startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", w[0])):
                w = w[2:] if w[0] in takes_value else w[1:]
        elif os.path.basename(w[0]) == "vault" and "--" in w:
            w = w[w.index("--") + 1:]
        else:
            break
    return w


GIT_VALUE_OPTS = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path")


def git_sub(words):
    """The git subcommand of a simple command whose real program is git (`git -c k=v -C x commit` -> "commit"),
    else None. Exact word, so `commit-tree` is not `commit` and `echo git commit` is not git at all."""
    w = program(words)
    if not w or os.path.basename(w[0]) != "git":
        return None
    i = 1
    while i < len(w) and w[i].startswith("-"):
        i += 2 if w[i] in GIT_VALUE_OPTS else 1
    return w[i] if i < len(w) else None


def gh_pr_create(words):
    """True when the simple command's real program is `gh pr create` (flags like -R x allowed before)."""
    w = program(words)
    if not w or os.path.basename(w[0]) != "gh":
        return False
    rest, i = [], 1
    while i < len(w) and len(rest) < 2:
        if w[i].startswith("-"):
            i += 2 if w[i] in ("-R", "--repo", "--hostname") else 1
        else:
            rest.append(w[i])
            i += 1
    return rest == ["pr", "create"]


def is_commit(cmd):
    return any(git_sub(w) == "commit" for _, w in flat_segments(cmd))


def is_pr_create(cmd):
    return any(gh_pr_create(w) for _, w in flat_segments(cmd))


def runs(words, e, depth=0):
    """True when one simple command actually runs eval `e`: an eval runner (npm, bun, deno, pytest ...) is the
    program, not a mention in a commit message, a grep or an echo. `bash -c '...'` is looked inside."""
    w = program(words)
    script = shell_c(w)
    if script is not None:
        return depth < 3 and any(runs(x, e, depth + 1) for _, x in segments(script))
    return bool(w) and os.path.basename(w[0]) in RUNNERS and bool(re.search(e["ran"], " ".join(w)))


def flat_segments(cmd, depth=0):
    """segments(), with each `bash -c '...'` replaced by the commands inside it."""
    out = []
    for sep, words in segments(cmd):
        script = shell_c(program(words))
        inner = flat_segments(script, depth + 1) if script is not None and depth < 3 else []
        if inner:
            out.append((sep, inner[0][1]))
            out.extend(inner[1:])
        else:
            out.append((sep, words))
    return out


def ran_before_commit(cmd, e):
    """True when `eval && ... && git commit` runs eval `e` first (the commit only happens if the eval passed)."""
    chain = []
    for sep, words in flat_segments(cmd):
        if sep not in (None, "&&"):
            chain = []
        if git_sub(words) == "commit":
            return any(runs(w, e) for w in chain)
        chain.append(words)
    return False


def parse_diff(text):
    """{path: [changed lines]} from a -U0 unified diff."""
    out, cur, header = {}, None, False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            cur, header = None, True
        elif line.startswith("@@"):
            header = False
        elif not header:
            if cur and line[:1] in "+-":
                out[cur].append(line[1:])
        elif line.startswith("+++ "):
            p = line[4:].strip()
            if p != "/dev/null":
                cur = p[2:] if p.startswith("b/") else p
                out.setdefault(cur, [])
        elif line.startswith("--- "):
            p = line[4:].strip()
            if p != "/dev/null":
                cur = p[2:] if p.startswith("a/") else p
                out.setdefault(cur, [])
    return out


def why_llm(path, lines):
    """Reason a changed file is a prompt or model change (from the path or the changed lines), or None."""
    if TEST_DIR.search(path):
        return None
    if PROMPT_PATH.search(path):
        return "prompt file"  # prompts/*.md are prompts, not docs
    if DOC_FILE.search(path):
        return None
    for l in lines:
        if MODEL_ID.search(l) or MODEL_ASSIGN.search(l):
            return "model id"
        if STRONG_PROMPT.search(l) or (YOU_ARE.search(l) and (len(l) >= 80 or PROMPT_WORD.search(l))):
            return "prompt string"
    return None


def is_llm_file(top, path, strict=False):
    """Whether the whole file builds a prompt or picks a model. strict (outside every eval area): only a
    system-prompt marker or a long "You are a ..." line counts, so a file that merely names a model doesn't."""
    try:
        with open(os.path.join(top, path), errors="replace") as f:
            text = f.read(300_000)
    except OSError:
        return False
    if strict:
        return bool(STRONG_PROMPT.search(text) or LONG_YOU_ARE.search(text))
    return bool(STRONG_PROMPT.search(text) or YOU_ARE.search(text) or MODEL_ID.search(text) or MODEL_ASSIGN.search(text))


def classify(cfg, changes, top):
    """{eval name or None: [(path, reason)]} for every prompt/model change.

    A file inside an eval's `always` area (its golden data, its own code) always counts. A file inside an
    eval's `paths` counts when it is an LLM file at all (an edit in the middle of a long prompt has no
    marker on the changed line). Anywhere else the path or the changed lines must show it, or the file must
    build a system prompt (an edit in the middle of a prompt string)."""
    out = {}
    for path, lines in sorted(changes.items()):
        ev = next((e for e in cfg["evals"] if re.search(e["paths"], path)), None)
        if ev and ev.get("always") and re.search(ev["always"], path):
            reason = "eval data"
        else:
            reason = why_llm(path, lines)
            if not reason and not (TEST_DIR.search(path) or DOC_FILE.search(path)) \
                    and is_llm_file(top, path, strict=ev is None):
                reason = "LLM file"
        if not reason:
            continue
        if ev is None:
            ev = next((e for e in cfg["evals"] if e["name"] == cfg.get("default")), None)
        out.setdefault(ev["name"] if ev else None, []).append((path, reason))
    return out


def newest_mtime(top, paths):
    ts = 0.0
    for p in paths:
        try:
            ts = max(ts, os.path.getmtime(os.path.join(top, p)))
        except OSError:
            pass
    return ts


def local():
    return os.environ.get("CLAUDE_CODE_REMOTE", "").lower() != "true" and shutil.which("vault")


def how(cfg, name):
    e = next(x for x in cfg["evals"] if x["name"] == name)
    if local() and e.get("live"):
        return f"`{e['offline']}` and live `{e['live']}`"
    return f"`{e['offline']}`" + ("" if e.get("live") else " (no live eval)")


def files_list(items, n=6):
    shown = ", ".join(f"{p} ({r})" for p, r in items[:n])
    return shown + (f" +{len(items) - n} more" if len(items) > n else "")


def missing_runs(repo, cfg, top, groups, cmd=""):
    """Evals that have not run since their files last changed (`eval && git commit` counts as a run)."""
    state = load_state().get(repo, {})
    need = []
    for name, items in groups.items():
        if name is None:
            continue
        e = next(x for x in cfg["evals"] if x["name"] == name)
        if cmd and ran_before_commit(cmd, e):
            continue
        rec = state.get(name, {})
        ran = rec.get("ts", 0)
        if rec.get("ok") is False or ran < newest_mtime(top, [p for p, _ in items]):  # failed counts as not run
            need.append(name)
    return need


def add_specs(cmd):
    """Pathspecs of the `git add` in a command ([] = everything: -A, --all, -u or no path given)."""
    for _, words in segments(cmd):
        if not ADD.search(" ".join(words)):
            continue
        rest = words[words.index("add") + 1:] if "add" in words else []
        if any(a in ("-A", "--all", "-u", "--update") for a in rest):
            return []
        return [a for a in rest if not a.startswith("-")]  # words are already unquoted: keep spaces
    return []


def commit_changes(top, cmd, d=None):
    staged = sh(["git", "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"], top)
    changes = parse_diff(staged)
    if ADD.search(cmd) or COMMIT_ALL.search(cmd):
        specs = add_specs(cmd) if ADD.search(cmd) and not COMMIT_ALL.search(cmd) else []
        d = d or top  # pathspecs are relative to where the command runs; diff output is repo-relative
        for p, ls in parse_diff(sh(["git", "diff", "-U0", "--no-color", "--no-ext-diff", "--", *specs], d)).items():
            changes.setdefault(p, []).extend(ls)
        if ADD.search(cmd):
            for p in sh(["git", "ls-files", "--others", "--exclude-standard", "--full-name", "--", *specs],
                        d).splitlines():
                try:
                    with open(os.path.join(top, p), errors="replace") as f:
                        changes.setdefault(p, []).extend(f.read(200_000).splitlines())
                except OSError:
                    changes.setdefault(p, [])
    return changes


def branch_changes(top, base, head="HEAD"):
    for ref in (f"origin/{base}", base):
        try:
            sh(["git", "rev-parse", "--verify", "--quiet", ref], top)
        except Exception:
            continue
        return parse_diff(sh(["git", "diff", "-U0", "--no-color", "--no-ext-diff", f"{ref}...{head}"], top))
    raise RuntimeError("base not found")


def default_base(top):
    try:
        return sh(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], top).strip().split("/", 1)[1]
    except Exception:
        return "main"


def check_commit(repo, cfg, top, cmd, d=None):
    groups = classify(cfg, commit_changes(top, cmd, d), top)
    need = missing_runs(repo, cfg, top, groups, cmd)
    if not need:
        return None
    lines = [f"- {n}: {how(cfg, n)}. Changed: {files_list(groups[n])}" for n in need]
    where = "Here (local, vault present) run offline and live." if local() else "Cloud: run the offline eval."
    return (f"eval-gate WARNING (commit goes through): this commit changes an LLM prompt or model in {repo} and its "
            f"eval has not run (or failed) since. {where}\n" + "\n".join(lines) +
            "\nThe PR is blocked until it passes and the score is in the PR body, e.g. `Eval (" + need[0] +
            ", offline): 47/50`, or the body says `Eval: skipped: <why>`.")


def check_pr(repo, cfg, top, base, head, body):
    groups = classify(cfg, branch_changes(top, base, head), top)
    if not groups or SKIPPED_LINE.search(body):
        return None
    problems = []
    need = missing_runs(repo, cfg, top, groups)
    for n in need:
        problems.append(f"- run {n}: {how(cfg, n)} (changed: {files_list(groups[n])})")
    for n in groups:
        if n is None:
            continue
        line = re.compile(r"(?i)\beval\s*\(\s*" + re.escape(n) + r"\s*(?:,[^)\n]*)?\)\s*:\s*" + SCORE.pattern)
        ok = bool(line.search(body))
        if not ok:
            problems.append(f"- the PR body needs a score line for {n}, e.g. `Eval ({n}, offline): 47/50 (94%)`")
    if None in groups and not NONE_LINE.search(body):
        problems.append("- no eval covers " + files_list(groups[None]) + ": add a line `Eval: none: <why>` to the "
                        "PR body, and write a small eval (skill llm-provider-chain, cheapest-model section)")
    if not problems:
        return None
    return (f"eval-gate: this PR changes an LLM prompt or model in {repo}. Before opening it:\n" + "\n".join(problems))


def pr_body_from_cmd(cmd, cwd):
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return cmd
    for i, t in enumerate(toks):
        if t in ("--body-file", "-F") and i + 1 < len(toks):
            p = toks[i + 1]
            try:
                with open(p if os.path.isabs(p) else os.path.join(cwd, p)) as f:
                    return f.read()
            except OSError:
                return ""
        if t.startswith("--body-file="):
            try:
                with open(os.path.join(cwd, t.split("=", 1)[1])) as f:
                    return f.read()
            except OSError:
                return ""
    return cmd  # the body is inline (--body / heredoc): search the whole command


def flag(cmd, names):
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return None
    for i, t in enumerate(toks):
        if t in names and i + 1 < len(toks):
            return toks[i + 1]
        for n in names:
            if n.startswith("--") and t.startswith(n + "="):
                return t.split("=", 1)[1]
    return None


def find_clone(repo, cwd):
    for d in (cwd, os.path.join(os.path.dirname(cwd), repo), os.path.join(cwd, repo),
              os.path.join("/home/user", repo), os.path.expanduser(f"~/{repo}")):
        if os.path.isdir(d):
            name, top = repo_of(d)
            if name == repo:
                return top
    return None


def deny(msg):
    return ("deny", msg) if msg else None


def pre(tool, inp, cwd, reg):
    if tool == "Bash":
        cmd = inp.get("command") or ""
        commit, pr = is_commit(cmd), is_pr_create(cmd)
        if not (commit or pr):
            return None
        d = target_dir(cmd, cwd)
        repo, top = repo_of(d)
        if repo not in reg:
            return None
        if commit:
            r = check_commit(repo, reg[repo], top, cmd, d)
            if r:
                return ("warn", r)  # a commit is never blocked; the hard requirement is at PR time
        if pr:
            base = flag(cmd, ("--base", "-B")) or default_base(top)
            head = flag(cmd, ("--head", "-H"))
            return deny(check_pr(repo, reg[repo], top, base, f"origin/{head}" if head else "HEAD", pr_body_from_cmd(cmd, d)))
        return None
    if PR_TOOL.match(tool):
        repo = inp.get("repo") or ""
        if repo not in reg:
            return None
        top = find_clone(repo, cwd)
        if not top:
            return None
        head = inp.get("head") or "HEAD"
        cur = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], top).strip()
        head_ref = "HEAD" if head in (cur, "HEAD") else f"origin/{head}"
        return deny(check_pr(repo, reg[repo], top, inp.get("base") or default_base(top), head_ref, inp.get("body") or ""))
    return None


# Commands after an eval that print nothing of their own.
QUIET = {"true", ":", "false", "exit"}
# Filters that only pass the eval's output on: quiet only right after a `|` and with no file to read.
PIPE_FILTERS = {"tee", "tail", "head", "grep"}


def quiet_after(sep, words):
    w = program(words) or [""]
    name = os.path.basename(w[0])
    if name in QUIET:
        return True
    if name not in PIPE_FILTERS or sep != "|":
        return False
    if name == "tee":
        return True
    args = [a for a in w[1:] if not a.startswith("-") and not a.isdigit()]
    if name == "grep" and any(grep_reads_files(a) for a in w[1:]):
        return False
    return len(args) <= (1 if name == "grep" else 0)  # grep keeps its pattern; anything more is a file


GREP_FILE_LONG = ("--recursive", "--dereference-recursive", "--file", "--directories")


def grep_reads_files(arg):
    """grep flags that read files with no file operand: -r/-R search the current
    directory (GNU grep), -f reads patterns from a file, -d sets how to read dirs.
    Short flags cluster, so -rf and -ir count too."""
    if arg.startswith("--"):
        return arg.startswith(GREP_FILE_LONG)
    return arg.startswith("-") and any(c in "rRfd" for c in arg[1:])


def post(tool, inp, resp, cwd, reg):
    if tool != "Bash":
        return
    cmd = inp.get("command") or ""
    repo, top = repo_of(target_dir(cmd, cwd))
    if repo not in reg:
        return
    segs = flat_segments(cmd)
    hits = {}
    for i, (_, w) in enumerate(segs):
        for e in reg[repo]["evals"]:
            if runs(w, e):
                # The exit status is the eval's only when nothing after it can overwrite it (`; true`, `|| x`, `| tee`).
                after = segs[i + 1:]
                # A later command that prints (`echo 47/50`) could fake the score when the status is masked.
                quiet = all(quiet_after(sep, x) for sep, x in after)
                hits[e["name"]] = (all(s == "&&" for s, _ in after), quiet)
    if not hits:
        return
    out, code = "", None
    if isinstance(resp, dict):
        out = (resp.get("stdout") or "") + (resp.get("stderr") or "")
        for k in ("exit_code", "exitCode", "returncode", "return_code", "status_code"):
            if isinstance(resp.get(k), int) and not isinstance(resp.get(k), bool):
                code = resp[k]
                break
        if resp.get("interrupted"):
            code = code if code else 130
    elif isinstance(resp, str):
        out = resp
    tail = out[-600:]
    m = SCORE.search(tail)
    score = m.group(0) if m else None
    state = load_state()
    for n, (observable, quiet) in hits.items():
        if observable and code is not None:
            ok = code == 0
        else:  # status masked or not reported: believe a score only if nothing after the eval printed
            ok = score is not None and quiet
        state.setdefault(repo, {})[n] = {"ts": time.time(), "cmd": cmd[:300], "tail": tail,
                                         "exit": code if observable else None, "score": score, "ok": ok}
    save_state(state)


def main():
    if os.environ.get("EVAL_GATE_OFF") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
        tool = data.get("tool_name") or ""
        inp = data.get("tool_input") or {}
        cwd = data.get("cwd") or os.getcwd()
        event = data.get("hook_event_name") or "PreToolUse"
        if not isinstance(inp, dict) or not (tool == "Bash" or PR_TOOL.match(tool)):
            return 0
        reg = load_registry()
        if event == "PostToolUse":
            post(tool, inp, data.get("tool_response"), cwd, reg)
            return 0
        reason = pre(tool, inp, cwd, reg)
    except Exception as e:  # fail open, but say so: a silent pass looks like a clean check
        print(f"eval-gate: check skipped ({type(e).__name__}: {str(e)[:120]}); run the eval by hand",
              file=sys.stderr)
        return 0
    if reason and reason[0] == "deny":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason[1],
        }}))
    elif reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": reason[1],
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
