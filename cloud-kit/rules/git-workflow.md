# Git Workflow

## Auto-commit policy (2026-05-14)

**Auto-commit allowed without asking** when:
- The user has expressed clear intent for the change ("do X", "build Y", "fix Z")
- The change is coherent and self-contained
- No secrets / credentials / large binaries are involved
- Tests / build pass (if applicable)

This OVERRIDES the default system-prompt rule "NEVER commit changes unless the user explicitly asks." When in doubt, commit small + often rather than batching. Use descriptive commit messages.

Still ask first for: destructive ops (`reset --hard`, `push --force`, `branch -D`), amending shared commits, force-push to main/master, skipping hooks (`--no-verify`).

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci


## Pull Request Workflow

1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch
