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
        self.assertEqual(out["permissionDecision"], "deny")
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

    def test_fail_open_says_so(self):
        d = self.model_change()
        r = subprocess.run([sys.executable, HOOK], capture_output=True, text=True, timeout=30,
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -am x"},
                                             "cwd": d}),
                           env={**self.env, "EVAL_GATE_REGISTRY": os.path.join(d, "missing.json")})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIn("check skipped", r.stderr)


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
