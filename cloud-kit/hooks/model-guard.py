#!/usr/bin/env python3
"""PreToolUse hook: enforce the model policy and the sub-agent budget (founder HARD RULE 2026-11-16).

Plan in Opus -> build in Sonnet (Haiku for mechanical work) -> review + ship-check in Opus.
NEVER Fable for lanes, routines or sub-agents: on 2026-11-16 two lanes booked on Fable hit the
weekly Fable limit and died. A rule the model has to remember failed; this check doesn't forget.

Denies (with the reason shown to the model so it can fix the call):
  1. Any Agent / Task / RemoteTrigger / Workflow / start_session / scheduled-task call that names
     a Fable model anywhere (a `model` field, or `model: 'fable…'` inside a workflow script).
  2. RemoteTrigger create/update that books a routine (has job_config) with no explicit model:
     the account default could be Fable.
  3. RemoteTrigger create/update whose name marks it as a review / ship-check routine on a
     non-Opus model.
  4. RemoteTrigger create/update whose prompt does not state a sub-agent cap
     ("at most 3 sub-agents", "no sub-agents", "sub-agent budget: max 2", ...).

Anything else passes. Fails OPEN on unreadable input (a guard bug must not block every tool);
tests in tests/hooks/test_model_guard.py prove each deny fires. Emergency off switch for the
founder only: env MODEL_GUARD_OFF=1 in the shell that starts Claude.
"""
import json, os, re, sys

GUARDED = re.compile(r"^(Agent|Task|RemoteTrigger|Workflow|mcp__ccd_session__start_session|mcp__scheduled-tasks__.*)$")
FABLE = re.compile(r"fable", re.I)
SCRIPT_FABLE = re.compile(r"""model\s*[:=]\s*['"`][^'"`]*fable""", re.I)
REVIEW_NAME = re.compile(r"ship-?check|\breview(er)?\b|\bred-?team\b|^R\d+\b", re.I)
HELPER = r"(?:sub-?agents?|helper[- ]agents?|helpers)"
LIMIT = r"(?:at most|max(?:imum)?|(?:no|not|never) (?:use )?more than|up to|cap(?:ped)?(?: of| at)?|limit(?:ed)?(?: of| to)?|≤|<=)"
CAP = re.compile(
    rf"{LIMIT}\s*:?\s*\d+\s*(?:\w+\s+)?{HELPER}"          # "at most 3 sub-agents", "max 2 Sonnet helpers"
    rf"|{HELPER}[^.\n]{{0,60}}?{LIMIT}\s*:?\s*\d+"         # "sub-agent budget: at most 3"
    rf"|\bno\s+{HELPER}\b|\bzero\s+{HELPER}\b",            # "no sub-agents"
    re.I,
)


def walk(x, path=()):
    """Yield (key_path, value) for every leaf."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, path + (str(k),))
    elif isinstance(x, list):
        for v in x:
            yield from walk(v, path)
    else:
        yield path, x


def models(inp):
    return [v for p, v in walk(inp) if p and p[-1] == "model" and isinstance(v, str)]


def prompts(inp):
    """Routine prompt text: message content strings under job_config events (plus any 'prompt' field)."""
    out = []
    for p, v in walk(inp):
        if isinstance(v, str) and p and (p[-1] in ("content", "prompt", "text") or "events" in p):
            if len(v) >= 200:
                out.append(v)
    return out


def check(tool, inp):
    """Return a deny reason, or None to allow."""
    for m in models(inp):
        if FABLE.search(m):
            return (f"model-guard: '{m}' is Fable. Policy (HARD, 2026-11-16): plan in Opus, build in "
                    "claude-sonnet-5-5 (Haiku for mechanical work), review + ship-check in claude-opus-5-5. "
                    "Never Fable for lanes, routines or sub-agents. Change the model and retry.")
    if tool == "Workflow":
        script = inp.get("script") or ""
        if isinstance(script, str) and SCRIPT_FABLE.search(script):
            return "model-guard: the workflow script asks for a Fable model. Use sonnet/haiku for builders, opus for review."
    if tool != "RemoteTrigger" or inp.get("action") not in ("create", "update"):
        return None
    body = inp.get("body") or {}
    if not isinstance(body, dict) or "job_config" not in body:
        return None  # enable/disable/cron-only update: nothing to check
    ms = models(body)
    if not ms:
        return ("model-guard: this routine has no explicit model (job_config.ccr.session_context.model); "
                "the account default could be Fable. Set claude-sonnet-5-5 for a build lane or "
                "claude-opus-5-5 for review / ship-check.")
    name = str(body.get("name") or "")
    if REVIEW_NAME.search(name) and not any("opus" in m.lower() for m in ms):
        return (f"model-guard: '{name}' is a review / ship-check routine but runs on {ms[0]}. "
                "Policy: review and ship-check run on Opus (claude-opus-5-5).")
    texts = prompts(body)
    if texts and not any(CAP.search(t) for t in texts):
        return ("model-guard: the routine prompt does not state a sub-agent cap. Every lane prompt says "
                "its budget, e.g. 'Sub-agent budget: at most 3, Sonnet/Haiku only, reuse one via "
                "SendMessage instead of spawning new ones' (or 'no sub-agents'). Add it and retry.")
    return None


def main():
    if os.environ.get("MODEL_GUARD_OFF") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
        tool = data.get("tool_name") or ""
        inp = data.get("tool_input") or {}
        if not GUARDED.match(tool) or not isinstance(inp, dict):
            return 0
        reason = check(tool, inp)
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
