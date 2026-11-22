"""Tests for the heavy-job gate: bin/heavy-run, hooks/heavy-gate.py (rewrite), hooks/heavy-ledger-hook.py
(brake ledger nudge) and the job-grouped brake in bin/memory-guard.py.

Run: python3 -m unittest discover -s tests/hooks -v
Everything runs against a throwaway state dir (MEMORY_GUARD_STATE_DIR); no real process is killed.
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, time, unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
HOOKS = os.path.join(ROOT, "cloud-kit", "hooks")
BIN = os.path.join(ROOT, "cloud-kit", "bin")
HEAVY_RUN = os.path.join(BIN, "heavy-run")
sys.path.insert(0, HOOKS)
import heavy_lib as hl  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = {**os.environ, "MEMORY_GUARD_STATE_DIR": os.path.join(self.tmp, "state"),
                    "MEMORY_GUARD_LOG": os.path.join(self.tmp, "mg.log"), "HEAVY_RUN_POLL_S": "0.2",
                    "HEAVY_RUN_SLOTS": "1", "HEAVY_RUN_BIN": HEAVY_RUN}
        for k in ("MEMORY_GUARD_STATE_DIR", "MEMORY_GUARD_LOG", "HEAVY_RUN_POLL_S", "HEAVY_RUN_SLOTS", "HEAVY_RUN_BIN"):
            p = mock.patch.dict(os.environ, {k: self.env[k]})
            p.start()
            self.addCleanup(p.stop)
        self.wt = os.path.join(self.tmp, "wt")
        os.makedirs(self.wt)
        subprocess.run(["git", "init", "-q", self.wt], check=True)

    def heavy(self, *args, budget="20", extra_env=None, cwd=None, wait=True):
        p = subprocess.Popen([sys.executable, HEAVY_RUN, f"--budget={budget}", *args], cwd=cwd or self.wt,
                             env={**self.env, **(extra_env or {})}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.communicate() + (p.returncode,) if wait else p


class RewriteTest(Base):
    def rw(self, cmd):
        return hl.rewrite_command(cmd, 100)

    def test_bare_heavy_is_wrapped(self):
        new, _ = self.rw("npx jest src/a")
        self.assertEqual(new, f"{HEAVY_RUN} --budget=100 npx jest src/a")

    def test_cd_and_pipe(self):
        new, _ = self.rw("cd x && npx tsc --noEmit 2>&1 | tail -5")
        self.assertEqual(new, f"cd x && {HEAVY_RUN} --budget=100 npx tsc --noEmit 2>&1 | tail -5")

    def test_vault_run_keeps_working(self):
        new, _ = self.rw("vault run --keys A -- npm test")
        self.assertEqual(new, f"vault run --keys A -- {HEAVY_RUN} --budget=100 npm test")

    def test_env_assignments_and_rtk(self):
        self.assertEqual(self.rw("CI=1 npx jest")[0], f"CI=1 {HEAVY_RUN} --budget=100 npx jest")
        self.assertEqual(self.rw("rtk jest a")[0], f"{HEAVY_RUN} --budget=100 rtk jest a")

    def test_already_wrapped_and_non_heavy_untouched(self):
        for cmd in (f"{HEAVY_RUN} npx jest", "heavy-run npm test", "git status", "ls && echo hi",
                    'git commit -m "fix npx jest; npm test"', "echo 'npx tsc'", "npx jest --help", "tsc --version",
                    "grep -r jest src", "npm install"):
            self.assertEqual(self.rw(cmd), (None, None), cmd)

    def test_bash_c_wrapped_whole(self):
        new, _ = self.rw("bash -c 'cd a && npx jest'")
        self.assertEqual(new, f"{HEAVY_RUN} --budget=100 bash -c 'cd a && npx jest'")

    def test_heredoc_with_heavy_is_denied_with_fix(self):
        new, deny = self.rw("cat <<EOF > f\nx\nEOF\nnpm test")
        self.assertIsNone(new)
        self.assertIn("heavy-run", deny)
        self.assertEqual(self.rw("cat <<EOF > f\nhello\nEOF"), (None, None))

    def test_missing_binary_is_noop(self):
        with mock.patch.dict(os.environ, {"HEAVY_RUN_BIN": "/nonexistent/heavy-run"}):
            self.assertEqual(hl.rewrite_command("npx jest", 100), (None, None))

    def test_hook_output_for_bash_and_ctx(self):
        for tool, inp, key in (("Bash", {"command": "npx jest"}, "command"),
                               ("mcp__plugin_context-mode_context-mode__ctx_execute", {"language": "shell", "code": "npm test"}, "code")):
            r = subprocess.run([sys.executable, os.path.join(HOOKS, "heavy-gate.py")], env=self.env, text=True,
                               input=json.dumps({"tool_name": tool, "tool_input": inp}), capture_output=True)
            out = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]
            self.assertIn("heavy-run", out[key])
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "heavy-gate.py")], env=self.env, text=True, capture_output=True,
                           input=json.dumps({"tool_name": "mcp__plugin_context-mode_context-mode__ctx_batch_execute",
                                             "tool_input": {"commands": [{"label": "a", "command": "git log"}, {"label": "b", "command": "npx eslint ."}]}}))
        cmds = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]["commands"]
        self.assertEqual(cmds[0]["command"], "git log")
        self.assertIn("heavy-run", cmds[1]["command"])
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "heavy-gate.py")], env=self.env, text=True, capture_output=True,
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
        self.assertEqual(r.stdout, "")

    def test_cap_workers(self):
        self.assertEqual(hl.cap_workers(["npx", "jest", "a"]), ["npx", "jest", "a", "--maxWorkers=2"])
        self.assertEqual(hl.cap_workers(["jest", "--runInBand"]), ["jest", "--runInBand"])
        self.assertEqual(hl.cap_workers(["jest", "--maxWorkers=1"]), ["jest", "--maxWorkers=1"])
        self.assertEqual(hl.cap_workers(["npm", "test"]), ["npm", "test"])
        self.assertEqual(hl.cap_workers(["tsc"]), ["tsc"])


class GateTest(Base):
    def test_slots_full_waits_then_runs(self):
        first = self.heavy("sleep", "2", wait=False)
        time.sleep(0.6)
        t0 = time.time()
        out, err, rc = self.heavy("echo", "second-ran")
        waited = time.time() - t0
        first.communicate()
        self.assertEqual(rc, 0)
        self.assertIn("second-ran", out)
        self.assertIn("waiting your turn", err)
        self.assertGreater(waited, 1.0)  # it really waited for the slot

    def test_two_slots_run_in_parallel(self):
        t0 = time.time()
        a = self.heavy("sleep", "1.5", wait=False, extra_env={"HEAVY_RUN_SLOTS": "2"})
        b = self.heavy("sleep", "1.5", wait=False, extra_env={"HEAVY_RUN_SLOTS": "2"})
        a.communicate(), b.communicate()
        self.assertLess(time.time() - t0, 2.8)

    def test_stale_lock_and_ticket_recovered(self):
        gate = os.path.join(self.env["MEMORY_GUARD_STATE_DIR"], "gate")
        os.makedirs(os.path.join(gate, "queue"))
        open(os.path.join(gate, "slot-0.lock"), "w").write('{"pid": 999999, "cmd": "dead job"}')  # holder long gone
        stale = os.path.join(gate, "queue", "00000000000000000001-dead.t")
        open(stale, "w").close()
        os.utime(stale, (time.time() - 3600, time.time() - 3600))
        out, _err, rc = self.heavy("echo", "ok")
        self.assertEqual((rc, out.strip()), (0, "ok"))
        self.assertFalse(os.path.exists(stale))

    def test_budget_exhausted_exits_75_and_keeps_place(self):
        first = self.heavy("sleep", "3", wait=False)
        time.sleep(0.5)
        _o, err, rc = self.heavy("echo", "x", budget="1")
        self.assertEqual(rc, 75)
        self.assertIn("Re-run the same command", err)
        self.assertEqual(len(hl._live_tickets()), 1)  # place in line kept
        first.communicate()

    def test_critical_pressure_holds_new_jobs_while_one_runs(self):
        pf = os.path.join(self.tmp, "pressure")
        open(pf, "w").write("4 9000")
        env = {"HEAVY_RUN_PRESSURE_FILE": pf, "HEAVY_RUN_SLOTS": "2"}
        first = self.heavy("sleep", "4", wait=False, extra_env=env)
        time.sleep(0.6)
        second = self.heavy("echo", "late", wait=False, extra_env=env)
        time.sleep(1.5)
        self.assertIsNone(second.poll())  # held: a free slot exists but pressure is critical
        open(pf, "w").write("1 1000")
        out, _ = second.communicate(timeout=10)
        first.communicate()
        self.assertIn("late", out)

    def test_pressure_does_not_starve_an_idle_gate(self):
        pf = os.path.join(self.tmp, "pressure")
        open(pf, "w").write("4 9000")
        out, _e, rc = self.heavy("echo", "idle-ok", extra_env={"HEAVY_RUN_PRESSURE_FILE": pf})
        self.assertEqual((rc, out.strip()), (0, "idle-ok"))

    def test_exit_code_passes_through(self):
        self.assertEqual(self.heavy("sh", "-c", "exit 3")[2], 3)


class LedgerTest(Base):
    def kill(self, **kw):
        return hl.record_kill(kw.get("cwd", self.wt), kw.get("command", "npx jest src/a"), 123, 500, 900, kw.get("hr"))

    def hook(self, event, cwd, session="s1", transcript=None):
        payload = {"hook_event_name": event, "session_id": session, "cwd": cwd}
        if transcript:
            payload["transcript_path"] = transcript
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "heavy-ledger-hook.py")], env=self.env, text=True,
                           input=json.dumps(payload), capture_output=True)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def transcript(self, text):
        p = os.path.join(self.tmp, "t.jsonl")
        open(p, "w").write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
        return p

    def test_killed_job_nudges_owner_only_and_clears_after_green_rerun(self):
        entry = self.kill()
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        subprocess.run(["git", "init", "-q", other], check=True)
        self.assertIsNone(self.hook("UserPromptSubmit", other))  # a different worktree is not told
        sub = os.path.join(self.wt, "pkg")
        os.makedirs(sub)
        out = self.hook("UserPromptSubmit", sub)  # inside the worktree counts as owner
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("memory brake stopped", ctx)
        self.assertIn("heavy-run", ctx)
        # PostToolUse nudges once per entry per session
        self.assertIsNotNone(self.hook("PostToolUse", self.wt, session="s2"))
        self.assertIsNone(self.hook("PostToolUse", self.wt, session="s2"))
        # a matching green heavy-run in that worktree closes the entry
        _o, _e, rc = self.heavy("sh", "-c", "exit 1")
        self.assertEqual(len(hl.open_entries()), 1)
        self.assertEqual(self.heavy("true")[2], 0)  # unrelated command: stays open
        self.assertEqual([e["id"] for e in hl.open_entries()], [entry["id"]])
        script = os.path.join(self.wt, "jest")
        open(script, "w").write("#!/bin/sh\nexit 0\n")
        os.chmod(script, 0o755)
        self.assertEqual(self.heavy("./jest")[2], 0)
        self.assertEqual(hl.open_entries(), [])
        self.assertIsNone(self.hook("UserPromptSubmit", self.wt))

    def test_stop_refuses_pass_claim_while_open(self):
        self.kill()
        out = self.hook("Stop", self.wt, transcript=self.transcript("All tests pass, typecheck clean."))
        self.assertEqual(out["decision"], "block")
        self.assertIn("re-run", out["reason"].lower())
        self.assertIsNone(self.hook("Stop", self.wt, transcript=self.transcript("Refactored the parser.")))
        self.assertIsNone(self.hook("Stop", os.path.join(self.tmp), transcript=self.transcript("All tests pass")))
        self.hook("Stop", self.wt, transcript=self.transcript("tests pass"))  # 2nd block
        self.assertIsNone(self.hook("Stop", self.wt, transcript=self.transcript("tests pass")))  # then allowed: no deadlock

    def test_entries_expire_after_48h_with_log_line(self):
        e = self.kill()
        events = hl.read_events()
        events[0]["time"] = int(time.time()) - 49 * 3600
        open(hl.ledger_path(), "w").write("".join(json.dumps(x) + "\n" for x in events))
        self.assertEqual(hl.open_entries(), [])
        self.assertIn(f"expired un-rerun kill id={e['id']}", open(self.env["MEMORY_GUARD_LOG"]).read())
        self.assertEqual([x["event"] for x in hl.read_events()], ["kill", "expired"])
        self.assertEqual(hl.open_entries(), [])  # and does not log again

    def test_heavy_run_requeues_a_job_the_brake_killed(self):
        # The child "gets killed by the brake": it writes a ledger entry naming this heavy-run, then dies.
        marker = os.path.join(self.tmp, "ran-once")
        script = os.path.join(self.tmp, "job.sh")
        # heavy-run pid isn't known to the child, so use the parent pid ($PPID) via a tiny wrapper
        open(script, "w").write(
            f"#!/bin/sh\nif [ ! -f {marker} ]; then touch {marker}; "
            f"{sys.executable} -c \"import sys;sys.path.insert(0,'{HOOKS}');import heavy_lib as h;"
            f"h.record_kill('{self.wt}','{script}',1,1,1,$PPID)\"; kill -9 $$; fi\nexit 0\n")
        os.chmod(script, 0o755)
        out, err, rc = self.heavy(script, extra_env={"HEAVY_RUN_RETRY_COOLDOWN_S": "0.2"})
        self.assertEqual(rc, 0, err)
        self.assertIn("memory brake stopped", err)
        self.assertEqual(hl.open_entries(), [])  # killed -> re-queued -> green -> entry closed


class BrakeTest(Base):
    def setUp(self):
        super().setUp()
        self.mg = load(os.path.join(BIN, "memory-guard.py"), "memory_guard_under_test")
        self.mg.STATE_DIR = hl.state_dir()
        self.mg.LOG = self.env["MEMORY_GUARD_LOG"] and __import__("pathlib").Path(self.env["MEMORY_GUARD_LOG"])

    def table(self, rows):
        return {pid: (ppid, rss, cmd) for pid, ppid, rss, cmd in rows}

    def run_brake(self, rows, dry=False, free=2500):
        killed = []
        self.mg.BRAKE_FREE_MB = free
        with mock.patch.object(self.mg, "ps_table", return_value=self.table(rows)), \
                mock.patch.object(self.mg, "pid_cwd", return_value=self.wt), \
                mock.patch.object(self.mg.os, "kill", side_effect=lambda pid, sig: killed.append(pid)):
            n = self.mg.brake(dry)
        return n, killed

    ROWS = [
        (100, 1, 40, "node /x/node_modules/.bin/jest src"), (101, 100, 150, "node /x/node_modules/jest-worker/processChild.js"),
        (102, 100, 120, "node /x/node_modules/jest-worker/processChild.js"),
        (200, 1, 700, "node /x/node_modules/typescript/bin/tsc --noEmit"),
        (300, 1, 600, "node /y/node_modules/.bin/eslint ."),
        (400, 1, 30, "/Applications/Claude.app/Contents/MacOS/Claude"),
        (500, 1, 20, "python3 /Users/e/bin/heavy-run npx jest waiting-job"),  # a job waiting in the gate
    ]

    def test_kills_whole_jobs_biggest_first_only_until_enough_freed(self):
        n, killed = self.run_brake(self.ROWS, free=800)
        self.assertEqual(n, 2)  # tsc (700) then eslint (600) -> 1300 >= 800; the 310 MB jest job is spared
        self.assertEqual(killed, [200, 300])
        self.assertNotIn(100, killed)

    def test_job_is_killed_as_a_unit_and_ledgered(self):
        n, killed = self.run_brake(self.ROWS, free=99999)
        self.assertEqual(sorted(killed), [100, 101, 102, 200, 300])  # workers go with their jest parent
        self.assertNotIn(500, killed)  # the waiting heavy-run is never killed
        self.assertNotIn(400, killed)  # nor Claude
        entries = hl.open_entries()
        self.assertEqual(len(entries), 3)  # one entry per job, not per process
        jest = [e for e in entries if e["pid"] == 100][0]
        self.assertEqual((jest["worktree"], jest["kind"], jest["job_rss_mb"]), (os.path.realpath(self.wt), "jest", 310))

    def test_dry_run_kills_and_records_nothing(self):
        n, killed = self.run_brake(self.ROWS, dry=True)
        self.assertEqual((killed, hl.open_entries()), ([], []))
        self.assertIn("would kill job", open(self.env["MEMORY_GUARD_LOG"]).read())

    def test_heavy_run_job_keeps_its_command_in_the_ledger(self):
        rec = [{"pid": 4242, "child": 90, "cwd": self.wt, "cmd": "npm test", "slot": 0}]
        rows = [(90, 1, 10, "npm test"), (100, 90, 300, "node /x/node_modules/.bin/jest")]
        with mock.patch.object(hl, "gate_records", return_value=rec):
            self.run_brake(rows)
        e = hl.open_entries()[0]
        self.assertEqual((e["command"], e["heavy_run_pid"]), ("npm test", 4242))


if __name__ == "__main__":
    unittest.main()
