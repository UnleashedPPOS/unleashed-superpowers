"""The monthly prune routine is defined, and the definition passes model-guard as it would be booked."""
import copy, importlib.util, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEF = os.path.join(ROOT, "docs", "learning", "monthly-prune.routine.json")

spec = importlib.util.spec_from_file_location("model_guard", os.path.join(ROOT, "cloud-kit", "hooks", "model-guard.py"))
model_guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model_guard)


def booked():
    """The RemoteTrigger create input exactly as it would be booked: the prompt block injected."""
    with open(DEF) as f:
        d = json.load(f)
    with open(os.path.join(ROOT, d["prompt_file"])) as f:
        prompt = re.search(r"```text\n(.*?)\n```", f.read(), re.S).group(1)
    inp = {"action": d["action"], "body": copy.deepcopy(d["body"])}
    inp["body"]["job_config"]["ccr"]["events"][0]["data"]["message"]["content"] = prompt
    return d, inp, prompt


class MonthlyPrune(unittest.TestCase):
    def test_passes_model_guard(self):
        d, inp, _ = booked()
        self.assertEqual(d["tool"], "RemoteTrigger")
        self.assertIsNone(model_guard.check("RemoteTrigger", inp))

    def test_opus_and_never_fable(self):
        _, inp, _ = booked()
        models = model_guard.models(inp["body"])
        self.assertEqual(models, ["claude-opus-5-5"])
        bad = copy.deepcopy(inp)
        bad["body"]["job_config"]["ccr"]["session_context"]["model"] = "claude-fable-5-2"
        self.assertIsNotNone(model_guard.check("RemoteTrigger", bad), "guard must deny the Fable variant")

    def test_monthly_schedule(self):
        d, _, _ = booked()
        fields = re.sub(r"^CRON_TZ=\S+\s+", "", d["body"]["cron_expression"]).split()
        self.assertEqual(len(fields), 5)
        minute, hour, dom, month, dow = fields
        self.assertTrue(dom.isdigit() and month == "*" and dow == "*", d["body"]["cron_expression"])
        self.assertNotIn(minute, ("0", "30"), "jitter the minute")

    def test_prompt_is_goal_shaped(self):
        _, _, prompt = booked()
        for part in ("Goal:", "Constraints:", "Done when", "Report:"):
            self.assertIn(part, prompt)
        self.assertTrue(model_guard.CAP.search(prompt))


if __name__ == "__main__":
    unittest.main()
