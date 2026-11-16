"""Tests for cloud-kit/hooks/correction-checks.py and corrections_lib.py.

Every check in corrections.json carries bad examples (must fire) and good examples (must stay quiet);
this file runs all of them, then tests the four hook events end to end. Credential examples are
written as {{fake:<kind>}} and expanded at runtime, so no secret-shaped string is committed.
"""
import importlib.util, io, json, os, sys, tempfile, unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOKS = os.path.join(ROOT, "cloud-kit", "hooks")
sys.path.insert(0, HOOKS)
import corrections_lib as lib  # noqa: E402

spec = importlib.util.spec_from_file_location("correction_checks", os.path.join(HOOKS, "correction-checks.py"))
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

REG = lib.load()
OWN = [e for e in REG if e["class"] == "check" and not e["check"].startswith("external:")]


def run_example(entry, ex):
    ex = {"text": ex} if isinstance(ex, str) else ex
    text = lib.expand_fakes(ex["text"])
    ctx = dict(ex.get("ctx") or {})
    hits = []
    for surface in lib.surfaces(entry):
        if (surface == "write") != ("path" in ex):
            continue
        if "path" in ex:
            ctx["path"] = ex["path"]
        hits += lib.evaluate(surface, text, ctx, registry=[entry])
    return hits


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"HOME": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class ExamplesTest(TempHome):
    def test_every_own_check_has_examples(self):
        for e in OWN:
            with self.subTest(e["id"]):
                self.assertTrue(e.get("bad"), "needs a bad example")
                self.assertTrue(e.get("good"), "needs a good example")
                self.assertIn(e["action"], ("block", "ask", "warn", "context"))
                self.assertTrue(e.get("message"))

    def test_bad_examples_fire(self):
        for e in OWN:
            for ex in e["bad"]:
                with self.subTest(id=e["id"], ex=ex):
                    self.assertTrue(run_example(e, ex), "should fire")

    def test_good_examples_stay_quiet(self):
        for e in OWN:
            for ex in e["good"]:
                with self.subTest(id=e["id"], ex=ex):
                    self.assertEqual(run_example(e, ex), [], "should stay quiet")

    def test_regex_checks_compile(self):
        for e in OWN:
            if e["check"] == "regex":
                lib._rx(e)
            else:
                self.assertIn(e["check"][3:], lib.FUNCTIONS)

    def test_brief_minimum_checks_exist(self):
        ids = {e["id"] for e in OWN}
        for need in ("unverified-url-in-reply", "openrouter-outside-os", "brand-x-for-y-copy",
                     "time-estimate-in-reply", "secret-pasted-in-prompt", "secret-in-tool-input", "status-in-chat"):
            self.assertIn(need, ids)


class EngineTest(TempHome):
    def test_override_skips_one_check(self):
        e = next(x for x in OWN if x["id"] == "empty-commit-ci-restart")
        self.assertTrue(lib.evaluate("bash", "git commit --allow-empty -m x", {}, registry=[e]))
        self.assertFalse(lib.evaluate("bash", "git commit --allow-empty -m x  # correction-ok: empty-commit-ci-restart",
                                      {}, registry=[e]))

    def test_secret_detail_never_echoes_value(self):
        key = lib.expand_fakes("{{fake:anthropic}}")
        hits = lib.evaluate("reply", f"key: {key}", {})
        self.assertTrue(hits)
        self.assertNotIn(key, lib.describe(hits))

    def test_anon_jwt_is_not_a_secret(self):
        self.assertEqual(lib.find_secrets(lib.expand_fakes("{{fake:anon-jwt}}")), [])
        self.assertEqual(lib.find_secrets(lib.expand_fakes("{{fake:service-jwt}}")), ["Supabase service-role JWT"])

    def test_broken_check_is_skipped(self):
        broken = {"id": "x", "class": "check", "surface": "bash", "action": "block", "check": "fn:missing", "message": "m"}
        self.assertEqual(lib.evaluate("bash", "anything", {}, registry=[broken]), [])

    def test_registry_files_are_never_checked(self):
        text = lib.expand_fakes("x = '{{fake:openrouter}}'")
        self.assertEqual(lib.evaluate("write", text, {"path": "/r/cloud-kit/hooks/corrections.json"}), [])
        self.assertTrue(lib.evaluate("write", text, {"path": "/r/src/llm.ts"}))

    def test_hits_logged_without_text(self):
        hits = lib.evaluate("bash", "git commit --allow-empty -m retrigger", {})
        lib.log_hits(hits, "bash")
        with open(os.path.join(self.tmp.name, ".claude", "state", "corrections-hits.jsonl")) as f:
            log = f.read()
        row = json.loads(log.splitlines()[0])
        self.assertEqual(row["id"], "empty-commit-ci-restart")
        self.assertNotIn("retrigger", log)

    def test_code_in_reply_is_ignored(self):
        self.assertEqual(lib.evaluate("reply", "Starter:\n```\nThis will take about 2 hours\n```", {}), [])


def write_transcript(path, entries):
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def prompt(text, uuid="p1"):
    return {"type": "user", "uuid": uuid, "message": {"role": "user", "content": text}}


def tool_call(mid, tid, name, inp, text=None):
    content = ([{"type": "text", "text": text}] if text else []) + [{"type": "tool_use", "id": tid, "name": name, "input": inp}]
    return {"type": "assistant", "uuid": mid + tid, "message": {"id": mid, "role": "assistant", "content": content}}


def result(tid, text):
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": text}]}}


def reply(text, mid="mfinal"):
    return {"type": "assistant", "uuid": mid, "message": {"id": mid, "role": "assistant", "content": [{"type": "text", "text": text}]}}


class EventTest(TempHome):
    def call(self, payload):
        buf = io.StringIO()
        with redirect_stdout(buf), mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
            out = hook.main(json.load(sys.stdin))
        return out

    def transcript(self, entries):
        p = os.path.join(self.tmp.name, "t.jsonl")
        write_transcript(p, entries)
        return p

    # PreToolUse
    def test_pre_tool_blocks(self):
        out = self.call({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                         "tool_input": {"command": "git commit --allow-empty -m 'ci: kick'"}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("empty-commit-ci-restart", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_pre_tool_asks(self):
        out = self.call({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                         "tool_input": {"command": "git push --force origin main"}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_pre_tool_write_and_multiedit(self):
        out = self.call({"hook_event_name": "PreToolUse", "tool_name": "MultiEdit",
                         "tool_input": {"file_path": "src/pages/Home.tsx", "edits": [{"old_string": "a", "new_string": "The Uber for coaches"}]}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_pre_tool_quiet_on_good(self):
        self.assertIsNone(self.call({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                     "tool_input": {"command": "npm test"}}))
        self.assertIsNone(self.call({"hook_event_name": "PreToolUse", "tool_name": "Read",
                                     "tool_input": {"file_path": "x"}}))

    def test_pre_tool_reason_has_no_secret(self):
        key = lib.expand_fakes("{{fake:github}}")
        out = self.call({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                         "tool_input": {"command": f"curl -H 'Authorization: token {key}' https://api.github.com"}})
        self.assertNotIn(key, json.dumps(out))

    # PostToolUse
    def test_post_tool_warns_commit_format(self):
        out = self.call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "agent_id": "a1",
                         "tool_input": {"command": "git commit -m 'stuff'"}})
        self.assertIn("commit-message-format", out["hookSpecificOutput"]["additionalContext"])

    def test_narration_nudged_once_per_turn(self):
        t = self.transcript([prompt("build it"), tool_call("m1", "t1", "Bash", {"command": "ls"}, text="Let me look around.")])
        base = {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"},
                "transcript_path": t, "session_id": "s1", "tool_use_id": "t1"}
        first = self.call(base)
        self.assertIn("narration-while-working", first["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.call(base))

    def test_no_narration_quiet(self):
        t = self.transcript([prompt("build it"), tool_call("m1", "t1", "Bash", {"command": "ls"})])
        self.assertIsNone(self.call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"},
                                     "transcript_path": t, "session_id": "s1", "tool_use_id": "t1"}))

    # Stop
    def stop(self, entries, **kw):
        return self.call(dict({"hook_event_name": "Stop", "transcript_path": self.transcript(entries), "session_id": "s"}, **kw))

    def test_stop_blocks_time_estimate(self):
        out = self.stop([prompt("go"), reply("Built. The migration will take about 2 hours.")])
        self.assertEqual(out["decision"], "block")
        self.assertIn("time-estimate-in-reply", out["reason"])

    def test_stop_respects_stop_hook_active_and_subagents(self):
        entries = [prompt("go"), reply("This will take about 2 hours.")]
        self.assertIsNone(self.stop(entries, stop_hook_active=True))
        self.assertIsNone(self.stop(entries, agent_id="sub"))

    def test_stop_url_seen_in_tool_result_is_fine(self):
        url = "https://docs.acme-vendor.io/setup"
        ok = [prompt("go"), tool_call("m1", "t1", "WebFetch", {"url": url}), result("t1", "page"), reply(f"Steps: {url}")]
        self.assertIsNone(self.stop(ok))
        bad = [prompt("go"), reply("Steps: https://docs.acme-vendor.io/other")]
        self.assertIn("unverified-url-in-reply", self.stop(bad)["reason"])

    def test_stop_status_in_chat_only_with_page(self):
        status = "**Done:** importer\n**Remaining:** none"
        with_page = [prompt("go"), tool_call("m1", "t1", "Artifact", {"file_path": "/s/status.html"}), result("t1", "ok"), reply(status)]
        self.assertIn("status-in-chat", self.stop(with_page)["reason"])
        self.assertIsNone(self.stop([prompt("go"), reply(status)]))

    def test_stop_only_checks_text_after_last_tool(self):
        entries = [prompt("go"), tool_call("m1", "t1", "Bash", {"command": "ls"}, text="Will take about 2 hours."),
                   result("t1", "ok"), reply("Shipped.")]
        self.assertIsNone(self.stop(entries))

    def test_stop_falls_back_to_last_assistant_message(self):
        out = self.call({"hook_event_name": "Stop", "last_assistant_message": "Want me to run ship-check?"})
        self.assertIn("permission-question-in-reply", out["reason"])

    # UserPromptSubmit
    def test_prompt_with_secret_adds_context(self):
        out = self.call({"hook_event_name": "UserPromptSubmit", "prompt": lib.expand_fakes("key {{fake:groq}}")})
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("vault set", ctx)
        self.assertNotIn(lib.expand_fakes("{{fake:groq}}"), ctx)
        self.assertIsNone(self.call({"hook_event_name": "UserPromptSubmit", "prompt": "ship it"}))

    def test_bad_payload_is_silent(self):
        self.assertIsNone(self.call({"hook_event_name": "Nope"}))
        self.assertIsNone(self.call({"hook_event_name": "Stop", "transcript_path": "/does/not/exist"}))


class PluginModeTest(TempHome):
    def test_plugin_mode_skips_when_installed_in_settings(self):
        os.makedirs(os.path.join(self.tmp.name, ".claude"))
        with open(os.path.join(self.tmp.name, ".claude", "settings.json"), "w") as f:
            json.dump({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/correction-checks.py"}]}]}}, f)
        self.assertTrue(hook.installed_in_settings())

    def test_plugin_mode_runs_when_not_installed(self):
        self.assertFalse(hook.installed_in_settings())


if __name__ == "__main__":
    unittest.main()
