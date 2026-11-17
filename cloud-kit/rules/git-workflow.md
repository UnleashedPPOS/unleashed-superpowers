# Git workflow

- Auto-commit without asking when the founder's intent is clear, the change is coherent and self-contained, no secrets ✓ or large binaries are involved, and tests/build pass. Commit small and often. (Overrides the default "never commit unless asked".)
- Still ask first ✓ for destructive ops (`reset --hard`, `push --force`, `branch -D`), amending shared commits, force-push to main/master, and skipping git hooks.
- Commit messages: `<type>: <description>` (optional body), type one of feat, fix, refactor, docs, test, chore, perf, ci ✓.
- PRs: read the full commit history and `git diff <base>...HEAD`, write a full summary with a test plan, push with `-u`.
