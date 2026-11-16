"""Shared engine for the correction checks (cloud-kit/hooks/correction-checks.py).

Founder corrections live as data in corrections.json next to this file. An entry with
"class": "check" is enforced here: either a regex ("check": "regex") or a named function
("check": "fn:<name>"). Each check names a surface (where it looks) and an action:

  surfaces: bash (a Bash command), write (text an Edit/Write/MultiEdit/NotebookEdit adds),
            reply (the final chat reply), prompt (the founder's message), turn (text the
            assistant wrote next to a tool call while working)
  actions:  block (PreToolUse deny / Stop block), ask (PreToolUse ask),
            warn (PostToolUse context), context (UserPromptSubmit context)

A line containing `correction-ok: <id>` in a command or written text skips that one check
(a deliberate, logged override). Hits are appended to ~/.claude/state/corrections-hits.jsonl
(id, surface, action, time; never the matched text) so the monthly prune can see which
checks never fire. Standard library only.
"""
import base64, json, os, re, time
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "corrections.json")
HITS = os.path.join("~", ".claude", "state", "corrections-hits.jsonl")

FENCE = re.compile(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)", re.S)
INLINE = re.compile(r"`[^`\n]*`")
URL = re.compile(r"https?://[^\s<>()\"'`\]\[|]+")
TEST_PATH = re.compile(r"(?:^|/)(?:tests?|__tests__|spec|fixtures)/|\.(?:test|spec)\.\w+$|(?:^|/)test_[^/]*$|_test\.\w+$")
DOC_PATH = re.compile(r"\.(?:md|mdx|txt|rst)$", re.I)
# The registry, engine and their tests hold bad examples on purpose; never check writes to them.
SELF_PATH = re.compile(r"cloud-kit/hooks/(?:corrections\.json|corrections_lib\.py|correction-checks\.py)$|tests/(?:hooks|learning)/test_correction")

_cache = {}


def load(path=REGISTRY):
    if path not in _cache:
        with open(path) as f:
            _cache[path] = json.load(f)["corrections"]
    return _cache[path]


def prose(text):
    """Reply text without code blocks or inline code (paths, commands, starters)."""
    return INLINE.sub(" ", FENCE.sub(" ", text or ""))


# ---------------------------------------------------------------- secrets
_SECRETS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenRouter key", re.compile(r"sk-or-v1-[A-Za-z0-9]{32,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-|svcacct-)?(?!ant-|or-)[A-Za-z0-9_-]{32,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Bedrock API key", re.compile(r"\bABSK[A-Za-z0-9+/=]{40,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Slack webhook", re.compile(r"hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]{20,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Groq key", re.compile(r"\bgsk_[A-Za-z0-9]{40,}")),
    ("Stripe secret", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}|\bwhsec_[A-Za-z0-9]{24,}")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("Supabase service-role JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.(eyJ[A-Za-z0-9_-]{20,})\.[A-Za-z0-9_-]{20,}")),
]
_PASSWORD = re.compile(r"""(?i)\b(?:password|passwd|pwd)\b["']?\s*[:=]\s*["']([^"'\s]{8,})["']""")
_PLACEHOLDER = re.compile(r"(?i)example|x{4,}|placeholder|your[_-]|dummy|fake|redacted|\*\*\*|changeme|<[^>]*>|\$\{|\.\.\.")


def _service_role(payload):
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return data.get("role") == "service_role"
    except Exception:
        return False


def find_secrets(text, passwords=False):
    """Kinds of credential found in text (placeholders and public Supabase anon keys don't count)."""
    found = []
    for kind, rx in _SECRETS:
        for m in rx.finditer(text or ""):
            if _PLACEHOLDER.search(m.group(0)):
                continue
            if kind.startswith("Supabase") and not _service_role(m.group(1)):
                continue
            found.append(kind)
            break
    if passwords:
        for m in _PASSWORD.finditer(text or ""):
            if not _PLACEHOLDER.search(m.group(1)) and not re.search(r"(?i)process\.env|os\.environ|getenv", m.group(1)):
                found.append("password")
                break
    return found


def fn_secret(entry, text, ctx):
    surface = ctx.get("surface")
    if surface == "bash" and re.match(r"\s*vault\s+(?:set|add|put|import)\b", text or ""):
        return None  # storing the pasted value in the vault is the fix, not the leak
    kinds = find_secrets(text, passwords=surface in ("reply", "prompt", "bash"))
    return ", ".join(kinds) if kinds else None


# ---------------------------------------------------------------- OpenRouter outside the OS app
OS_REPO = re.compile(r"(?i)unleashed-?os-mobile|(?:^|/)unleashedos(?:/|$)|/os-mobile(?:/|$)")
OPENROUTER_CODE = re.compile(r"openrouter\.ai/api|OPENROUTER_API_KEY|api\.openrouter|baseURL[^\n]{0,40}openrouter", re.I)
OPENROUTER_SPEND = re.compile(r"openrouter\.ai/api/v1/(?:key|credits)\b")
HTTP_CLIENT = re.compile(r"\b(?:curl|wget|http|xh|httpie|python3?|node|deno|bun)\b")


def fn_openrouter_outside_os(entry, text, ctx):
    where = f"{ctx.get('path') or ''} {ctx.get('cwd') or ''}"
    if OS_REPO.search(where) or "LLM_ALLOW_OPENROUTER" in (text or ""):
        return None
    if ctx.get("surface") == "write":
        p = ctx.get("path") or ""
        if DOC_PATH.search(p) or TEST_PATH.search(p) or not OPENROUTER_CODE.search(text or ""):
            return None
        return "OpenRouter call or key in non-OS code"
    calls = [m for m in re.finditer(r"openrouter\.ai/api/v1/\S*", text or "")]
    if not calls or not HTTP_CLIENT.search(text):
        return None
    if all(OPENROUTER_SPEND.match(m.group(0)) for m in calls):
        return None  # spend checks (/key, /credits) are allowed anywhere
    return "OpenRouter request outside the OS app"


# ---------------------------------------------------------------- URLs the founder can't open
LOCAL_HOST = re.compile(r"^(?:localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|\[::1\])$|\.(?:local|internal|test|invalid|localhost)$|(?:^|\.)example\.(?:com|org|net)$", re.I)
PLACEHOLDER_URL = re.compile(r"[{}<>]|XXX|(?i:your[-_]|<id>|TODO|\.\.\.)")
DEEP_LINK_HOSTS = (
    "github.com", "raw.githubusercontent.com", "claude.ai", "code.claude.com", "supabase.com", "vercel.com",
    "dashboard.stripe.com", "console.aws.amazon.com", "my.slack.com", "api.slack.com", "openrouter.ai",
    "console.groq.com", "console.anthropic.com", "platform.claude.com", "platform.openai.com",
    "console.cloud.google.com", "search.google.com", "dash.cloudflare.com", "railway.app", "railway.com",
    "fly.io", "appstoreconnect.apple.com", "developer.apple.com", "play.google.com", "expo.dev",
    "portal.telnyx.com", "app.netlify.com", "takeout.google.com",
)


def _host_ok(host):
    return any(host == h or host.endswith("." + h) for h in DEEP_LINK_HOSTS)


def _clean(url):
    return url.rstrip(".,;:!?*_)'\"").split("#")[0]


def fn_unverified_url(entry, text, ctx):
    seen = {_clean(u).rstrip("/") for u in ctx.get("seen_urls") or ()}
    bad = []
    for raw in URL.findall(prose(text)):
        url = _clean(raw)
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            continue
        if LOCAL_HOST.search(host) or PLACEHOLDER_URL.search(url):
            bad.append(url)
            continue
        if _host_ok(host):
            continue
        u = url.rstrip("/")
        if not any(u == s or s.startswith(u + "/") or s.startswith(u + "?") for s in seen):
            bad.append(url)
    return ", ".join(dict.fromkeys(bad)) if bad else None


# ---------------------------------------------------------------- status written in chat
SECTION = re.compile(r"^\s*(?:#{1,6}\s*|[-*]\s+)?\**(Done|Remaining|Still open|Heads-up|Proof|Needs you|Change log)\b\**\s*:?", re.M)


def fn_status_in_chat(entry, text, ctx):
    if not ctx.get("page_published"):
        return None
    if re.match(r"\s*\**\s*(?:STOP|NOT SHIPPABLE)\b", text or ""):
        return None  # STOP / NOT SHIPPABLE are said in chat in full
    sections = {m.group(1) for m in SECTION.finditer(prose(text))}
    return ", ".join(sorted(sections)) if len(sections) >= 2 else None


# ---------------------------------------------------------------- more than one question
def fn_multi_question(entry, text, ctx):
    body = URL.sub(" ", prose(text))
    qs = re.findall(r"[^.!?\n]{3,}\?(?=\s|$)", body)
    return f"{len(qs)} questions" if len(qs) > 1 else None


# ---------------------------------------------------------------- commit message format
COMMIT = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
COMMIT_TYPE = re.compile(r"^(?:feat|fix|refactor|docs|test|chore|perf|ci|style|build|revert)(?:\([\w./-]+\))?!?: \S")


def fn_commit_format(entry, text, ctx):
    if not COMMIT.search(text or "") or "--amend" in text and "-m" not in text:
        return None
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n\s*\1\b", text, re.S)
    if m:
        first = next((l.strip() for l in m.group(2).splitlines() if l.strip()), "")
    else:
        m = re.search(r"\s-(?:a?m|-message)\s*(?:=\s*)?(['\"])(.*?)(?<!\\)\1", text, re.S)
        if not m:
            return None
        first = m.group(2).strip().splitlines()[0] if m.group(2).strip() else ""
    if not first or first.startswith("$(") or COMMIT_TYPE.match(first):
        return None
    return first[:60]


# ---------------------------------------------------------------- narration while working
def fn_narration(entry, text, ctx):
    words = re.findall(r"\w+", prose(text))
    return f"{len(words)} words" if words else None


FUNCTIONS = {
    "secret": fn_secret,
    "openrouter_outside_os": fn_openrouter_outside_os,
    "unverified_url": fn_unverified_url,
    "status_in_chat": fn_status_in_chat,
    "multi_question": fn_multi_question,
    "commit_format": fn_commit_format,
    "narration": fn_narration,
}

_compiled = {}


def _rx(entry):
    key = (entry["id"], entry.get("pattern"))
    if key not in _compiled:
        flags = 0
        for ch in entry.get("flags", "i"):
            flags |= {"i": re.I, "s": re.S, "m": re.M}.get(ch, 0)
        _compiled[key] = re.compile(entry["pattern"], flags)
    return _compiled[key]


def surfaces(entry):
    s = entry.get("surface") or []
    return [s] if isinstance(s, str) else list(s)


def applies(entry, surface, ctx):
    if entry.get("class") != "check" or surface not in surfaces(entry):
        return False
    path = ctx.get("path") or ""
    if surface == "write":
        if SELF_PATH.search(path):
            return False
        if entry.get("paths") and not re.search(entry["paths"], path):
            return False
        if entry.get("skip_paths") and re.search(entry["skip_paths"], path):
            return False
    return True


def match(entry, text, ctx):
    """Short detail string when the check fires, else None."""
    text = text or ""
    if re.search(r"correction-ok:\s*" + re.escape(entry["id"]) + r"\b", text):
        return None
    check = entry.get("check", "regex")
    if check.startswith("fn:"):
        return FUNCTIONS[check[3:]](entry, text, ctx)
    body = prose(text) if entry.get("on", "prose" if ctx.get("surface") in ("reply", "turn") else "raw") == "prose" else text
    if entry.get("unless") and re.search(entry["unless"], body, re.I):
        return None
    m = _rx(entry).search(body)
    return m.group(0).strip()[:80] if m else None


def evaluate(surface, text, ctx=None, registry=None, actions=None):
    """[(entry, detail)] for every check on this surface that fires."""
    ctx = dict(ctx or {}, surface=surface)
    out = []
    for entry in registry if registry is not None else load():
        if not applies(entry, surface, ctx):
            continue
        if actions and entry.get("action") not in actions:
            continue
        try:
            detail = match(entry, text, ctx)
        except Exception:
            continue  # one broken check must never break the hook
        if detail:
            out.append((entry, detail))
    return out


def log_hits(hits, surface):
    if not hits:
        return
    try:
        path = os.path.expanduser(HITS)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        now = int(time.time())
        with open(path, "a") as f:
            for entry, _ in hits:
                f.write(json.dumps({"ts": now, "id": entry["id"], "surface": surface, "action": entry.get("action")}) + "\n")
    except Exception:
        pass


def describe(hits):
    """One line per hit. fn:secret details are credential kinds only, never the value."""
    return "\n".join(f"- {entry['id']}: {entry['message']} (found: {detail})" for entry, detail in hits)


# ---------------------------------------------------------------- test helpers
_FAKES = {
    "anthropic": lambda: "sk-ant-api03-" + "Q7wZ" * 12,
    "openrouter": lambda: "sk-or-v1-" + "a1b2c3d4" * 8,
    "openai": lambda: "sk-proj-" + "Zr4T" * 10,
    "aws": lambda: "AKIA" + "QWERTYUIOPASDFGH",
    "github": lambda: "ghp_" + "Ab3D" * 9,
    "slack": lambda: "xoxb-" + "1234567890-abcdefghij",
    "groq": lambda: "gsk_" + "Mn8P" * 11,
    "google": lambda: "AIza" + "Sy" + "B" * 33,
    "stripe": lambda: "sk_live_" + "51HqLm" * 5,
    "private-key": lambda: "-----BEGIN " + "PRIVATE KEY-----",
    "service-jwt": lambda: "eyJhbGciOiJIUzI1NiJ9." + base64.urlsafe_b64encode(
        json.dumps({"role": "service_role", "iss": "supabase"}).encode()).decode().rstrip("=") + "." + "s1gnature" * 3,
    "anon-jwt": lambda: "eyJhbGciOiJIUzI1NiJ9." + base64.urlsafe_b64encode(
        json.dumps({"role": "anon", "iss": "supabase"}).encode()).decode().rstrip("=") + "." + "s1gnature" * 3,
}


def expand_fakes(text):
    """Examples write credentials as {{fake:<kind>}} so no secret-shaped string is ever committed."""
    return re.sub(r"\{\{fake:([\w-]+)\}\}", lambda m: _FAKES[m.group(1)](), text)
