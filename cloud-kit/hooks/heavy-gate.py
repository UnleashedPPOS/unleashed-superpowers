#!/usr/bin/env python3
"""PreToolUse hook: route bare heavy commands (jest, tsc, eslint, vitest, builds) through
~/bin/heavy-run so every chat waits its turn instead of piling onto an 8 GB Mac.

Covers Bash and context-mode ctx_execute (shell) / ctx_batch_execute. Rewrites each heavy
segment in place (`cd x && npx jest | tail` -> `cd x && heavy-run npx jest | tail`), leaves
`vault run -- ...` working (wraps after the `--`), skips commands already wrapped, and, when
a rewrite isn't safe (heredoc mixed with a heavy job), denies with the exact fix.
No-op when ~/bin/heavy-run isn't installed (cloud sessions). Silent on any error.
HEAVY_GATE=off disables. The wait budget follows the tool's timeout (background = no limit).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import heavy_lib as hl  # noqa: E402

SHELL_LANGS = {"shell", "bash", "sh", "zsh"}


def budget_for(inp):
    if inp.get("run_in_background"):
        return 0
    ms = inp.get("timeout") or 120000
    try:
        return min(30, int(ms) / 1000 * 0.25)  # leave most of the tool timeout for the job itself
    except (TypeError, ValueError):
        return 100


def rewrite_input(tool, inp):
    """Returns (new_input or None, deny_reason or None)."""
    budget = budget_for(inp)
    if tool == "Bash":
        new, deny = hl.rewrite_command(inp.get("command", ""), budget)
        return ({**inp, "command": new} if new else None), deny
    if tool.endswith("ctx_execute"):
        if str(inp.get("language", "")).lower() not in SHELL_LANGS:
            return None, None
        new, deny = hl.rewrite_command(inp.get("code", ""), budget)
        return ({**inp, "code": new} if new else None), deny
    if tool.endswith("ctx_batch_execute"):
        cmds, changed = [], False
        for c in inp.get("commands") or []:
            if isinstance(c, dict) and isinstance(c.get("command"), str):
                new, deny = hl.rewrite_command(c["command"], budget)
                if deny:
                    return None, deny
                if new:
                    c, changed = {**c, "command": new}, True
            cmds.append(c)
        return ({**inp, "commands": cmds} if changed else None), None
    return None, None


def main():
    if os.environ.get("HEAVY_GATE") == "off":
        return
    payload = json.load(sys.stdin)
    new, deny = rewrite_input(payload.get("tool_name", ""), payload.get("tool_input") or {})
    if deny:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": deny}}))
    elif new:
        # Same shape as rtk's rewrite: updatedInput without a permission decision (normal permission flow stays).
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecisionReason": "heavy-run gate: wait-your-turn for heavy jobs",
                                                 "updatedInput": new}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
