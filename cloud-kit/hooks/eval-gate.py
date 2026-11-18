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
                        with no recorded run of its eval since the files last changed is denied.
  PreToolUse PR create  `gh pr create` or a GitHub MCP create_pull_request: the branch diff against
                        its base is scanned the same way, and the body must carry one score line per
                        eval ("Eval (inbox-triage, offline): 47/50") or "Eval: none" with a reason
                        when no eval covers the change.

What counts as a prompt or model change:
  - a changed path under a prompt location (prompts/ dirs, *_prompt.py, system_prompt files) or inside
    a registered eval's `paths` (which includes the eval's golden data), or
  - an added or removed line, outside tests and docs, with a model id, a model assignment or a prompt
    string (SYSTEM_PROMPT, role "system", "You are a ...").

Unknown repos (anything not in eval-gate.json) are never touched. Fails OPEN on unreadable input or a
git error (a gate bug must not block every commit). Off switch for the founder: EVAL_GATE_OFF=1.
Tests: tests/hooks/test_eval_gate.py.
"""
import json, os, re, shlex, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.environ.get("EVAL_GATE_REGISTRY") or os.path.join(HERE, "eval-gate.json")
STATE = os.environ.get("EVAL_GATE_STATE") or os.path.expanduser("~/.claude/state/eval-gate.json")

PR_TOOL = re.compile(r"^mcp__.*github.*__create_pull_request$")
COMMIT = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b")
PR_CREATE = re.compile(r"\bgh\s+pr\s+create\b")
ADD = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?add\b")
COMMIT_ALL = re.compile(r"\bcommit\b[^|;&]*\s(?:--all\b|-[a-zA-Z]*a[a-zA-Z]*\b)")

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
    r"\b[A-Z_]*MODEL[A-Z_]*\s*[:=]\s*['\"`\w]"                 # LLM_MODEL = "...", DEFAULT_MODEL: x
    r"|\bmodel(?:_?[iI]d|_?[nN]ame)?\s*[:=]\s*['\"`]")          # model: '...', model_id="..."
PROMPT_STR = re.compile(
    r"\bSYSTEM_PROMPT\b|\bsystem_?[pP]rompt\b|['\"]role['\"]\s*:\s*['\"]system['\"]|\brole:\s*['\"]system['\"]"
    r"|\bYou are (?:a|an|the)\b")
SCORE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|/\s*\d+)")
NONE_LINE = re.compile(r"(?i)\beval\s*:\s*none\b[^\n]{8,}")


def sh(args, cwd, timeout=8):
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
    """The directory a Bash command acts on: a leading `cd X &&`, else `git -C X`, else cwd."""
    m = re.match(r"\s*cd\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)\s*(?:&&|;)", cmd)
    if not m:
        m = re.search(r"\bgit\s+-C\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", cmd)
    if m:
        p = os.path.expanduser(m.group(1).strip("'\""))
        return p if os.path.isabs(p) else os.path.join(cwd, p)
    return cwd


def parse_diff(text):
    """{path: [changed lines]} from a -U0 unified diff."""
    out, cur = {}, None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            cur = None
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
        elif cur and line[:1] in "+-":
            out[cur].append(line[1:])
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
        if PROMPT_STR.search(l):
            return "prompt string"
    return None


def is_llm_file(top, path):
    try:
        with open(os.path.join(top, path), errors="replace") as f:
            text = f.read(300_000)
    except OSError:
        return False
    return bool(PROMPT_STR.search(text) or MODEL_ID.search(text) or MODEL_ASSIGN.search(text))


def classify(cfg, changes, top):
    """{eval name or None: [(path, reason)]} for every prompt/model change.

    A file inside an eval's `always` area (its golden data, its own code) always counts. A file inside an
    eval's `paths` counts when it is an LLM file at all (an edit in the middle of a long prompt has no
    marker on the changed line). Anywhere else the path or the changed lines must show it."""
    out = {}
    for path, lines in sorted(changes.items()):
        ev = next((e for e in cfg["evals"] if re.search(e["paths"], path)), None)
        if ev and ev.get("always") and re.search(ev["always"], path):
            reason = "eval data"
        else:
            reason = why_llm(path, lines)
            if not reason and ev and not (TEST_DIR.search(path) or DOC_FILE.search(path)) and is_llm_file(top, path):
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
    """Evals that have not run since their files last changed (a command that runs the eval itself counts)."""
    state = load_state().get(repo, {})
    need = []
    for name, items in groups.items():
        if name is None:
            continue
        e = next(x for x in cfg["evals"] if x["name"] == name)
        if cmd and re.search(e["ran"], cmd):
            continue
        ran = state.get(name, {}).get("ts", 0)
        if ran < newest_mtime(top, [p for p, _ in items]):
            need.append(name)
    return need


def commit_changes(top, cmd):
    staged = sh(["git", "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"], top)
    changes = parse_diff(staged)
    if ADD.search(cmd) or COMMIT_ALL.search(cmd):
        for p, ls in parse_diff(sh(["git", "diff", "-U0", "--no-color", "--no-ext-diff"], top)).items():
            changes.setdefault(p, []).extend(ls)
        if ADD.search(cmd):
            for p in sh(["git", "ls-files", "--others", "--exclude-standard"], top).splitlines():
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


def check_commit(repo, cfg, top, cmd):
    groups = classify(cfg, commit_changes(top, cmd), top)
    need = missing_runs(repo, cfg, top, groups, cmd)
    if not need:
        return None
    lines = [f"- {n}: {how(cfg, n)}. Changed: {files_list(groups[n])}" for n in need]
    where = "Here (local, vault present) run offline and live." if local() else "Cloud: run the offline eval."
    return (f"eval-gate: this commit changes an LLM prompt or model in {repo} and its eval has not run since. "
            f"{where}\n" + "\n".join(lines) +
            "\nThen commit again and put the score in the PR body, e.g. `Eval (" + need[0] + ", offline): 47/50`.")


def check_pr(repo, cfg, top, base, head, body):
    groups = classify(cfg, branch_changes(top, base, head), top)
    if not groups:
        return None
    problems = []
    need = missing_runs(repo, cfg, top, groups)
    for n in need:
        problems.append(f"- run {n}: {how(cfg, n)} (changed: {files_list(groups[n])})")
    for n in groups:
        if n is None:
            continue
        ok = any(n.lower() in l.lower() and re.search(r"(?i)\beval", l) and SCORE.search(l)
                 for l in body.splitlines())
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


def pre(tool, inp, cwd, reg):
    if tool == "Bash":
        cmd = inp.get("command") or ""
        is_commit, is_pr = bool(COMMIT.search(cmd)), bool(PR_CREATE.search(cmd))
        if not (is_commit or is_pr):
            return None
        d = target_dir(cmd, cwd)
        repo, top = repo_of(d)
        if repo not in reg:
            return None
        if is_commit:
            r = check_commit(repo, reg[repo], top, cmd)
            if r:
                return r
        if is_pr:
            base = flag(cmd, ("--base", "-B")) or default_base(top)
            head = flag(cmd, ("--head", "-H"))
            return check_pr(repo, reg[repo], top, base, f"origin/{head}" if head else "HEAD", pr_body_from_cmd(cmd, d))
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
        return check_pr(repo, reg[repo], top, inp.get("base") or default_base(top), head_ref, inp.get("body") or "")
    return None


def post(tool, inp, resp, cwd, reg):
    if tool != "Bash":
        return
    cmd = inp.get("command") or ""
    repo, top = repo_of(target_dir(cmd, cwd))
    if repo not in reg:
        return
    hits = [e["name"] for e in reg[repo]["evals"] if re.search(e["ran"], cmd)]
    if not hits:
        return
    out = ""
    if isinstance(resp, dict):
        out = (resp.get("stdout") or "") + (resp.get("stderr") or "")
    elif isinstance(resp, str):
        out = resp
    state = load_state()
    for n in hits:
        state.setdefault(repo, {})[n] = {"ts": time.time(), "cmd": cmd[:300], "tail": out[-600:]}
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
    except Exception:
        return 0
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
