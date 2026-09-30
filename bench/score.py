"""Leaderboard: our arms (judged via the shim) next to the published tools (official judge run).

Precision/recall/F1 are micro-averaged over PRs, same as Code Review Bench's dashboard.
95% intervals come from a bootstrap over the 50 PRs.

Usage: python score.py OUR_EVALUATIONS_JSON OFFICIAL_EVALUATIONS_JSON [--calibration TOOL]
"""
import argparse, json, random

OURS = ["pr-proof", "pr-proof-draft", "opus-5.5-vanilla"]


def prf(rows):
    tp = sum(r["tp"] for r in rows); fp = sum(r["fp"] for r in rows); fn = sum(r["fn"] for r in rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0), tp, fp, fn


def per_tool(evals):
    out = {}
    for url, tools in evals.items():
        for tool, r in tools.items():
            if isinstance(r, dict) and not r.get("skipped"):
                out.setdefault(tool, {})[url] = r
    return out


def boot(rows_by_url, urls, n=2000, seed=0):
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        sample = [rows_by_url[rng.choice(urls)] for _ in urls]
        vals.append(prf(sample)[2])
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n)]


def paired_diff(a, b, urls, n=2000, seed=0):
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        s = [rng.choice(urls) for _ in urls]
        diffs.append(prf([a[u] for u in s])[2] - prf([b[u] for u in s])[2])
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n)], sum(d <= 0 for d in diffs) / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ours")
    ap.add_argument("official")
    ap.add_argument("--calibration", default="claude-code")
    a = ap.parse_args()
    ours, official = per_tool(json.load(open(a.ours))), per_tool(json.load(open(a.official)))

    rows = []
    for tool, by_url in list(official.items()) + [(t, ours[t]) for t in OURS if t in ours]:
        src = "ours" if tool in OURS else "published"
        p, r, f, tp, fp, fn = prf(by_url.values())
        rows.append((f, tool, p, r, len(by_url), tp, fp, src, by_url))
    rows.sort(key=lambda x: -x[0])

    print("| # | Tool | Precision | Recall | F1 (95% CI) | PRs | Comments judged |")
    print("|---|---|---|---|---|---|---|")
    for i, (f, tool, p, r, n, tp, fp, src, by_url) in enumerate(rows, 1):
        lo, hi = boot(by_url, list(by_url))
        name = f"**{tool}**" if src == "ours" else tool
        print(f"| {i} | {name} | {p:.1%} | {r:.1%} | {f:.1%} ({lo:.1%}–{hi:.1%}) | {n} | {tp + fp} |")

    if a.calibration in ours and a.calibration in official:
        urls = sorted(set(ours[a.calibration]) & set(official[a.calibration]))
        o = prf([ours[a.calibration][u] for u in urls]); p_ = prf([official[a.calibration][u] for u in urls])
        print(f"\nCalibration ({a.calibration}, {len(urls)} PRs): shim judge P={o[0]:.1%} R={o[1]:.1%} "
              f"F1={o[2]:.1%} vs published P={p_[0]:.1%} R={p_[1]:.1%} F1={p_[2]:.1%}")

    for x, y in [("pr-proof", "opus-5.5-vanilla"), ("pr-proof", "pr-proof-draft")]:
        if x in ours and y in ours:
            urls = sorted(set(ours[x]) & set(ours[y]))
            lo, hi, p_le0 = paired_diff(ours[x], ours[y], urls)
            print(f"F1 {x} minus {y}: 95% CI {lo:+.1%} to {hi:+.1%} (share of resamples <= 0: {p_le0:.3f})")


if __name__ == "__main__":
    main()
