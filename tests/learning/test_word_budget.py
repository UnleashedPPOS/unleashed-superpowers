"""The always-loaded set (cloud-kit rules + High-Level style) must stay under the word budget."""
import json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corrections  # noqa: E402


class WordBudget(unittest.TestCase):
    def test_under_budget(self):
        b, per, total = corrections.word_count()
        biggest = ", ".join(f"{k}={v}" for k, v in sorted(per.items(), key=lambda kv: -kv[1])[:3])
        self.assertLessEqual(total, b["budget"], f"always-loaded set is {total} words, budget {b['budget']} "
                             f"(largest: {biggest}). Move detail into a skill; don't raise the budget.")

    def test_budget_is_at_least_30_percent_cut(self):
        with open(corrections.BUDGET) as f:
            b = json.load(f)
        self.assertLessEqual(b["budget"], b["baseline_words"] * 0.7)

    def test_budget_covers_rules_and_style(self):
        _, files = corrections.always_loaded_files()
        rels = {os.path.relpath(f, ROOT) for f in files}
        self.assertIn("output-styles/high-level.md", rels)
        self.assertTrue(any(r.startswith("cloud-kit/rules/") for r in rels))
        self.assertGreaterEqual(len(rels), 5)


if __name__ == "__main__":
    unittest.main()
