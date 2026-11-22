"""Tests for the heavy-job gate: bin/heavy-run, hooks/heavy-gate.py (rewrite), hooks/heavy-ledger-hook.py
(brake ledger nudge) and the job-grouped brake in bin/memory-guard.py.

Run: python3 -m unittest discover -s tests/hooks -v
Everything runs against a throwaway state dir (MEMORY_GUARD_STATE_DIR); no real process is killed.
"""
import importlib.util, json, os, shutil, signal, subprocess, sys, tempfile, time, unittest
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

    def test_heredoc_read_by_a_shell_is_denied_with_fix(self):
        new, deny = self.rw("bash <<EOF\nnpx jest\nEOF")
        self.assertIsNone(new)
        self.assertIn("heavy-run", deny)
        self.assertEqual(self.rw("cat <<EOF > f\nhello\nEOF"), (None, None))

    def test_heredoc_text_is_not_code(self):
        # a PR body that mentions `npm test` is prose, not a heavy job
        self.assertEqual(self.rw("gh pr create --body-file - <<'EOF'\nrun npm test and npx tsc\nEOF"), (None, None))
        # ...but a real heavy command after a cat heredoc is still wrapped
        new, deny = self.rw("cat <<EOF > f\nx\nEOF\nnpx tsc")
        self.assertIsNone(deny)
        self.assertTrue(new.endswith(f"{HEAVY_RUN} --budget=100 npx tsc"), new)

    def test_watch_modes_and_npm_ci_are_not_wrapped(self):
        for cmd in ("npm ci", "npx jest --watch", "npx jest --watchAll", "tsc -w", "tsc --watch", "npx tsc -w"):
            self.assertEqual(self.rw(cmd), (None, None), cmd)

    def test_jest_w_workers_and_watchall_false_are_still_gated(self):
        for cmd in ("npx jest -w 2", "npx jest --watchAll=false", "npx jest --watch=false"):
            new, _ = self.rw(cmd)
            self.assertIn(HEAVY_RUN, new or "", cmd)

    def test_brace_group_is_wrapped(self):
        new, _ = self.rw("{ npx jest; }")
        self.assertIn(f"{HEAVY_RUN} --budget=100 npx jest", new)

    def test_has_heavy_cli_for_rtk_guard(self):
        for cmd, rc in (("npm run build", 0), ("npx next build", 0), ("npx playwright test", 0),
                        ("git status", 1), ("npm ci", 1), ("npx jest --watch", 1)):
            r = subprocess.run([sys.executable, os.path.join(HOOKS, "heavy_lib.py"), "--has-heavy"], input=cmd,
                               text=True, capture_output=True)
            self.assertEqual(r.returncode, rc, cmd)

    def test_budget_is_a_quarter_of_the_tool_timeout_capped_at_30s(self):
        gate = load(os.path.join(HOOKS, "heavy-gate.py"), "heavy_gate_under_test")
        self.assertEqual(gate.budget_for({"timeout": 120000}), 30)
        self.assertEqual(gate.budget_for({"timeout": 40000}), 10)
        self.assertEqual(gate.budget_for({}), 30)
        self.assertEqual(gate.budget_for({"run_in_background": True}), 0)

    def test_retry_safe_allowlist(self):
        for ok in ("npm test", "npx jest a", "npm run lint", "npx tsc --noEmit"):
            self.assertTrue(hl.retry_safe(ok), ok)
        for bad in ("npm run test:db", "npm run migrate", "npm run build", "npx next build", "npm run db:reset"):
            self.assertFalse(hl.retry_safe(bad), bad)

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
        # rendezvous, not timing: each job waits (up to ~10 s) for the other's file, so it only passes if both run at once
        pf = os.path.join(self.tmp, "pressure")
        open(pf, "w").write("1 1000")
        env = {"HEAVY_RUN_SLOTS": "2", "HEAVY_RUN_PRESSURE_FILE": pf}
        fa, fb = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        job = 'touch "$1"; for i in $(seq 100); do [ -f "$2" ] && exit 0; sleep 0.1; done; exit 1'
        a = self.heavy("sh", "-c", job, "x", fa, fb, wait=False, extra_env=env)
        b = self.heavy("sh", "-c", job, "x", fb, fa, wait=False, extra_env=env)
        a.communicate(), b.communicate()
        self.assertEqual((a.returncode, b.returncode), (0, 0))

    def test_slot_is_freed_when_the_job_exits_even_with_a_background_grandchild(self):
        _o, _e, rc = self.heavy("sh", "-c", "sleep 4 >/dev/null 2>&1 &")
        self.assertEqual(rc, 0)
        t0 = time.time()
        out, _e, rc = self.heavy("echo", "next", budget="2")
        self.assertEqual((rc, out.strip()), (0, "next"))
        self.assertLess(time.time() - t0, 2)

    def test_dead_owner_ticket_at_the_head_does_not_block(self):
        queue = os.path.join(self.env["MEMORY_GUARD_STATE_DIR"], "gate", "queue")
        os.makedirs(queue)
        open(os.path.join(queue, "00000000000000000001-ghost.t"), "w").write("999999")  # fresh mtime, dead owner
        first = self.heavy("sleep", "1.5", wait=False)
        time.sleep(0.4)
        out, _e, rc = self.heavy("echo", "ok", budget="10")
        first.communicate()
        self.assertEqual((rc, out.strip()), (0, "ok"))

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

    def held_until_released(self, pressure):
        pf = os.path.join(self.tmp, "pressure")
        open(pf, "w").write(pressure)
        env = {"HEAVY_RUN_PRESSURE_FILE": pf, "HEAVY_RUN_SLOTS": "2"}
        first = self.heavy("sleep", "4", wait=False, extra_env=env)
        time.sleep(0.6)
        second = self.heavy("echo", "late", wait=False, extra_env=env)
        time.sleep(1.5)
        held = second.poll() is None  # a free slot exists but the gate holds the job
        open(pf, "w").write("1 1000")
        out, _ = second.communicate(timeout=10)
        first.communicate()
        self.assertIn("late", out)
        return held

    def test_critical_pressure_alone_holds_new_jobs(self):
        self.assertTrue(self.held_until_released("4 100"))  # critical level, tiny swap

    def test_swap_over_the_line_alone_holds_new_jobs(self):
        self.assertTrue(self.held_until_released("1 9000"))  # calm level, swap over HEAVY_RUN_SWAP_MB

    def test_calm_machine_does_not_hold(self):
        self.assertFalse(self.held_until_released("1 1000"))

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
        self.assertEqual(self.heavy("./jest", "src/a")[2], 0)  # same arguments as the killed run
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
        script = os.path.join(self.tmp, "jest")
        # heavy-run pid isn't known to the child, so use the parent pid ($PPID) via a tiny wrapper
        open(script, "w").write(
            f"#!/bin/sh\nif [ ! -f {marker} ]; then touch {marker}; "
            f"{sys.executable} -c \"import sys;sys.path.insert(0,'{HOOKS}');import heavy_lib as h;"
            f"h.record_kill('{self.wt}','{script}',1,1,1,$PPID)\"; kill -9 $$; fi\nexit 0\n")
        os.chmod(script, 0o755)
        out, err, rc = self.heavy(script, budget="0", extra_env={"HEAVY_RUN_RETRY_COOLDOWN_S": "0.2"})
        self.assertEqual(rc, 0, err)
        self.assertIn("memory brake stopped", err)
        self.assertEqual(hl.open_entries(), [])  # killed -> re-queued -> green -> entry closed


class LedgerFixesTest(Base):
    kill = LedgerTest.kill

    def test_green_partial_run_does_not_close_a_killed_full_run(self):
        e = self.kill(command="npx jest", hr=4242)
        self.assertEqual(hl.mark_done(self.wt, "npx jest one.test.ts"), 0)
        self.assertEqual([x["id"] for x in hl.open_entries()], [e["id"]])
        self.assertEqual(hl.mark_done(self.wt, "npx jest"), 1)  # exact label closes it
        self.assertEqual(hl.open_entries(), [])

    def test_raw_kill_is_not_closed_by_a_different_argument_run(self):
        e = self.kill(command="npx jest")
        self.assertEqual(hl.mark_done(self.wt, "npx jest only/this.test.ts"), 0)
        self.assertEqual([x["id"] for x in hl.open_entries()], [e["id"]])

    def test_nested_repo_inside_the_worktree_does_not_own_the_entry(self):
        e = self.kill()
        nested = os.path.join(self.wt, "inner")
        os.makedirs(nested)
        subprocess.run(["git", "init", "-q", nested], check=True)
        pkg = os.path.join(self.wt, "pkg")
        os.makedirs(pkg)
        self.assertFalse(hl.owns(e, nested))
        self.assertTrue(hl.owns(e, pkg))

    def test_ledger_rotation_keeps_only_open_entries(self):
        a = self.kill(command="npx jest a")
        b = self.kill(command="npx jest b")
        hl.mark_done(self.wt, "npx jest a")
        hl.rotate_ledger(max_bytes=10)
        self.assertTrue(os.path.exists(str(hl.ledger_path()) + ".1"))
        self.assertEqual([x["id"] for x in hl.open_entries()], [b["id"]])
        self.assertEqual([x["id"] for x in hl.read_events() if x["event"] == "kill"], [b["id"]])


class BrakeRunTest(Base):
    """heavy-run behaviour around a brake kill (the child records the kill, then dies)."""

    def killer_job(self, marker_name="marker"):
        marker = os.path.join(self.tmp, marker_name)
        script = os.path.join(self.tmp, "jest")  # named jest so the label is retry-safe
        open(script, "w").write(
            f"#!/bin/sh\nif [ ! -f {marker} ]; then touch {marker}; "
            f"{sys.executable} -c \"import sys;sys.path.insert(0,'{HOOKS}');import heavy_lib as h;"
            f"h.record_kill('{self.wt}','{script}',1,1,1,$PPID)\"; kill -9 $$; fi\nexit 0\n")
        os.chmod(script, 0o755)
        return script

    def test_foreground_brake_kill_exits_without_retrying(self):
        script = self.killer_job()
        out, err, rc = self.heavy(script, budget="20", extra_env={"HEAVY_RUN_RETRY_COOLDOWN_S": "0.2"})
        self.assertNotEqual(rc, 0, err)
        self.assertIn("memory brake stopped", err)
        self.assertEqual(len(hl.open_entries()), 1)  # left for the ledger to nudge a re-run

    def test_background_retry_of_a_safe_label_and_sigterm_after_the_child_exits(self):
        script = self.killer_job("m2")
        p = self.heavy(script, budget="0", extra_env={"HEAVY_RUN_RETRY_COOLDOWN_S": "30"}, wait=False)
        for _ in range(100):  # wait for the kill to be ledgered; the retry cooldown then starts
            if hl.read_events():
                break
            time.sleep(0.1)
        time.sleep(0.8)
        p.send_signal(signal.SIGTERM)  # handlers must be restored once the child is gone
        p.communicate(timeout=5)
        self.assertEqual(p.returncode, -signal.SIGTERM)


class BrakeTest(Base):
    def setUp(self):
        super().setUp()
        self.mg = load(os.path.join(BIN, "memory-guard.py"), "memory_guard_under_test")
        self.mg.STATE_DIR = hl.state_dir()
        self.mg.LOG = self.env["MEMORY_GUARD_LOG"] and __import__("pathlib").Path(self.env["MEMORY_GUARD_LOG"])

    def table(self, rows):
        return {pid: (ppid, rss, cmd, age) for pid, ppid, rss, cmd, age in rows}

    def run_brake(self, rows, dry=False, free=900, critical=True, max_kills=1, gated=(100, 200, 300), recs=None):
        killed = []
        default = [{"pid": 9000 + p, "child": p, "cwd": self.wt, "cmd": next(r[3] for r in rows if r[0] == p), "slot": 0}
                for p in gated if any(r[0] == p for r in rows)]
        gr = mock.patch.object(hl, "gate_records", return_value=default if recs is None else recs)
        gr.start()
        self.addCleanup(gr.stop)
        self.mg.BRAKE_FREE_MB = free
        self.mg.BRAKE_MAX_KILLS_PER_CYCLE = max_kills
        with mock.patch.object(self.mg, "ps_table", return_value=self.table(rows)), \
                mock.patch.object(self.mg, "pid_cwd", return_value=self.wt), \
                mock.patch.object(self.mg.os, "kill", side_effect=lambda pid, sig: killed.append(pid)):
            n = self.mg.brake(dry, critical=critical)
        return n, killed

    # (pid, ppid, rss_mb, command, age_s): tsc is the oldest job, eslint the biggest of the others
    ROWS = [
        (100, 1, 40, "node /x/node_modules/.bin/jest src", 100),
        (101, 100, 150, "node /x/node_modules/jest-worker/processChild.js", 100),
        (102, 100, 120, "node /x/node_modules/jest-worker/processChild.js", 100),
        (200, 1, 700, "node /x/node_modules/typescript/bin/tsc --noEmit", 500),
        (300, 1, 600, "node /y/node_modules/.bin/eslint .", 50),
        (400, 1, 30, "/Applications/Claude.app/Contents/MacOS/Claude", 900),
        (500, 1, 20, "python3 /Users/e/bin/heavy-run npx jest waiting-job", 10),  # a job waiting in the gate
    ]

    def test_lone_job_is_not_killed_on_swap_alone(self):
        n, killed = self.run_brake([self.ROWS[3]], critical=False)
        self.assertEqual((n, killed), (0, []))

    def test_swap_only_with_two_jobs_kills_one_and_spares_the_oldest(self):
        n, killed = self.run_brake(self.ROWS, critical=False, free=99999)
        self.assertEqual(killed, [300])  # eslint: biggest non-oldest; tsc (oldest) and jest spared
        self.assertEqual(n, 1)

    def test_lone_job_is_killed_at_critical(self):
        n, killed = self.run_brake([self.ROWS[3]], critical=True)
        self.assertEqual((n, killed), (1, [200]))

    def test_one_kill_per_cycle_even_when_far_over(self):
        n, killed = self.run_brake(self.ROWS, free=99999)
        self.assertEqual(killed, [300])
        self.assertEqual(len(hl.open_entries()), 1)

    def test_job_is_killed_as_a_unit_and_ledgered_per_job(self):
        n, killed = self.run_brake(self.ROWS, free=99999, max_kills=5)
        self.assertEqual(sorted(killed), [100, 101, 102, 300])  # workers go with their jest parent; oldest (tsc) spared
        self.assertNotIn(500, killed)  # the waiting heavy-run is never killed
        self.assertNotIn(400, killed)  # nor Claude
        entries = hl.open_entries()
        self.assertEqual(len(entries), 2)  # one entry per job, not per process
        jest = [e for e in entries if e["pid"] == 100][0]
        self.assertEqual((jest["worktree"], jest["kind"], jest["job_rss_mb"]), (os.path.realpath(self.wt), "jest", 310))

    def test_stops_once_enough_is_freed(self):
        n, killed = self.run_brake(self.ROWS, free=500, max_kills=5)
        self.assertEqual(killed, [300])  # 600 MB >= 500, so jest is spared too

    def test_never_list_protects_every_alternative(self):
        # each command matches BRAKE_PATTERNS (it would be killed) and must be saved only by BRAKE_NEVER
        for cmd in ("node /x/xcodebuild/jest", "node /x/eas-cli/node_modules/.bin/jest", "node /x/eas build/jest",
                    "/Applications/Claude.app/Contents/Helper/jest", "/usr/local/bin/claude --jest",
                    "node /x/mcp-server/node_modules/.bin/jest", "python3 /bin/heavy-run npx jest"):
            self.assertTrue(self.mg.BRAKE_PATTERNS.search(cmd), cmd)
            n, killed = self.run_brake([(10, 1, 900, cmd, 100)])
            self.assertEqual((n, killed), (0, []), cmd)

    def test_dry_run_kills_and_records_nothing(self):
        n, killed = self.run_brake(self.ROWS, dry=True)
        self.assertEqual((killed, hl.open_entries()), ([], []))
        self.assertIn("would kill job", open(self.env["MEMORY_GUARD_LOG"]).read())

    TSSERVER = (600, 1, 300, "node /x/node_modules/typescript/lib/tsserver.js", 99999)

    def test_editor_server_does_not_make_a_lone_heavy_run_job_killable_on_swap(self):
        # one heavy-run test + the editor's tsserver (older): still ONE job, so swap alone kills nothing
        n, killed = self.run_brake([self.ROWS[0], self.TSSERVER], critical=False, gated=(100,))
        self.assertEqual((n, killed), (0, []))

    def test_oldest_spared_is_among_heavy_run_jobs_only(self):
        # tsserver is the oldest process but not a heavy-run job: it must not be the one spared
        n, killed = self.run_brake([self.ROWS[3], self.ROWS[4], self.TSSERVER], critical=False, free=99999,
                                   gated=(200, 300))
        self.assertEqual(killed, [300])  # eslint (not the oldest heavy-run job) dies; tsserver untouched on swap

    def test_long_running_server_stays_killable_at_critical(self):
        n, killed = self.run_brake([self.TSSERVER], critical=True, gated=())
        self.assertEqual((n, killed), (1, [600]))

    def test_heavy_run_job_keeps_its_command_in_the_ledger(self):
        rec = [{"pid": 4242, "child": 90, "cwd": self.wt, "cmd": "npm test", "slot": 0}]
        rows = [(90, 1, 10, "npm test", 5), (100, 90, 300, "node /x/node_modules/.bin/jest", 5)]
        self.run_brake(rows, recs=rec)
        e = hl.open_entries()[0]
        self.assertEqual((e["command"], e["heavy_run_pid"]), ("npm test", 4242))


if __name__ == "__main__":
    unittest.main()
