"""eval-gate.py: a prompt or model change in a product repo needs its eval run, and the PR its score.

Fixtures are throwaway git repos whose `origin` is named after a registered product repo, so the real
registry (cloud-kit/hooks/eval-gate.json) is what gets tested.
"""
import json, os, subprocess, sys, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.path.join(ROOT, "cloud-kit", "hooks", "eval-gate.py")
REGISTRY = os.path.join(ROOT, "cloud-kit", "hooks", "eval-gate.json")
SKILL = os.path.join(ROOT, "skills", "llm-provider-chain", "SKILL.md")

QUALIFY = "src/unleashed_leadgen/hunters/coach_hunter/prompts/qualify.md"
DRAFT = "src/unleashed_leadgen/hunters/coach_hunter/prompts/draft_d0.md"


def git(d, *args):
    subprocess.run(["git", "-C", d, *args], check=True, capture_output=True, text=True)


def write(d, path, text):
    full = os.path.join(d, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "state", "eval-gate.json")
        self.env = {**os.environ, "EVAL_GATE_STATE": self.state, "CLAUDE_CODE_REMOTE": "true"}
        self.env.pop("EVAL_GATE_OFF", None)

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self, name, files):
        d = os.path.join(self.tmp.name, name)
        os.makedirs(d)
        git(d, "init", "-q", "-b", "main")
        git(d, "config", "user.email", "t@example.com")
        git(d, "config", "user.name", "t")
        git(d, "remote", "add", "origin", f"https://github.com/UnleashedPPOS/{name}.git")
        for p, t in files.items():
            write(d, p, t)
        git(d, "add", "-A")
        git(d, "commit", "-qm", "init")
        git(d, "update-ref", "refs/remotes/origin/main", "HEAD")
        return d

    def hook(self, tool, inp, cwd, event="PreToolUse", resp=None, env=None):
        payload = {"hook_event_name": event, "tool_name": tool, "tool_input": inp, "cwd": cwd}
        if resp is not None:
            payload["tool_response"] = resp
        r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
                           text=True, env=env or self.env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return None
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.kind = out.get("permissionDecision", "warn")  # a commit only warns; a PR is denied
        if self.kind == "warn":
            return out["additionalContext"]
        self.assertEqual(self.kind, "deny")
        return out["permissionDecisionReason"]

    def bash(self, cmd, cwd, **kw):
        return self.hook("Bash", {"command": cmd}, cwd, **kw)

    def ran(self, cmd, cwd, stdout="qualify: 47/50 (94%) PASS"):
        self.bash(cmd, cwd, event="PostToolUse", resp={"stdout": stdout, "stderr": ""})

    def leadgen(self):
        return self.repo("unleashed-leadgen", {
            QUALIFY: "Qualify this lead.\nScore 0-10.\n",
            DRAFT: "Write a first email.\n",
            "src/unleashed_leadgen/util.py": "def add(a, b):\n    return a + b\n",
            "README.md": "# leadgen\n",
        })

    def systems(self):
        return self.repo("unleashed-systems", {
            "src/lib/llm/client.ts": "export const MODEL = 'openai.gpt-oss-120b-1:0';\n",
            "src/lib/inbox/classify.ts": "const P = `You are a triage assistant.\nSort the mail.\nBe brief.`;\n",
            "src/app/page.tsx": "export default () => 'Welcome';\n",
            "tests/llm.test.ts": "it('x', () => {});\n",
        })


class Commit(Fixture):
    def test_fires_on_prompt_file_change(self):
        d = self.leadgen()
        write(d, QUALIFY, "Qualify this lead.\nScore 0-100.\n")
        git(d, "add", QUALIFY)
        r = self.bash("git commit -m 'feat: sharper qualify prompt'", d)
        self.assertIsNotNone(r)
        self.assertIn("qualify", r)
        self.assertIn("evals.m3 qualify", r)
        self.assertNotIn("--live", r, "the cloud gets the offline command only")

    def test_fires_on_model_id_change_outside_eval_area(self):
        d = self.systems()
        write(d, "src/lib/llm/client.ts", "export const MODEL = 'openai.gpt-oss-20b-1:0';\n")
        r = self.bash(f"cd {d} && git commit -am 'perf: cheaper model'", self.tmp.name)
        self.assertIsNotNone(r)
        self.assertIn("inbox-triage", r, "the repo default eval covers a model change anywhere")
        self.assertIn("npm run eval:triage", r)

    def test_fires_on_mid_prompt_edit_in_eval_area(self):
        d = self.systems()
        write(d, "src/lib/inbox/classify.ts", "const P = `You are a triage assistant.\nSort the mail.\nBe kind.`;\n")
        r = self.bash("git add -A && git commit -m 'fix: tone'", d)
        self.assertIsNotNone(r)
        self.assertIn("LLM file", r)

    def test_fires_on_untracked_prompt_added_in_same_command(self):
        d = self.leadgen()
        write(d, "src/unleashed_leadgen/hunters/gym_hunter/prompts/qualify.md", "Qualify gyms.\n")
        self.assertIsNotNone(self.bash("git add -A && git commit -m 'feat: gym hunter'", d))

    def test_silent_on_unrelated_change(self):
        d = self.systems()
        write(d, "src/app/page.tsx", "export default () => 'Hello';\n")
        write(d, "tests/llm.test.ts", "it('uses claude-haiku-5-5', () => {});\n")
        write(d, "README.md", "Model: claude-haiku-5-5. You are a reader.\n")
        self.assertIsNone(self.bash("git add -A && git commit -m 'feat: copy'", d))

    def test_silent_on_unstaged_prompt_when_committing_other_staged_file(self):
        d = self.leadgen()
        write(d, QUALIFY, "changed\n")
        write(d, "src/unleashed_leadgen/util.py", "def add(a, b):\n    return b + a\n")
        git(d, "add", "src/unleashed_leadgen/util.py")
        self.assertIsNone(self.bash("git commit -m 'refactor: add'", d))

    def test_silent_in_unknown_repo(self):
        d = self.repo("unleashed-superpowers", {"prompts/x.md": "a\n"})
        write(d, "prompts/x.md", "You are a new prompt.\n")
        self.assertIsNone(self.bash("git commit -am 'docs: prompt'", d))

    def test_allows_after_eval_ran_and_fires_again_after_a_new_edit(self):
        d = self.leadgen()
        write(d, QUALIFY, "Qualify this lead.\nScore 0-100.\n")
        git(d, "add", QUALIFY)
        self.ran("PYTHONPATH=. uv run python -m evals.m3 qualify", d)
        with open(self.state) as f:
            st = json.load(f)
        self.assertIn("47/50", st["unleashed-leadgen"]["qualify"]["tail"])
        self.assertIsNone(self.bash("git commit -m 'feat: qualify'", d))
        future = time.time() + 60
        os.utime(os.path.join(d, QUALIFY), (future, future))
        self.assertIsNotNone(self.bash("git commit -m 'feat: qualify'", d), "edited after the eval: run it again")

    def test_eval_in_same_command_counts(self):
        d = self.leadgen()
        write(d, QUALIFY, "x\n")
        git(d, "add", QUALIFY)
        self.assertIsNone(self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify && git commit -m 'feat: q'", d))

    def test_local_with_vault_names_the_live_eval(self):
        d = self.leadgen()
        write(d, QUALIFY, "x\n")
        git(d, "add", QUALIFY)
        bindir = os.path.join(self.tmp.name, "bin")
        os.makedirs(bindir)
        write(bindir, "vault", "#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(bindir, "vault"), 0o755)
        env = {**self.env, "PATH": bindir + os.pathsep + os.environ["PATH"]}
        env.pop("CLAUDE_CODE_REMOTE")
        r = self.bash("git commit -m 'feat: q'", d, env=env)
        self.assertIn("vault run", r)
        self.assertIn("--live", r)

    def test_uncovered_prompt_change_commits(self):
        d = self.leadgen()
        write(d, DRAFT, "Write a warmer first email.\n")
        self.assertIsNone(self.bash("git commit -am 'feat: warmer draft'", d), "no eval to run at commit time")


class PullRequest(Fixture):
    def branch(self, d, path, text):
        git(d, "checkout", "-qb", "feat/x")
        write(d, path, text)
        git(d, "commit", "-qam", "feat: x")

    def test_denies_without_run_and_score_then_allows(self):
        d = self.leadgen()
        self.branch(d, QUALIFY, "Score 0-100.\n")
        r = self.bash("gh pr create --draft --title t --body 'Sharper prompt.'", d)
        self.assertIn("run qualify", r)
        self.assertIn("score line for qualify", r)
        self.ran("cd . && PYTHONPATH=. uv run python -m evals.m3 qualify", d)
        r = self.bash("gh pr create --title t --body 'Eval: 47/50'", d)
        self.assertIn("score line for qualify", r, "the score line must name the eval")
        body = "## Summary\nSharper.\n\nEval (qualify, offline): 47/50 (94%)\n"
        self.assertIsNone(self.bash(f"gh pr create --title t --body \"{body}\"", d))

    def test_body_file_and_heredoc(self):
        d = self.leadgen()
        self.branch(d, QUALIFY, "Score 0-100.\n")
        self.ran("PYTHONPATH=. uv run python -m evals.m3 qualify", d)
        write(d, "body.md", "Eval (qualify, offline): 94%\n")
        self.assertIsNone(self.bash("gh pr create --title t --body-file body.md", d))
        heredoc = "gh pr create --title t --body \"$(cat <<'EOF'\nEval (qualify, offline): 47/50\nEOF\n)\""
        self.assertIsNone(self.bash(heredoc, d))
        self.assertIsNotNone(self.bash("gh pr create --fill", d))

    def test_uncovered_change_needs_eval_none_line(self):
        d = self.leadgen()
        self.branch(d, DRAFT, "Warmer.\n")
        r = self.bash("gh pr create --title t --body 'Warmer draft.'", d)
        self.assertIn("Eval: none", r)
        self.assertIsNone(self.bash(
            "gh pr create --title t --body 'Eval: none: no eval covers the draft prompts yet'", d))

    def test_silent_for_unrelated_branch(self):
        d = self.leadgen()
        self.branch(d, "src/unleashed_leadgen/util.py", "def add(a, b):\n    return b + a\n")
        self.assertIsNone(self.bash("gh pr create --title t --body 'refactor'", d))

    def test_mcp_create_pull_request(self):
        d = self.leadgen()
        self.branch(d, QUALIFY, "Score 0-100.\n")
        inp = {"owner": "UnleashedPPOS", "repo": "unleashed-leadgen", "head": "feat/x", "base": "main",
               "title": "t", "body": "Sharper."}
        tool = "mcp__github__create_pull_request"
        self.assertIsNotNone(self.hook(tool, inp, d))
        self.ran("PYTHONPATH=. uv run python -m evals.m3 qualify", d)
        inp["body"] = "Eval (qualify, offline): 47/50"
        self.assertIsNone(self.hook(tool, inp, d))
        self.assertIsNone(self.hook(tool, {**inp, "repo": "some-other-repo", "body": ""}, d))

    def test_score_line_must_be_in_the_eval_format(self):
        d = self.leadgen()
        self.branch(d, QUALIFY, "Score 0-100.\n")
        self.ran("PYTHONPATH=. uv run python -m evals.m3 qualify", d)
        r = self.bash("gh pr create --title t --body 'Eval of qualify prompt changed on 11/18'", d)
        self.assertIn("score line for qualify", r, "a date next to the name is not a score")
        for body in ("Eval (qualify): ran on 11/18", "Eval (qualify, offline): 11/18/26"):
            self.assertIsNotNone(self.bash(f"gh pr create --title t --body '{body}'", d), body)


class MentionsAndStatus(Fixture):
    def staged(self):
        d = self.leadgen()
        write(d, QUALIFY, "Qualify this lead.\nScore 0-100.\n")
        git(d, "add", QUALIFY)
        return d

    def test_mentions_of_git_commit_are_not_commits(self):
        d = self.staged()
        for cmd in ('echo "remember to git commit later"', 'git log --grep "git commit"',
                    "git commit-tree HEAD^{tree} -m x", "grep -r 'gh pr create' docs",
                    'echo "gh pr create later"'):
            self.assertIsNone(self.bash(cmd, d), cmd)
        self.assertIsNotNone(self.bash("git commit -m x", d))
        self.assertIsNotNone(self.bash("echo hi; git commit -m x", d))

    def test_commit_only_warns_pr_denies(self):
        d = self.staged()
        self.assertIsNotNone(self.bash("git commit -m x", d))
        self.assertEqual(self.kind, "warn")
        git(d, "commit", "-qm", "x")
        git(d, "checkout", "-qb", "feat/y", "HEAD")
        self.assertIsNotNone(self.bash("gh pr create --title t --body 'x'", d))
        self.assertEqual(self.kind, "deny")

    def test_failed_eval_is_recorded_and_does_not_count(self):
        d = self.staged()
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify", d, event="PostToolUse",
                  resp={"stdout": "boom", "stderr": "", "exit_code": 1})
        st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
        self.assertEqual((st["exit"], st["ok"], st["score"]), (1, False, None))
        self.assertIsNotNone(self.bash("git commit -m x", d))
        self.assertEqual(self.kind, "warn")

    def test_masked_exit_is_not_trusted_without_a_score(self):
        d = self.staged()
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify; true", d, event="PostToolUse",
                  resp={"stdout": "boom", "stderr": "", "exit_code": 0})
        st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
        self.assertFalse(st["ok"])
        self.assertIsNone(st["exit"])

    def test_masked_exit_score_from_a_later_echo_is_not_trusted(self):
        d = self.staged()
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify; echo 47/50", d, event="PostToolUse",
                  resp={"stdout": "missing script\n47/50", "stderr": "", "exit_code": 0})
        st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
        self.assertFalse(st["ok"])

    def test_masked_exit_score_through_tee_is_trusted(self):
        d = self.staged()
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify | tee out.txt", d, event="PostToolUse",
                  resp={"stdout": "qualify: 47/50 PASS", "stderr": "", "exit_code": 0})
        st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
        self.assertTrue(st["ok"])

    def test_masked_exit_score_read_from_a_file_is_not_trusted(self):
        d = self.staged()
        for cmd in ("PYTHONPATH=. uv run python -m evals.m3 qualify; grep -h . /tmp/fake.txt",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; tail -1 /tmp/fake.txt",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | head -c 100 /tmp/fake.txt",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep -f /tmp/pats",
                    # GNU grep -r with no file searches the current directory.
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep -r 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep -R 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep --recursive 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep --dereference-recursive 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep -ir 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep -rf pats",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep --file=pats",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep -d recurse 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep --directories=recurse 47/50",
                    # Unambiguous long-flag prefixes are accepted by GNU grep.
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep --rec 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep --dir=recurse 47/50",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep --fil=pats",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify; true | grep --dereference 47/50"):
            self.bash(cmd, d, event="PostToolUse", resp={"stdout": "47/50", "stderr": "", "exit_code": 0})
            st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
            self.assertFalse(st["ok"], cmd)

    def test_masked_exit_score_through_tail_and_grep_is_trusted(self):
        d = self.staged()
        for cmd in ("PYTHONPATH=. uv run python -m evals.m3 qualify 2>&1 | tail -5",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep -i score",
                    "PYTHONPATH=. uv run python -m evals.m3 qualify | grep -E --fixed-strings score"):
            self.bash(cmd, d, event="PostToolUse", resp={"stdout": "score 47/50", "stderr": "", "exit_code": 0})
            st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
            self.assertTrue(st["ok"], cmd)

    def test_passing_run_records_score(self):
        d = self.staged()
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify", d, event="PostToolUse",
                  resp={"stdout": "qualify: 47/50 PASS", "stderr": "", "exit_code": 0})
        st = json.load(open(self.state))["unleashed-leadgen"]["qualify"]
        self.assertEqual((st["exit"], st["ok"], st["score"]), (0, True, "47/50"))
        self.assertIsNone(self.bash("git commit -m x", d))

    # Harnesses that report no exit status (this app, the cloud): the runner's closing line is the proof.
    DENO = "deno test -A supabase/functions/voice/evals/"
    PYTEST = "python -m pytest tests/test_receptionist_eval.py livekit_agent/tests/test_prompt.py"

    def uos(self):
        return self.repo("unleashedos", {"supabase/functions/voice/evals/golden.json": "[]\n"})

    def voice(self):
        return self.repo("unleashed-voice", {"livekit_agent/prompt.py": "P = 'hi'\n"})

    def rec(self, repo, name):
        return json.load(open(self.state))[repo][name]

    def test_deno_pass_with_no_exit_status_counts(self):
        d = self.uos()
        out = "running 42 tests from ./evals_test.ts\n\x1b[32mok\x1b[0m | 42 passed | 0 failed (163ms)\n"
        for cmd in (self.DENO, self.DENO + " 2>&1 | tail -5", f"cd {d} && {self.DENO}"):
            self.bash(cmd, d, event="PostToolUse", resp={"stdout": out, "stderr": ""})
            st = self.rec("unleashedos", "voice")
            self.assertEqual((st["exit"], st["ok"], st["score"]), (None, True, "42/42"), cmd)

    def test_deno_failed_or_empty_run_with_no_exit_status_does_not_count(self):
        d = self.uos()
        for out in ("FAILED | 40 passed | 2 failed (1s)\n",
                    "ok | 40 passed | 0 failed (1s)\nFAILED | 1 passed | 1 failed (1s)\n",
                    "ok | 0 passed | 0 failed (3ms)\n",
                    "error: Module not found\n"):
            self.bash(self.DENO, d, event="PostToolUse", resp={"stdout": out, "stderr": ""})
            self.assertFalse(self.rec("unleashedos", "voice")["ok"], out)

    def test_pytest_summary_with_no_exit_status(self):
        d = self.voice()
        for out, ok in (("============ 13 passed, 2 warnings in 1.20s ============\n", True),
                        ("13 passed in 62.10s (0:01:02)\n", True),
                        ("1 skipped, 12 passed in 0.9s\n", True),
                        ("======= 3 failed, 10 passed in 2.10s =======\n", False),
                        ("10 passed, 1 error in 2.10s\n", False),
                        ("===== 2 errors in 0.40s =====\n", False),
                        ("no tests ran in 0.01s\n", False)):
            self.bash(self.PYTEST, d, event="PostToolUse", resp={"stdout": out, "stderr": ""})
            self.assertEqual(self.rec("unleashed-voice", "prompts")["ok"], ok, out)
        self.assertIsNone(self.rec("unleashed-voice", "prompts")["score"])

    def test_vitest_and_jest_summaries_with_no_exit_status(self):
        d = self.systems()
        cmd = "npx vitest run tests/evals"
        for out, ok in ((" Test Files  3 passed (3)\n      Tests  42 passed (42)\n   Duration  1.2s\n", True),
                        (" Test Files  1 failed | 2 passed (3)\n      Tests  42 passed (42)\n", False),
                        (" Test Files  3 passed (3)\n      Tests  2 failed | 40 passed (42)\n", False),
                        (" Test Files  3 passed (3)\n      Tests  42 passed (42)\n     Errors  1 error\n", False),
                        ("Test Suites: 3 passed, 3 total\nTests:       42 passed, 42 total\n", True),
                        ("Test Suites: 1 failed, 2 passed, 3 total\nTests:       42 passed, 42 total\n", False)):
            self.bash(cmd, d, event="PostToolUse", resp={"stdout": out, "stderr": ""})
            self.assertEqual(self.rec("unleashed-systems", "inbox-triage")["ok"], ok, out)

    def test_pass_summary_from_a_later_command_is_not_trusted(self):
        d = self.uos()
        for cmd in (self.DENO + '; echo "ok | 42 passed | 0 failed"',
                    self.DENO + "; tail -1 /tmp/fake.txt",
                    self.DENO + " && git commit -m x"):
            self.bash(cmd, d, event="PostToolUse", resp={"stdout": "ok | 42 passed | 0 failed (1s)\n", "stderr": ""})
            self.assertFalse(self.rec("unleashedos", "voice")["ok"], cmd)

    def test_failing_summary_beats_a_score_when_status_is_masked(self):
        d = self.uos()
        self.bash(self.DENO + "; true", d, event="PostToolUse",
                  resp={"stdout": "coverage 94%\nFAILED | 40 passed | 2 failed (1s)\n", "stderr": "", "exit_code": 0})
        self.assertFalse(self.rec("unleashedos", "voice")["ok"])

    def test_reported_exit_status_still_wins_over_a_pass_summary(self):
        d = self.uos()
        self.bash(self.DENO, d, event="PostToolUse",
                  resp={"stdout": "ok | 42 passed | 0 failed (1s)\n", "stderr": "", "exit_code": 1})
        st = self.rec("unleashedos", "voice")
        self.assertEqual((st["exit"], st["ok"]), (1, False))

    def test_pr_opens_on_a_deno_pass_with_no_exit_status(self):
        d = self.uos()
        git(d, "checkout", "-qb", "feat/x")
        write(d, "supabase/functions/voice/evals/golden.json", '[{"q": 1}]\n')
        git(d, "commit", "-qam", "feat: x")
        body = "gh pr create --title t --body 'Eval (voice, offline): 42/42 (100%)'"
        self.assertIsNotNone(self.bash(body, d))
        self.assertEqual(self.kind, "deny")
        self.bash(self.DENO, d, event="PostToolUse",
                  resp={"stdout": "ok | 42 passed | 0 failed (163ms)\n", "stderr": ""})
        self.assertIsNone(self.bash(body, d))

    def test_pr_blocked_by_failed_eval_but_skipped_line_passes(self):
        d = self.leadgen()
        git(d, "checkout", "-qb", "feat/x")
        write(d, QUALIFY, "Score 0-100.\n")
        git(d, "commit", "-qam", "feat: x")
        self.bash("PYTHONPATH=. uv run python -m evals.m3 qualify", d, event="PostToolUse",
                  resp={"stdout": "x", "stderr": "", "exit_code": 2})
        self.assertIsNotNone(self.bash("gh pr create --title t --body 'Eval (qualify, offline): 47/50'", d))
        self.assertEqual(self.kind, "deny")
        self.assertIsNone(self.bash(
            "gh pr create --title t --body 'Eval: skipped: eval harness down, ran by hand'", d))


class Loopholes(Fixture):
    """Review findings (Opus review of PR #36): each was a way past the gate or a false block."""

    def model_change(self):
        d = self.systems()
        write(d, "src/lib/llm/client.ts", "export const MODEL = 'openai.gpt-oss-20b-1:0';\n")
        return d

    def test_mentioning_the_eval_is_not_running_it(self):
        d = self.model_change()
        self.assertIsNotNone(self.bash("git commit -am 'perf: cheaper model, ran eval:triage'", d))
        self.ran("grep eval:triage package.json", d)
        self.assertFalse(os.path.exists(self.state), "a grep is not an eval run")
        self.assertIsNotNone(self.bash("git commit -am 'perf: cheaper model'", d))
        self.ran("timeout 900 npm run eval:triage 2>&1 | tail -5", d)
        self.assertIsNone(self.bash("git commit -am 'perf: cheaper model'", d))

    def test_eval_after_the_commit_does_not_count(self):
        d = self.model_change()
        self.assertIsNotNone(self.bash("git commit -am 'perf: x'; npm run eval:triage", d))
        self.assertIsNotNone(self.bash("npm run eval:triage || git commit -am 'perf: x'", d))

    def test_removed_sql_style_comment_does_not_hide_the_change(self):
        d = self.repo("unleashed-systems", {"src/lib/llm/models.lua": "-- old note\nLLM_MODEL = 'a'\n"})
        write(d, "src/lib/llm/models.lua", "LLM_MODEL = 'openai.gpt-oss-20b-1:0'\n")
        self.assertIsNotNone(self.bash("git commit -am 'perf: model'", d))

    def test_git_options_and_subshells_are_still_commits(self):
        d = self.model_change()
        for cmd in ("git -c core.quotepath=off commit -am x", "git --no-pager commit -am x",
                    f"git -C {d} commit -am x"):
            self.assertIsNotNone(self.bash(cmd, d), cmd)
        self.assertIsNotNone(self.bash(f"(cd {d} && git commit -am x)", self.tmp.name))

    def test_mid_prompt_edit_outside_every_eval_area(self):
        prompt = "export const SYSTEM_PROMPT = `\nAnswer as the coach.\nKeep it short.\n`;\n"
        d = self.repo("unleashed-systems", {"src/lib/brain/compose.ts": prompt})
        write(d, "src/lib/brain/compose.ts", prompt.replace("short", "warm"))
        r = self.bash("git commit -am 'fix: tone'", d)
        self.assertIsNotNone(r)
        self.assertIn("LLM file", r)

    def test_ordinary_code_that_looks_like_llm_code_is_silent(self):
        d = self.systems()
        write(d, "src/lib/db/schema.ts",
              "export const DATA_MODEL_VERSION = 3;\nUser.init({}, { modelName: \"User\" });\n")
        write(d, "src/app/crew.tsx", "export default () => <Text>You are the owner of this crew.</Text>;\n")
        self.assertIsNone(self.bash("git add -A && git commit -m 'feat: crew'", d))

    def test_git_add_of_one_file_does_not_scan_other_untracked_files(self):
        d = self.leadgen()
        write(d, "src/unleashed_leadgen/util.py", "def add(a, b):\n    return b + a\n")
        write(d, "src/unleashed_leadgen/hunters/gym_hunter/prompts/qualify.md", "Qualify gyms.\n")
        self.assertIsNone(self.bash("git add src/unleashed_leadgen/util.py && git commit -m 'refactor: add'", d))

    def test_quoted_add_paths_with_spaces_or_quotes(self):
        prompt = "export const SYSTEM_PROMPT = `\nAnswer as the coach.\nKeep it short.\n`;\n"
        d = self.repo("unleashed-systems", {"src/space dir/agent.ts": prompt, "src/it's.ts": prompt})
        for path in ("src/space dir/agent.ts", "src/it's.ts"):
            write(d, path, prompt.replace("short", "warm"))
            quoted = '"' + path + '"'
            self.assertIsNotNone(self.bash(f"git add {quoted} && git commit -m 'fix: tone'", d), path)

    def test_wrapped_eval_runs_are_recorded(self):
        d = self.model_change()
        for cmd in ("sh -c 'echo eval:triage'", "sudo grep eval:triage f", "time echo eval:triage",
                    "sh script.sh eval:triage", "vault run --keys K -- echo eval:triage"):
            self.ran(cmd, d)
            self.assertFalse(os.path.exists(self.state), cmd)
        self.assertIsNotNone(self.bash("bash -c 'echo eval:triage' && git commit -am x", d))
        self.assertIsNone(self.bash("bash -c 'npm run eval:triage && git commit -am x'", d))
        self.ran("bash -c 'npm run eval:triage'", d)
        self.assertIsNone(self.bash("git commit -am 'perf: x'", d))

    def test_wrapper_flag_values_are_skipped(self):
        d = self.model_change()
        for cmd in ("sudo -u me npm run eval:triage", "nice -n 5 npm run eval:triage",
                    "timeout -s KILL 900 npm run eval:triage"):
            self.assertIsNone(self.bash(cmd + " && git commit -am x", d), cmd)
        self.assertIsNotNone(self.bash("sudo -u me grep eval:triage f && git commit -am x", d))

    def test_fail_open_says_so(self):
        d = self.model_change()
        r = subprocess.run([sys.executable, HOOK], capture_output=True, text=True, timeout=30,
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -am x"},
                                             "cwd": d}),
                           env={**self.env, "EVAL_GATE_REGISTRY": os.path.join(d, "missing.json")})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("check skipped", r.stderr)

    def test_symlinked_hook_finds_its_registry(self):
        # ~/.claude/hooks/eval-gate.py is a symlink with no eval-gate.json beside it.
        d = self.model_change()
        link = os.path.join(self.tmp.name, "hooks", "eval-gate.py")
        os.makedirs(os.path.dirname(link))
        os.symlink(HOOK, link)
        r = subprocess.run([sys.executable, link], capture_output=True, text=True, timeout=30,
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -am x"},
                                             "cwd": d}), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("check skipped", r.stderr)
        self.assertTrue(r.stdout.strip(), "symlinked hook did not gate the commit")


class PassSummaryAttacks(Fixture):
    """Opus red-team of PR #45 (pass from the runner's closing line when no exit status is reported)."""
    DENO = "deno test -A supabase/functions/voice/evals/"
    PYTEST = "python -m pytest tests/test_receptionist_eval.py"
    VITEST = "npx vitest run tests/evals"
    OK = "ok | 42 passed | 0 failed (1s)\n"
    QUAL = "PYTHONPATH=. uv run python -m evals.m3 qualify"

    def voice(self):
        return self.repo("unleashed-voice", {"livekit_agent/prompt.py": "P = 'hi'\n"})

    def ok_after(self, repo, name, cmd, d, stdout, stderr="", code=None):
        if os.path.exists(self.state):
            os.remove(self.state)
        resp = {"stdout": stdout, "stderr": stderr}
        if code is not None:
            resp["exit_code"] = code
        self.bash(cmd, d, event="PostToolUse", resp=resp)
        if not os.path.exists(self.state):
            return None
        with open(self.state) as f:
            return json.load(f).get(repo, {}).get(name, {}).get("ok")

    def test_fake_closing_line_from_another_command(self):
        d = self.repo("unleashedos", {"a": "1"})
        fake = "'ok | 42 passed | 0 failed (1s)'"
        for cmd in (f"echo {fake}; {self.DENO}", f"printf {fake} >&2; {self.DENO}",
                    f"cat /tmp/fake.txt && {self.DENO}",
                    f"deno test -A supabase/functions/owner/x_test.ts; {self.DENO}",
                    f"{self.DENO}; echo {fake}", f"{self.DENO} && echo {fake}", f"{self.DENO} || echo {fake}",
                    f"{self.DENO}; printf {fake}", f"{self.DENO}; cat /tmp/fake.txt", f"{self.DENO}; (echo {fake})",
                    f"{self.DENO}; true `echo {fake} >&2`", f'{self.DENO}; : "$(printf {fake} >&2)"',
                    f'{self.DENO}; true "${{X:?{fake}}}"', f"{self.DENO} | tee >(sed s/FAILED/ok/ >&2) >/dev/null",
                    f"{self.DENO} <<EOF\nok | 42 passed | 0 failed (1s)\nEOF",
                    f"{self.DENO}; python -c \"print({fake})\"", f"{self.DENO} | sed s/FAILED/ok/",
                    f"{self.DENO} | awk '{{print}}'", f"{self.DENO} | cat /tmp/fake.txt"):
            self.assertFalse(self.ok_after("unleashedos", "voice", cmd, d, "error: boom\n", self.OK), cmd)

    def test_inline_code_naming_the_eval_is_not_a_run(self):
        d = self.leadgen()
        for cmd in ("uv run python -c \"print('47/50')\" evals.m3 qualify",
                    "node -e \"console.log('47/50')\" evals.m3 qualify", "bun --eval=x evals.m3 qualify"):
            self.assertIsNone(self.ok_after("unleashed-leadgen", "qualify", cmd, d, "47/50\n", code=0), cmd)
        self.assertTrue(self.ok_after("unleashed-leadgen", "qualify", "python -W ignore -m evals.m3 qualify", d,
                                      "47/50\n", code=0))

    def test_runner_says_passed_but_the_run_failed(self):
        uos, voice, sysd = self.repo("unleashedos", {"a": "1"}), self.voice(), self.systems()
        cov = "TOTAL 10 5 50%\n\nFAIL Required test coverage of 90% not reached. Total coverage: 50.00%\n"
        for repo, name, d, cmd, out in (
                ("unleashedos", "voice", uos, self.DENO, self.OK + "error: Uncaught (in promise) Error: x\n"),
                ("unleashedos", "voice", uos, self.DENO, "ok | 3 passed\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST, cov + "===== 13 passed in 1.2s =====\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST, "INTERNALERROR> boom\nt.py ....  [100%]\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST + " -n 4", "created: 4/4 workers\nINTERNALERROR> x\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST,
                 "!!!!! Interrupted: 1 error during collection !!!!!\n=== 13 passed in 1.2s ===\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST,
                 " Test Files  3 passed (3)\n      Tests  42 passed (42)\n"
                 "ERROR: Coverage for lines (50%) does not meet global threshold (80%)\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST,
                 "Unhandled Errors\n Test Files  3 passed (3)\n      Tests  42 passed (42)\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST,
                 " Test Files  3 passed (3)\n      Tests  42 passed (42)\n Type Errors  1 error\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST,
                 "\x1b[2m Test Files \x1b(B 1 failed | 2 passed (3)\n      Tests  42 passed (42)\n"),
                ("unleashed-systems", "inbox-triage", sysd, "npx vitest run tests/evals/jest",
                 "Test Suites: 3 passed, 3 total\nTests:       42 passed, 42 total\n"
                 'Jest: "global" coverage threshold for lines (90%) not met: 50%\n')):
            self.assertFalse(self.ok_after(repo, name, cmd, d, out), out)

    def test_filters_that_can_drop_the_failed_line(self):
        voice, sysd = self.voice(), self.systems()
        for repo, name, d, cmd, out in (
                ("unleashed-voice", "prompts", voice, self.PYTEST + " | tail -1", "=== 13 passed in 1.2s ===\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST + " | grep passed", "13 passed in 1.2s\n"),
                ("unleashed-voice", "prompts", voice, self.PYTEST + " | head -50", "13 passed in 1.2s\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST + " 2>&1 | tail -3",
                 "      Tests  40 passed (40)\n   Start at  12:00:00\n   Duration  1.2s\n"),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST + " 2>&1 | grep passed",
                 " Test Files  3 passed (3)\n      Tests  42 passed (42)\n")):
            self.assertFalse(self.ok_after(repo, name, cmd, d, out), cmd)

    def test_600_character_tail_cutting_a_failed_line(self):
        voice = self.voice()
        out = "x" * 700 + "\n3 failed, 10 passed in 2.10s\n"
        stderr = "w" * (600 - len("10 passed in 2.10s\n"))
        self.assertFalse(self.ok_after("unleashed-voice", "prompts", self.PYTEST, voice, out, stderr))

    def test_honest_runs_still_pass(self):
        uos, voice, sysd, lead = self.repo("unleashedos", {"a": "1"}), self.voice(), self.systems(), self.leadgen()
        green = "\x1b[32mok\x1b[0m | 42 passed | 0 failed (163ms)\r\n"
        vit = " Test Files  3 passed (3)\n      Tests  42 passed (42)\n   Start at  12:00:00\n   Duration  1.2s\n"
        for repo, name, d, cmd, out, code in (
                ("unleashedos", "voice", uos, self.DENO, green, None),
                ("unleashedos", "voice", uos, self.DENO + " --quiet --reporter=dot 2>&1 | tail -1", self.OK, None),
                ("unleashedos", "voice", uos, f"cd {uos} && export NO_COLOR=1; {self.DENO}; true", self.OK, 0),
                ("unleashed-voice", "prompts", voice, self.PYTEST + " -q -x", "13 passed in 1.20s\n", None),
                ("unleashed-voice", "prompts", voice, self.PYTEST + " -n 4 2>&1 | tail -20",
                 "created: 4/4 workers\n.............  [100%]\n13 passed in 2.1s\n", None),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST + " --reporter=dot | tee out.txt", vit, None),
                ("unleashed-systems", "inbox-triage", sysd, self.VITEST + " 2>&1 | tail -n 10", vit, None),
                ("unleashed-leadgen", "qualify", lead, self.QUAL, "qualify: 47/50 (94%) PASS\n", None),
                ("unleashed-leadgen", "qualify", lead, self.QUAL + " | grep -i score", "score 47/50\n", 0),
                ("unleashed-leadgen", "qualify", lead, self.QUAL + " | tee out; true", "qualify: 47/50\n", 0)):
            self.assertTrue(self.ok_after(repo, name, cmd, d, out, code=code), cmd)
        write(lead, QUALIFY, "Qualify this lead.\nScore 0-100.\n")
        git(lead, "add", QUALIFY)
        self.assertIsNone(self.bash(self.QUAL + " && git commit -m x", lead))


class Safety(Fixture):
    def run_raw(self, stdin, env=None):
        return subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True,
                              env=env or self.env, timeout=30)

    def test_garbage_fails_open(self):
        for junk in ("", "not json", "[]", json.dumps({"tool_name": "Bash", "tool_input": "x"})):
            r = self.run_raw(junk)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, ""), junk)

    def test_off_switch(self):
        d = self.leadgen()
        write(d, QUALIFY, "x\n")
        git(d, "add", QUALIFY)
        self.assertIsNone(self.bash("git commit -m q", d, env={**self.env, "EVAL_GATE_OFF": "1"}))

    def test_not_a_git_dir(self):
        self.assertIsNone(self.bash("git commit -m q", self.tmp.name))


class RegistryInSkill(unittest.TestCase):
    def test_every_eval_is_in_the_skill_table(self):
        with open(REGISTRY) as f:
            repos = json.load(f)["repos"]
        with open(SKILL) as f:
            skill = f.read()
        section = skill[skill.index("## Catalogue: eval per repo"):]
        section = section[:section.index("\n## ", 5)]
        for repo, cfg in repos.items():
            self.assertIn(f"`{repo}`", section, repo)
            names = {e["name"] for e in cfg["evals"]}
            self.assertIn(cfg.get("default"), names | {None}, repo)
            for e in cfg["evals"]:
                self.assertIn(e["name"], section, f"{repo}/{e['name']}")
                self.assertIn(e["offline"].replace("|", "\\|"), section, f"{repo}/{e['name']} offline command")
                self.assertNotIn("openrouter", json.dumps(e).lower().replace("calls openrouter", ""),
                                 "evals never run on OpenRouter")


if __name__ == "__main__":
    unittest.main()
