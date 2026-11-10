#!/usr/bin/env python3
"""Minimal coding agent on the raw Anthropic Messages API (bills API credits, not the subscription).

Usage:
  vault run --keys ANTHROPIC_API_KEY -- python3 api-agent.py --cwd <dir> --prompt-file task.md \
      [--model claude-sonnet-5-5] [--budget-usd 40] [--log run.log]
Tools: bash (runs in --cwd) and the text editor tool. Stops at end_turn or when the budget is hit.
"""
import argparse, json, os, subprocess, sys, time, urllib.request, urllib.error

PRICES = {  # USD per million tokens: input, output
    "claude-sonnet-5-5": (3.0, 15.0), "claude-opus-5-5": (5.0, 25.0), "claude-haiku-5-5": (1.0, 5.0)}

TOOLS = [
    {"name": "bash", "description": "Run a shell command (bash -lc) in the working directory. Returns stdout+stderr (truncated to 30k chars). Timeout 600s.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "write_file", "description": "Create or overwrite a file with the given content.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace an exact, unique string in a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}},
]


def call(body):
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:500]
            if e.code in (429, 500, 529) and attempt < 5:
                time.sleep(15 * (attempt + 1)); continue
            raise SystemExit(f"API error {e.code}: {msg}")


def run_tool(name, inp, cwd):
    try:
        if name == "bash":
            p = subprocess.run(["bash", "-lc", inp["command"]], cwd=cwd, capture_output=True, text=True, timeout=600)
            out = (p.stdout + p.stderr)
            if len(out) > 30000: out = out[:15000] + "\n...[truncated]...\n" + out[-15000:]
            return f"exit={p.returncode}\n{out}"
        path = inp["path"] if os.path.isabs(inp["path"]) else os.path.join(cwd, inp["path"])
        if name == "write_file":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            open(path, "w").write(inp["content"]); return "written"
        if name == "edit_file":
            s = open(path).read(); n = s.count(inp["old"])
            if n != 1: return f"error: old string found {n} times"
            open(path, "w").write(s.replace(inp["old"], inp["new"])); return "edited"
    except Exception as e:
        return f"error: {e}"
    return "unknown tool"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--cwd", required=True); a.add_argument("--prompt-file", required=True)
    a.add_argument("--model", default="claude-sonnet-5-5"); a.add_argument("--budget-usd", type=float, default=40)
    a.add_argument("--log", default=None); a.add_argument("--max-turns", type=int, default=600)
    o = a.parse_args()
    if os.path.exists(o.prompt_file + ".model"):  # per-task model override (lets a running pipeline switch model)
        o.model = open(o.prompt_file + ".model").read().strip()
    log = open(o.log, "a") if o.log else sys.stdout
    pin, pout = PRICES.get(o.model, (5.0, 25.0))
    system = [{"type": "text", "cache_control": {"type": "ephemeral"}, "text":
               f"You are an autonomous senior engineer working in {o.cwd}. Use the tools to read, edit, build and test. "
               "Work until the task is fully done; read files with bash (sed -n, rg). Never print secrets. "
               "When finished, reply with a short final report and no tool calls."}]
    msgs = [{"role": "user", "content": open(o.prompt_file).read()}]
    spent = 0.0
    for turn in range(o.max_turns):
        # cache the conversation prefix each turn
        last = msgs[-1]["content"]
        if isinstance(last, list) and last: last[-1]["cache_control"] = {"type": "ephemeral"}
        r = call({"model": o.model, "max_tokens": 16000, "system": system, "tools": TOOLS, "messages": msgs})
        for m in msgs:
            if isinstance(m["content"], list):
                for b in m["content"]:
                    if isinstance(b, dict): b.pop("cache_control", None)
        u = r.get("usage", {})
        spent += (u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) * 1.25
                  + u.get("cache_read_input_tokens", 0) * 0.1) * pin / 1e6 + u.get("output_tokens", 0) * pout / 1e6
        msgs.append({"role": "assistant", "content": r["content"]})
        results = []
        for b in r["content"]:
            if b["type"] == "text": print(f"[{turn}] ${spent:.2f} TEXT: {b['text'][:2000]}", file=log, flush=True)
            if b["type"] == "tool_use":
                print(f"[{turn}] ${spent:.2f} {b['name']}: {json.dumps(b['input'])[:300]}", file=log, flush=True)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": run_tool(b["name"], b["input"], o.cwd)})
        if r.get("stop_reason") != "tool_use":
            print(f"DONE ${spent:.2f}", file=log, flush=True); return
        if spent > o.budget_usd:
            print(f"BUDGET HIT ${spent:.2f}", file=log, flush=True); return
        msgs.append({"role": "user", "content": results})
    print(f"MAX TURNS ${spent:.2f}", file=log, flush=True)


if __name__ == "__main__":
    main()
