"""Add our review arms to a copy of Code Review Bench's benchmark_data.json.

Tools added:
  opus-5.5-vanilla   plain Claude Code (claude-opus-5-5), no skills
  pr-proof-draft     pr-review drafts before self-validation
  pr-proof           pr-review after self-validation (what would be posted)

Usage: python to_benchmark.py BENCHMARK_DATA_IN BENCHMARK_DATA_OUT
"""
import json, sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent / "runs"


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def comments(items):
    return [{"path": c.get("path"), "line": c.get("line"), "body": c.get("body") or c.get("claim", "")}
            for c in items or []]


data = json.load(open(sys.argv[1]))
missing = []
for golden_url, entry in data.items():
    pr_id = golden_url.split("github.com/")[1].replace("/pull/", "-").replace("/", "_")
    entry["reviews"] = [r for r in entry["reviews"]
                        if r["tool"] not in ("opus-5.5-vanilla", "pr-proof-draft", "pr-proof")]
    done = {arm: (RUNS / pr_id / arm / "result.json").exists() for arm in ("vanilla", "pr-proof")}
    vanilla = load(RUNS / pr_id / "vanilla" / "comments.json") if done["vanilla"] else None
    raw = load(RUNS / pr_id / "pr-proof" / "drafts_raw.json") if done["pr-proof"] else None
    final = load(RUNS / pr_id / "pr-proof" / "drafts.json") if done["pr-proof"] else None
    if isinstance(raw, dict):  # tolerate {"drafts": [...]} shapes
        raw = raw.get("drafts") or raw.get("kept", []) + raw.get("dropped", [])
    arms = {"opus-5.5-vanilla": vanilla, "pr-proof-draft": raw,
            "pr-proof": final.get("kept") if isinstance(final, dict) else None}
    for tool, items in arms.items():
        if items is None:
            missing.append(f"{pr_id}:{tool}")
            continue
        entry["reviews"].append({"tool": tool, "repo_name": pr_id, "pr_url": golden_url,
                                 "review_comments": comments(items)})
json.dump(data, open(sys.argv[2], "w"), indent=1)
print(f"missing {len(missing)}: {missing[:20]}")
