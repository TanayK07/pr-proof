"""Score pr-comment-validation as a filter over another tool's review issues.

Uses the official Code Review Bench labels (Claude Opus 4.5 judge): each of the tool's
issues is either a true positive (matches a golden comment) or a false positive.
An issue is kept if its verdict is VALID or PARTIALLY_VALID.

Usage: python score_filter.py OFFICIAL_RESULTS_DIR [--tool coderabbit]
"""
import argparse, json
from pathlib import Path

KEEP = {"VALID", "PARTIALLY_VALID"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("official")
    ap.add_argument("--tool", default="coderabbit")
    ap.add_argument("--partial", action="store_true", help="only score PRs that have verdicts")
    a = ap.parse_args()
    cands = json.load(open(Path(a.official) / "candidates.json"))
    evals = json.load(open(Path(a.official) / "evaluations.json"))
    runs = Path(__file__).resolve().parent / "runs-filter" / a.tool

    base = {"tp": 0, "fp": 0, "fn": 0}
    filt = {"tp": 0, "fp": 0, "fn": 0}
    real_total = real_kept = noise_total = noise_kept = prs = 0
    dropped_real = []
    for url, tools in evals.items():
        ev = tools.get(a.tool)
        items = cands.get(url, {}).get(a.tool, [])
        pr_id = url.split("github.com/")[1].replace("/pull/", "-").replace("/", "_")
        vfile = runs / pr_id / "verdicts.json"
        if not ev or ev.get("skipped"):
            continue
        golden = ev["tp"] + ev["fn"]
        if a.partial and items and not vfile.exists():
            continue
        for k in base:
            base[k] += ev[k]
        if not items:  # tool said nothing: nothing to filter
            filt["fn"] += golden
            continue
        if not vfile.exists():
            raise SystemExit(f"missing verdicts for {pr_id}")
        prs += 1
        verdicts = {v["id"]: v for v in json.loads(vfile.read_text())}
        kept_text = {c["text"] for i, c in enumerate(items)
                     if verdicts.get(i, {}).get("verdict", "").upper() in KEEP}
        tp_kept = 0
        for t in ev["true_positives"]:
            real_total += 1
            if t["matched_candidate"] in kept_text:
                real_kept += 1
                tp_kept += 1
            else:
                dropped_real.append((pr_id, t["matched_candidate"][:140]))
        fp_kept = sum(1 for f in ev["false_positives"] if f["candidate"] in kept_text)
        noise_total += len(ev["false_positives"])
        noise_kept += fp_kept
        filt["tp"] += tp_kept
        filt["fp"] += fp_kept
        filt["fn"] += golden - tp_kept

    def prf(m):
        p = m["tp"] / (m["tp"] + m["fp"]) if m["tp"] + m["fp"] else 0
        r = m["tp"] / (m["tp"] + m["fn"]) if m["tp"] + m["fn"] else 0
        return p, r, 2 * p * r / (p + r) if p + r else 0

    print(f"PRs with verdicts: {prs}")
    print(f"Real bugs kept:  {real_kept}/{real_total} ({real_kept / max(real_total, 1):.1%})")
    print(f"Noise removed:   {noise_total - noise_kept}/{noise_total} "
          f"({(noise_total - noise_kept) / max(noise_total, 1):.1%})")
    print("\n| | Precision | Recall | F1 | Issues posted |\n|---|---|---|---|---|")
    for name, m in [(a.tool, base), (f"{a.tool} + pr-proof filter", filt)]:
        p, r, f = prf(m)
        print(f"| {name} | {p:.1%} | {r:.1%} | {f:.1%} | {m['tp'] + m['fp']} |")
    if dropped_real:
        print("\nReal bugs the filter dropped:")
        for pr_id, t in dropped_real:
            print(f"  {pr_id}: {t}")


if __name__ == "__main__":
    main()
