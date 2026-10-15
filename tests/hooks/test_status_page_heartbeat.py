"""Tests for cloud-kit/hooks/status-page-heartbeat.py (keeps the status page live during long work).

Run: python3 -m unittest discover -s tests/hooks -v
"""
import importlib.util, json, os, shutil, tempfile, unittest
from datetime import datetime, timezone
from unittest import mock

HOOK = os.path.join(os.path.dirname(__file__), "..", "..", "cloud-kit", "hooks", "status-page-heartbeat.py")
spec = importlib.util.spec_from_file_location("status_page_heartbeat", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

T0 = 1_800_000_000.0
URL = "https://claude.ai/artifact/AbC123"
PARENT = "https://claude.ai/artifact/Parent9"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def prompt(t, text="do the thing"):
    return {"type": "user", "timestamp": iso(t), "message": {"role": "user", "content": text}}


def tool(t, name, tid="x", **inp):
    return {"type": "assistant", "timestamp": iso(t),
            "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def result(t, text, tid="x"):
    return {"type": "user", "timestamp": iso(t),
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": text}]}}


def published(t, url=URL, path="/tmp/work-status.html"):
    return [tool(t, "Artifact", tid="pub", file_path=path), result(t, f"Published {path} at {url} (Version 1)", "pub")]


class HeartbeatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = mock.patch.dict(os.environ, {"HOME": self.tmp})
        self.home.start()
        self.addCleanup(self.home.stop)
        self.path = os.path.join(self.tmp, "t.jsonl")
        open(self.path, "w").close()
        self.repo_file = "/Users/someone/Developer/app/src/x.py"

    def add(self, *entries):
        with open(self.path, "a") as f:
            for e in entries:
                for x in (e if isinstance(e, list) else [e]):
                    f.write(json.dumps(x) + "\n")

    def run_hook(self, now, event="PostToolUse", **extra):
        return hook.main({"transcript_path": self.path, "session_id": "s1", "hook_event_name": event, **extra}, now=now)

    def test_no_nudge_before_interval(self):
        self.add(prompt(T0), tool(T0 + 60, "Bash", command="ls"))
        self.assertIsNone(self.run_hook(T0 + 29 * 60))

    def test_nudges_after_interval_then_waits_again(self):
        self.add(prompt(T0), published(T0 + 60), tool(T0 + 120, "Edit", file_path=self.repo_file))
        out = self.run_hook(T0 + 60 + 31 * 60)
        msg = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn(URL, msg)
        self.assertIn("31 min", msg)
        self.assertIsNone(self.run_hook(T0 + 60 + 45 * 60))  # nudged 14 min ago
        self.assertIsNotNone(self.run_hook(T0 + 60 + 62 * 60))

    def test_publish_resets_the_clock(self):
        self.add(prompt(T0), published(T0 + 25 * 60))
        self.assertIsNone(self.run_hook(T0 + 40 * 60))

    def test_no_page_yet_asks_to_publish_one(self):
        self.add(prompt(T0), tool(T0 + 10, "Edit", file_path=self.repo_file))
        msg = self.run_hook(T0 + 31 * 60)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("No status page yet", msg)

    def test_side_session_uses_parent_page_from_brief(self):
        self.add(prompt(T0, f"Fix the feed. Status page: {PARENT}"), tool(T0 + 10, "Agent", prompt="x"))
        msg = self.run_hook(T0 + 31 * 60)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(PARENT, msg)
        self.assertIn("only this work's lines", msg)

    def test_own_page_beats_brief_link(self):
        self.add(prompt(T0, f"status: {PARENT}"), published(T0 + 60), tool(T0 + 70, "Edit", file_path=self.repo_file))
        msg = self.run_hook(T0 + 40 * 60)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(URL, msg)
        self.assertNotIn(PARENT, msg)

    def test_subagent_calls_ignored(self):
        self.add(prompt(T0))
        self.assertIsNone(self.run_hook(T0 + 90 * 60, agent_id="a1"))

    def test_stop_blocks_once_when_work_after_publish(self):
        self.add(prompt(T0), published(T0 + 60), tool(T0 + 120, "Bash", command="gh pr merge 5 --squash"))
        out = self.run_hook(T0 + 300, event="Stop")
        self.assertEqual(out["decision"], "block")
        self.assertIn(URL, out["reason"])
        self.assertIsNone(self.run_hook(T0 + 400, event="Stop", stop_hook_active=True))

    def test_stop_allows_when_page_published_after_work(self):
        self.add(prompt(T0), tool(T0 + 60, "Edit", file_path=self.repo_file), published(T0 + 120))
        self.assertIsNone(self.run_hook(T0 + 300, event="Stop"))

    def test_stop_ignores_scratch_edits_and_plain_answers(self):
        self.add(prompt(T0), published(T0 + 10), prompt(T0 + 100, "what is X?"),
                 tool(T0 + 110, "Write", file_path="/tmp/scratch.html"), tool(T0 + 120, "Bash", command="git log"))
        self.assertIsNone(self.run_hook(T0 + 300, event="Stop"))

    def test_stop_short_turn_without_page_is_silent(self):
        self.add(prompt(T0), tool(T0 + 60, "Edit", file_path=self.repo_file))
        self.assertIsNone(self.run_hook(T0 + 300, event="Stop"))

    def test_stop_long_turn_without_page_asks_for_one(self):
        self.add(prompt(T0), tool(T0 + 60, "Agent", prompt="build it"))
        out = self.run_hook(T0 + 45 * 60, event="Stop")
        self.assertIn("No status page yet", out["reason"])

    def test_new_prompt_rearms_stop(self):
        self.add(prompt(T0), published(T0 + 10), tool(T0 + 20, "Bash", command="git commit -m x"))
        self.assertIsNotNone(self.run_hook(T0 + 30, event="Stop"))
        self.add(prompt(T0 + 100), tool(T0 + 120, "Bash", command="git commit -m y"))
        self.assertIsNotNone(self.run_hook(T0 + 130, event="Stop"))

    def test_incremental_reads_and_truncation(self):
        self.add(prompt(T0), published(T0 + 10))
        self.run_hook(T0 + 20)
        open(self.path, "w").close()  # transcript rewritten
        self.add(prompt(T0 + 1000), tool(T0 + 1010, "Edit", file_path=self.repo_file))
        self.assertIn("No status page yet",
                      self.run_hook(T0 + 1000 + 31 * 60)["hookSpecificOutput"]["additionalContext"])

    def test_report_artifact_is_not_the_status_page(self):
        self.add(prompt(T0), published(T0 + 10, url=PARENT, path="/tmp/report.html"),
                 tool(T0 + 20, "Edit", file_path=self.repo_file))
        msg = self.run_hook(T0 + 31 * 60)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn(PARENT, msg)
        self.assertIn("No status page yet", msg)

    def test_unrelated_link_in_prompt_is_not_the_page(self):
        self.add(prompt(T0, f"look at this design {PARENT}"), tool(T0 + 10, "Edit", file_path=self.repo_file))
        self.assertIsNone(self.run_hook(T0 + 300, event="Stop"))

    def test_published_text_in_other_tool_output_ignored(self):
        self.add(prompt(T0), tool(T0 + 10, "Bash", tid="b", command="cat log"),
                 result(T0 + 11, f"Published x at {PARENT}", "b"), tool(T0 + 20, "Edit", file_path=self.repo_file))
        self.assertIsNone(self.run_hook(T0 + 300, event="Stop"))

    def test_task_notification_does_not_rearm_stop(self):
        self.add(prompt(T0), published(T0 + 10), tool(T0 + 20, "Bash", command="git commit -m x"))
        self.assertIsNotNone(self.run_hook(T0 + 30, event="Stop"))
        self.add(prompt(T0 + 100, "<task-notification>agent done</task-notification>"))
        self.assertIsNone(self.run_hook(T0 + 130, event="Stop"))

    def test_work_after_block_reblocks_once(self):
        self.add(prompt(T0), published(T0 + 10), tool(T0 + 20, "Edit", file_path=self.repo_file))
        self.assertIsNotNone(self.run_hook(T0 + 30, event="Stop"))
        self.add(tool(T0 + 40, "Bash", command="gh pr merge 1 --squash"))
        self.assertIsNotNone(self.run_hook(T0 + 50, event="Stop", stop_hook_active=True))
        self.assertIsNone(self.run_hook(T0 + 60, event="Stop", stop_hook_active=True))

    def test_read_only_long_turn_no_nudge(self):
        self.add(prompt(T0), tool(T0 + 10, "Bash", command="ls"))
        self.assertIsNone(self.run_hook(T0 + 90 * 60))

    def test_cloud_fallback_in_stop_reason(self):
        self.add(prompt(T0), tool(T0 + 60, "Agent", prompt="build it"))
        self.assertIn("PR description", self.run_hook(T0 + 45 * 60, event="Stop")["reason"])

    def test_bad_input_is_silent(self):
        self.assertIsNone(hook.main({"transcript_path": "/nope"}))


if __name__ == "__main__":
    unittest.main()
