"""Draw the noise-audit sample exactly as PROTOCOL.md specifies. Writes samples.json.

Usage: python sample.py OFFICIAL_RESULTS_DIR SHIM_RESULTS_DIR
"""
import json, random, sys
from pathlib import Path

official, shim = Path(sys.argv[1]), Path(sys.argv[2])
TOOLS = [  # (tool name in results, source dir, label used in reports)
    ("cubic-v2", official, "cubic-v2"),
    ("coderabbit", official, "CodeRabbit"),
    ("copilot", official, "GitHub Copilot"),
    ("claude-code", official, "Claude Code (published)"),
    ("pr-proof", shim, "pr-proof pr-review"),
    ("opus-5.5-vanilla", shim, "Claude Code (Opus 5.5)"),
]
N_NOISE, N_CONTROL = 40, 15

rng = random.Random(20261002)
samples = []
for tool, src, label in TOOLS:
    evals = json.load(open(src / "evaluations.json"))
    cands = json.load(open(src / "candidates.json"))
    noise, control = [], []
    for url, tools in evals.items():
        ev = tools.get(tool)
        if not ev or ev.get("skipped"):
            continue
        where = {c["text"]: (c.get("path"), c.get("line")) for c in cands.get(url, {}).get(tool, [])}
        for fp in ev["false_positives"]:
            noise.append((url, fp["candidate"], *where.get(fp["candidate"], (None, None))))
        for tp in ev["true_positives"]:
            control.append((url, tp["matched_candidate"], *where.get(tp["matched_candidate"], (None, None))))
    for kind, pool, n in (("noise", sorted(set(noise)), N_NOISE), ("control", sorted(set(control)), N_CONTROL)):
        for url, text, path, line in rng.sample(pool, n):
            samples.append({"tool": tool, "label": label, "kind": kind, "golden_url": url,
                            "issue": text, "path": path, "line": line})

for i, s in enumerate(samples):
    s["uid"] = f"a{i:03d}"
run_order = [s["uid"] for s in samples]
rng.shuffle(run_order)  # blind: tools interleaved when run
Path(__file__).with_name("samples.json").write_text(json.dumps(
    {"seed": 20261002, "run_order": run_order, "samples": samples}, indent=1))
print(f"{len(samples)} issues:", {t: sum(s['tool'] == t for s in samples) for t, *_ in TOOLS})
