import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOOK = str(Path(__file__).resolve().parents[2] / "cloud-kit" / "hooks" / "chief-cloud-report.py")
TOKEN = "cloudtok-SECRET-0123456789abcdef"


class Capture(BaseHTTPRequestHandler):
    hits = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        Capture.hits.append({"auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(n))})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


class Hang(BaseHTTPRequestHandler):
    def do_POST(self):
        import time
        time.sleep(10)

    def log_message(self, *a):
        pass


def serve(handler):
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/"


def run(event, home, token=TOKEN, url=None, extra=None, session="s1", transcript=None):
    env = {"PATH": os.environ["PATH"], "HOME": home}
    if token is not None:
        env["CHIEF_INGEST_CLOUD_TOKEN"] = token
    if url:
        env["CHIEF_INGEST_URL"] = url
    env.update(extra or {})
    payload = {"hook_event_name": event, "session_id": session, "cwd": home}
    if transcript:
        payload["transcript_path"] = transcript
    return subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=20)


class ChiefCloudReport(unittest.TestCase):
    def setUp(self):
        Capture.hits = []
        self.home = tempfile.mkdtemp()
        self.srv, self.url = serve(Capture)

    def tearDown(self):
        self.srv.shutdown()

    def test_no_token_is_silent_noop(self):
        for tok in (None, "", "  "):
            r = run("SessionStart", self.home, token=tok, url=self.url)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(Capture.hits, [])

    def test_posts_run_start_as_cloud_with_bearer(self):
        r = run("SessionStart", self.home, url=self.url)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(len(Capture.hits), 1)
        h = Capture.hits[0]
        self.assertEqual(h["auth"], "Bearer " + TOKEN)
        self.assertEqual(h["body"]["op"], "work")
        ev = h["body"]["event"]
        self.assertEqual((ev["event"], ev["runs_on"], ev["session_id"]), ("run_start", "cloud", "s1"))

    def test_session_end_is_run_end(self):
        run("SessionEnd", self.home, url=self.url)
        self.assertEqual(Capture.hits[0]["body"]["event"]["event"], "run_end")

    def test_never_claims_laptop_or_server(self):
        for e in ("SessionStart", "Stop", "SessionEnd"):
            run(e, self.home, url=self.url, session="x" + e, extra={"CLAUDE_RUNS_ON": "laptop"})
        self.assertTrue(all(h["body"]["event"]["runs_on"] == "cloud" for h in Capture.hits))

    def test_token_never_printed(self):
        r = run("SessionStart", self.home, url="http://127.0.0.1:1/")
        self.assertNotIn(TOKEN, r.stdout + r.stderr)
        r = run("Stop", self.home, url=self.url)
        self.assertNotIn(TOKEN, r.stdout + r.stderr)
        self.assertNotIn(TOKEN, json.dumps(Capture.hits[0]["body"]))

    def test_heartbeat_throttled_per_session(self):
        run("Stop", self.home, url=self.url)
        run("Stop", self.home, url=self.url)
        self.assertEqual(len(Capture.hits), 1)
        run("Stop", self.home, url=self.url, session="other")
        self.assertEqual(len(Capture.hits), 2)

    def _transcript(self, text):
        p = os.path.join(self.home, "t.jsonl")
        with open(p, "w") as f:
            f.write(json.dumps({"type": "user", "message": {"content": "USER-MESSAGE-BODY"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
        return p

    def test_register_state_per_event(self):
        for i, (e, want) in enumerate([("SessionStart", "working"), ("UserPromptSubmit", "working"), ("Stop", "waiting"), ("Notification", "waiting"), ("SessionEnd", "done")]):
            run(e, self.home, url=self.url, session="st%d" % i)
            self.assertEqual(Capture.hits[-1]["body"]["event"]["chat_state"], want, e)

    def test_state_change_posts_inside_throttle_window(self):
        run("UserPromptSubmit", self.home, url=self.url)
        run("Stop", self.home, url=self.url)
        run("Stop", self.home, url=self.url)
        self.assertEqual([h["body"]["event"]["chat_state"] for h in Capture.hits], ["working", "waiting"])

    def test_last_line_is_last_assistant_text_clipped_never_user_text(self):
        t = self._transcript("Shipped the register. " + "x" * 400)
        run("Stop", self.home, url=self.url, transcript=t)
        ev = Capture.hits[0]["body"]["event"]
        self.assertTrue(ev["last_line"].startswith("Shipped the register."))
        self.assertLessEqual(len(ev["last_line"]), 200)
        self.assertNotIn("USER-MESSAGE-BODY", json.dumps(Capture.hits[0]["body"]))

    def test_secret_in_last_line_is_scrubbed(self):
        key = "sk" + "-fake-" + "A1b2C3d4E5f6G7h8"  # built in pieces: not a real key
        t = self._transcript("set SOME_API_KEY=%s then Bearer abc.def.ghi done" % key)
        run("Stop", self.home, url=self.url, transcript=t)
        body = json.dumps(Capture.hits[0]["body"])
        self.assertNotIn(key, body)
        self.assertNotIn("abc.def.ghi", body)
        self.assertIn("[redacted]", body)

    def test_session_end_sends_no_last_line(self):
        t = self._transcript("bye")
        run("SessionEnd", self.home, url=self.url, transcript=t)
        self.assertNotIn("last_line", Capture.hits[0]["body"]["event"])

    def test_missing_transcript_is_fine(self):
        r = run("Stop", self.home, url=self.url, transcript="/nonexistent/t.jsonl")
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        self.assertNotIn("last_line", Capture.hits[0]["body"]["event"])

    def test_unreachable_exits_zero_quietly(self):
        r = run("SessionStart", self.home, url="http://127.0.0.1:1/")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_hung_server_times_out_fast(self):
        import time
        srv, url = serve(Hang)
        try:
            t = time.time()
            r = run("SessionStart", self.home, url=url)
            self.assertEqual(r.returncode, 0)
            self.assertLess(time.time() - t, 5)
        finally:
            srv.shutdown()

    def test_skips_chief_runner_and_opt_out(self):
        for extra in ({"CHIEF_RUNNER": "1"}, {"CHIEF_JOB_ID": "j"}, {"CHIEF_LEDGER_SKIP": "1"}):
            run("SessionStart", self.home, url=self.url, extra=extra)
        self.assertEqual(Capture.hits, [])

    def test_bad_stdin_exits_zero(self):
        env = {"PATH": os.environ["PATH"], "HOME": self.home, "CHIEF_INGEST_CLOUD_TOKEN": TOKEN, "CHIEF_INGEST_URL": self.url}
        r = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True, env=env)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))


    def test_override_url_cannot_leak_token_to_cleartext_or_other_schemes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("chief_cloud_report", HOOK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for bad in ("http://evil.example/x", "http://10.0.0.5/x", "file:///etc/passwd", "ftp://h/x", "https://", "", None):
            self.assertEqual(mod.ingest_url(bad), mod.DEFAULT_URL, bad)
        for ok in ("https://example.test/fn", "http://127.0.0.1:9/x", "http://localhost:9/x"):
            self.assertEqual(mod.ingest_url(ok), ok)

    def test_disallowed_override_posts_to_default_not_override(self):
        import importlib.util, io
        from unittest import mock
        spec = importlib.util.spec_from_file_location("chief_cloud_report", HOOK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bad_hits = []

        class Bad(BaseHTTPRequestHandler):
            def do_POST(self):
                bad_hits.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        bad_srv = HTTPServer(("127.0.0.2", 0), Bad)
        threading.Thread(target=bad_srv.serve_forever, daemon=True).start()
        try:
            mod.DEFAULT_URL = self.url
            env = {"HOME": self.home, "CHIEF_INGEST_CLOUD_TOKEN": TOKEN, "CHIEF_INGEST_URL": f"http://127.0.0.2:{bad_srv.server_port}/"}
            stdin = io.StringIO(json.dumps({"hook_event_name": "SessionStart", "session_id": "s9", "cwd": self.home}))
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "stdin", stdin):
                mod.main()
        finally:
            bad_srv.shutdown()
        self.assertEqual(bad_hits, [])
        self.assertEqual(len(Capture.hits), 1)
        self.assertEqual(Capture.hits[0]["body"]["event"]["session_id"], "s9")


if __name__ == "__main__":
    unittest.main()
