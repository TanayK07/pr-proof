"""Fail if any review was judged on raw comments instead of its extracted issues.

step3 silently falls back to raw comments when extraction hasn't produced candidates,
which changes how precision is counted. Every scored review must use its candidates.

Usage: python check_scoring.py RESULTS_MODEL_DIR TOOL [TOOL ...]
"""
import json, sys
from pathlib import Path

d = Path(sys.argv[1])
cands = json.load(open(d / "candidates.json"))
evals = json.load(open(d / "evaluations.json"))
bad = []
for tool in sys.argv[2:]:
    for url, tools in evals.items():
        ev = tools.get(tool)
        if not ev or ev.get("skipped"):
            continue
        n = len([c for c in cands.get(url, {}).get(tool, []) if c.get("text")])
        if n == 0 or n != ev["total_candidates"] or ev.get("errors_count"):
            bad.append(f"{tool} {url}: candidates={n} judged={ev['total_candidates']} errors={ev.get('errors_count')}")
print("\n".join(bad) if bad else "check_scoring: every review judged on its extracted issues")
sys.exit(1 if bad else 0)
