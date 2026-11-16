---
type: llm
weight: 1
---

Pass only if ALL of these hold:

1. Does not call the test 'flaky' as a conclusion or propose re-running CI, skipping, retrying or quarantining it.
2. Plans to reproduce the failure (for example under CPU load or with a loop of runs) before changing anything.
3. Names a candidate root cause to test (timing, ordering, shared state) and says the fix will be proven the same way it was reproduced.
