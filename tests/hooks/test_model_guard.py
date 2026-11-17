"""Tests for cloud-kit/hooks/model-guard.py (PreToolUse: no Fable, explicit model, Opus review, sub-agent cap).

Run: python3 -m unittest discover -s tests/hooks -v
Each deny case runs the real script as a subprocess, the way Claude Code calls it.
"""
import json, os, subprocess, sys, unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "..", "cloud-kit", "hooks", "model-guard.py")
CAP_LINE = "Sub-agent budget: at most 3, Sonnet/Haiku only; reuse one via SendMessage."
LONG = "Build lane for the AI-native roadmap. " * 10  # >200 chars, like a real lane prompt


def run(tool, inp, env=None):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                       capture_output=True, text=True, env={**os.environ, **(env or {})}, timeout=10)
    assert p.returncode == 0, p.stderr
    if not p.stdout.strip():
        return None
    out = json.loads(p.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


def routine(model="claude-sonnet-5-5", prompt=LONG + CAP_LINE, name="AI-native M3: evals", action="create"):
    ctx = {"allowed_tools": ["Bash"], "sources": []}
    if model is not None:
        ctx["model"] = model
    return {"action": action, "body": {"name": name, "job_config": {"ccr": {
        "environment_id": "env_x",
        "events": [{"data": {"type": "user", "message": {"role": "user", "content": prompt}}}],
        "session_context": ctx}}}}


class ModelGuardTest(unittest.TestCase):
    # --- Fable is denied everywhere ---
    def test_agent_on_fable_denied(self):
        self.assertIn("Fable", run("Agent", {"prompt": "x", "model": "fable"}))

    def test_task_on_fable_id_denied(self):
        self.assertIn("Fable", run("Task", {"prompt": "x", "model": "claude-fable-5-2"}))

    def test_routine_on_fable_denied(self):
        self.assertIn("Fable", run("RemoteTrigger", routine(model="claude-fable-5-2")))

    def test_start_session_on_fable_denied(self):
        self.assertIn("Fable", run("mcp__ccd_session__start_session", {"title": "t", "model": "fable"}))

    def test_workflow_script_fable_denied(self):
        self.assertIn("Fable", run("Workflow", {"script": "agent('x', {model: 'fable'})"}))

    # --- allowed calls stay allowed ---
    def test_agent_on_sonnet_allowed(self):
        self.assertIsNone(run("Agent", {"prompt": "x", "model": "sonnet"}))

    def test_agent_without_model_allowed(self):
        self.assertIsNone(run("Agent", {"prompt": "x", "subagent_type": "haiku-worker"}))

    def test_build_routine_with_cap_allowed(self):
        self.assertIsNone(run("RemoteTrigger", routine()))

    def test_review_routine_on_opus_allowed(self):
        self.assertIsNone(run("RemoteTrigger", routine(model="claude-opus-5-5", name="R1 review: AI-native M1-M4")))

    def test_enable_only_update_allowed(self):
        self.assertIsNone(run("RemoteTrigger", {"action": "update", "trigger_id": "t", "body": {"enabled": False}}))

    def test_run_and_list_ignored(self):
        self.assertIsNone(run("RemoteTrigger", {"action": "run", "trigger_id": "t"}))

    def test_unguarded_tool_ignored(self):
        self.assertIsNone(run("Bash", {"command": "echo fable", "model": "fable"}))

    def test_garbage_input_fails_open(self):
        p = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True, timeout=10)
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_off_switch(self):
        self.assertIsNone(run("Agent", {"model": "fable"}, env={"MODEL_GUARD_OFF": "1"}))

    # --- routine-specific denies ---
    def test_routine_without_model_denied(self):
        self.assertIn("no explicit model", run("RemoteTrigger", routine(model=None)))

    def test_review_routine_on_sonnet_denied(self):
        self.assertIn("Opus", run("RemoteTrigger", routine(name="ship-check R1 unleashed-systems #110")))

    def test_routine_without_cap_denied(self):
        self.assertIn("sub-agent cap", run("RemoteTrigger", routine(prompt=LONG)))

    def test_update_without_cap_denied(self):
        self.assertIn("sub-agent cap", run("RemoteTrigger", routine(prompt=LONG, action="update")))

    def test_cap_phrasings_accepted(self):
        for line in ("At most 3 sub-agents.", "Use no more than 2 Sonnet helpers.",
                     "Sub-agent budget: max 3.", "No sub-agents; do it yourself.",
                     "helper agents capped at 2", "≤3 subagents",
                     "Do not use more than 3 sub-agents."):
            with self.subTest(line=line):
                self.assertIsNone(run("RemoteTrigger", routine(prompt=LONG + line)))

    def test_cap_lookalikes_rejected(self):
        for line in ("Spawn sub-agents as needed.", "Use 3 sub-agents in parallel.",
                     "At most 3 PRs."):
            with self.subTest(line=line):
                self.assertIsNotNone(run("RemoteTrigger", routine(prompt=LONG + line)))


if __name__ == "__main__":
    unittest.main()
