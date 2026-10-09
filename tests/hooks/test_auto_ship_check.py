"""Tests for cloud-kit/hooks/auto-ship-check.py (the Stop hook that asks for /ship-check).

Run: python3 -m unittest discover -s tests/hooks -v
Builds throwaway git repos and transcripts, then runs the hook's main() on them.
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest import mock

HOOK = os.path.join(os.path.dirname(__file__), "..", "..", "cloud-kit", "hooks", "auto-ship-check.py")
spec = importlib.util.spec_from_file_location("auto_ship_check", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def sh(cwd, *args, env=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **(env or {})}).stdout


def init_repo(path, origin):
    os.makedirs(path)
    sh(path, "git", "init", "-q", "-b", "main")
    sh(path, "git", "config", "user.email", "t@example.com")
    sh(path, "git", "config", "user.name", "t")
    sh(path, "git", "remote", "add", "origin", origin)
    with open(os.path.join(path, "index.md"), "w") as f:
        f.write("# index\n")
    sh(path, "git", "add", "-A")
    old = "2020-01-01T00:00:00"  # before the prompt, so only the turn's commits are in its window
    sh(path, "git", "commit", "-q", "-m", "init", env={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old})


def commit(repo, files, msg="change"):
    """Write files, commit, return git's `[branch sha] msg` output like the Bash tool shows it."""
    for rel, body in files.items():
        p = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(body)
    sh(repo, "git", "add", "-A")
    return sh(repo, "git", "commit", "-m", msg)


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        hook._knowledge.clear()
        # The knowledge repo (a stand-in for ~/Developer/unleashed-memory) and a normal code repo.
        self.um = os.path.join(self.tmp, "Developer", "unleashed-memory")
        init_repo(self.um, "https://github.com/UnleashedPPOS/unleashed-memory.git")
        self.app = os.path.join(self.tmp, "Developer", "some-app")
        init_repo(self.app, "https://github.com/UnleashedPPOS/some-app.git")
        self.cwd = os.path.join(self.tmp, "Developer")  # session cwd: not a git repo, like ~/Developer
        self.prompt_ts = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
        self.entries = [{"type": "user", "timestamp": self.prompt_ts,
                         "message": {"role": "user", "content": "add the research note"}}]
        self.n = 0
        patcher = mock.patch.object(hook, "KNOWLEDGE_PATHS", [self.um])
        patcher.start()
        self.addCleanup(patcher.stop)

    def tool(self, name, inp, output="ok"):
        self.n += 1
        tid = f"toolu_{self.n}"
        self.entries.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
        self.entries.append({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tid, "content": output}]}})

    def scratch_worktree(self, repo, name="um-wt"):
        """A worktree under a scratchpad-like temp path, as research sessions use."""
        w = os.path.join(self.tmp, "private-tmp", "scratchpad", name)
        sh(repo, "git", "worktree", "add", "-q", "-b", name, w)
        return w

    def run_hook(self):
        path = os.path.join(self.tmp, "t.jsonl")
        with open(path, "w") as f:
            f.writelines(json.dumps(e) + "\n" for e in self.entries)
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"transcript_path": path, "cwd": self.cwd}))), \
                redirect_stdout(out):
            hook.main()
        return json.loads(out.getvalue()) if out.getvalue().strip() else None

    # (a) markdown / research-only changes to the knowledge repo: no block

    def test_md_note_committed_from_removed_scratch_worktree_does_not_block(self):
        w = self.scratch_worktree(self.um)
        out = commit(w, {"wiki/investigations/ai-influencers.md": "## new section\n"})
        sh(self.um, "git", "worktree", "remove", "--force", w)  # removed before the turn ends
        cmd = f'W={w} && cd "$W" && git add -A && git commit -m "research: note" && git push -q origin HEAD:main'
        self.tool("Bash", {"command": cmd}, out)
        self.assertIsNone(self.run_hook())

    def test_quiet_commit_then_log_sha_from_persisted_output_does_not_block(self):
        w = self.scratch_worktree(self.um)
        commit(w, {"wiki/investigations/x.md": "x\n"})
        sha = sh(w, "git", "log", "-1", "--format=%h %s").strip()
        sh(self.um, "git", "worktree", "remove", "--force", w)
        # big pre-commit output is moved to a file; the tool result only previews it
        with mock.patch.object(hook, "HOME", self.tmp):
            saved = os.path.join(self.tmp, ".claude", "projects", "x", "tool-results", "b.txt")
            os.makedirs(os.path.dirname(saved))
            with open(saved, "w") as f:
                f.write("[pre-commit] OK\n" * 2000 + sha + "\n")
            cmd = (f'W={w}; cd "$W" && git commit -q -m note >/dev/null; git push -q origin HEAD:main; '
                   f"cd {self.um} && git worktree remove --force $W && git log origin/main -1 --format='%h %s'")
            self.tool("Bash", {"command": cmd}, f"<persisted-output>\nOutput too large. Full output saved to: {saved}\n")
            self.assertIsNone(self.run_hook())

    def test_logged_sha_older_than_prompt_blocks(self):
        # commit -q made code, the push failed, and `git log origin/main -1` showed an old docs commit
        w = self.scratch_worktree(self.um)
        old = sh(self.um, "git", "log", "-1", "--format=%h").strip()
        commit(w, {"bin/ingest.py": "x\n"})
        self.tool("Bash", {"command": f'W={w}; cd "$W" && git commit -q -am x; git log origin/main -1 --format=%h'}, old)
        self.assertIsNotNone(self.run_hook())

    def test_raw_sources_pdf_and_html_report_do_not_block(self):
        w = self.scratch_worktree(self.um)
        out = commit(w, {"raw/research/ai-influencers/terms.pdf": "%PDF-1.4",
                         "raw/research/ai-influencers/report.html": "<html></html>",
                         "wiki/investigations/ai-influencers.md": "x\n", "log.md": "- note\n"})
        self.tool("Bash", {"command": f"cd {w} && git commit -am note"}, out)
        self.assertIsNone(self.run_hook())

    def test_write_tool_md_edit_in_knowledge_main_checkout_does_not_block(self):
        self.tool("Write", {"file_path": os.path.join(self.um, "wiki", "investigations", "new-topic.md"),
                            "content": "# t\n"})
        self.assertIsNone(self.run_hook())

    # (b) real code still blocks

    def test_py_commit_in_knowledge_repo_blocks(self):
        w = self.scratch_worktree(self.um)
        out = commit(w, {"bin/ingest.py": "print(1)\n", "wiki/investigations/x.md": "x\n"})
        self.tool("Bash", {"command": f'cd "{w}" && git commit -am "feat: ingest"'}, out)
        self.assertIn("Code changed", self.run_hook()["reason"])

    def test_ts_commit_in_code_repo_blocks(self):
        out = commit(self.app, {"src/index.ts": "export const a = 1\n"})
        self.tool("Bash", {"command": f"cd {self.app} && git commit -am 'feat: a'"}, out)
        self.assertIn("Code changed", self.run_hook()["reason"])

    def test_md_commit_in_code_repo_is_unchanged_light_check(self):
        out = commit(self.app, {"wiki/guide.md": "x\n"})
        self.tool("Bash", {"command": f"cd {self.app} && git commit -am 'docs: guide'"}, out)
        self.assertIn("Prose-only", self.run_hook()["reason"])

    def test_edit_tool_ts_and_py_block(self):
        for fp in (os.path.join(self.app, "src", "a.ts"), os.path.join(self.um, "bin", "x.py")):
            self.entries = self.entries[:1]
            self.tool("Edit", {"file_path": fp, "old_string": "a", "new_string": "b"})
            self.assertIn("Code changed", self.run_hook()["reason"], fp)

    def test_knowledge_repo_agent_instructions_still_count(self):
        w = self.scratch_worktree(self.um)
        out = commit(w, {"CLAUDE.md": "new ingest rule\n"})
        self.tool("Bash", {"command": f"cd {w} && git commit -am rules"}, out)
        self.assertIn("Prose-only", self.run_hook()["reason"])

    def test_commit_without_printed_sha_falls_back_to_blocking(self):
        w = self.scratch_worktree(self.um)
        commit(w, {"wiki/investigations/x.md": "x\n"})
        self.tool("Bash", {"command": f'W={w}; cd "$W" && git commit -q -am note'}, "")
        self.assertIsNotNone(self.run_hook())

    def test_sha_not_in_any_known_repo_blocks(self):
        other = os.path.join(self.tmp, "elsewhere", "repo")
        init_repo(other, "https://github.com/x/elsewhere.git")
        out = commit(other, {"notes.md": "x\n"})
        self.tool("Bash", {"command": 'cd "$R" && git commit -am x'}, out)
        self.assertIsNotNone(self.run_hook())


if __name__ == "__main__":
    unittest.main()
