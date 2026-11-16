"""Corrections registry integrity: one home per fact, generated reports fresh, eval cases well-formed."""
import glob, json, os, re, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corrections  # noqa: E402

REQUIRED = ("id", "rule", "source", "class", "home", "anchor")


def frontmatter(path):
    text = open(path).read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


class Registry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = corrections.load()

    def test_required_fields_and_classes(self):
        for e in self.entries:
            for k in REQUIRED:
                self.assertTrue(e.get(k), f"{e.get('id')}: missing {k}")
            self.assertIn(e["class"], ("check", "eval", "prose"), e["id"])
            if e["class"] == "eval":
                self.assertTrue(e.get("eval", "").startswith("evals/"), e["id"])
            if e["class"] == "check":
                self.assertTrue(e.get("check"), e["id"])

    def test_unique_ids(self):
        ids = [e["id"] for e in self.entries]
        self.assertEqual(len(ids), len(set(ids)), [i for i in ids if ids.count(i) > 1])

    def test_anchor_lives_in_home(self):
        for e in self.entries:
            path = os.path.join(ROOT, e["home"])
            self.assertTrue(os.path.exists(path), f"{e['id']}: home {e['home']} missing")
            with open(path) as f:
                text = f.read()
            body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)  # frontmatter doesn't count
            self.assertTrue(e["anchor"].lower() in body.lower(), f"{e['id']}: anchor not in the body of {e['home']}")
            self.assertGreaterEqual(len(e["anchor"]), 12, f"{e['id']}: anchor too vague to pin one line")

    def test_external_checks_exist(self):
        ids = {e["id"] for e in self.entries}
        for e in self.entries:
            c = e.get("check", "")
            if not c.startswith("external:"):
                continue
            target = c[len("external:"):]
            if target.startswith("same check:"):
                for ref in target[len("same check:"):].split(","):
                    self.assertIn(ref.strip(), ids, e["id"])
            else:
                self.assertTrue(os.path.exists(os.path.join(ROOT, target)), f"{e['id']}: {target}")

    def test_retired_rules_not_shipped(self):
        with open(os.path.join(ROOT, "cloud-kit", "RETIRED")) as f:
            retired = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        self.assertTrue(retired)
        for name in retired:
            self.assertFalse(os.path.exists(os.path.join(ROOT, "cloud-kit", "rules", name)), name)

    def test_inventory_fresh(self):
        with open(corrections.INVENTORY) as f:
            self.assertEqual(f.read(), corrections.render_inventory(self.entries), "run scripts/corrections.py inventory")

    def test_unenforced_fresh(self):
        with open(corrections.UNENFORCED) as f:
            self.assertEqual(f.read(), corrections.render_unenforced(self.entries), "run scripts/corrections.py unenforced")

    def test_every_eval_case_written_and_well_formed(self):
        cases = {e["eval"] for e in self.entries if e["class"] == "eval"}
        cases |= {os.path.relpath(d, ROOT) for d in glob.glob(os.path.join(ROOT, "evals", "*")) if os.path.isdir(d)}
        for case in cases:
            fm, body = frontmatter(os.path.join(ROOT, case, "prompt.md"))
            self.assertIn("max_turns:", fm, case)
            self.assertIn("allowed_tools:", fm, case)
            self.assertTrue(body.split("---", 2)[2].strip(), case)
            fm, body = frontmatter(os.path.join(ROOT, case, "graders", "criteria.md"))
            self.assertIn("type: llm", fm, case)
            self.assertRegex(body, r"\n1\. ", case)

    def test_no_secret_shaped_strings_in_evals_or_docs(self):
        sys.path.insert(0, os.path.join(ROOT, "cloud-kit", "hooks"))
        import corrections_lib as lib
        files = glob.glob(os.path.join(ROOT, "evals", "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "docs", "learning", "*.md"))
        for f in files:
            hits = lib.evaluate("write", open(f).read(), {"path": f}, actions=("block",))
            self.assertFalse([e["id"] for e, _ in hits if e["id"].startswith("secret")], f)


if __name__ == "__main__":
    unittest.main()
