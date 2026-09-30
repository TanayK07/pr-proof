"""Run pr-comment-validation over another tool's review issues on Code Review Bench PRs.

Input is the tool's issues exactly as the benchmark extracted and labelled them
(official candidates.json, judged by Claude Opus 4.5). Each session sees only the
issue text, file and line, never the labels. Verdicts go to runs-filter/<tool>/<pr>/.

Usage: python run_filter.py prs.json WORKDIR OFFICIAL_RESULTS_DIR [--tool coderabbit] [--jobs 6]
"""
import argparse, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import run_reviews as rr

PROMPT = """/pr-proof:pr-comment-validation

An AI code reviewer left the review issues listed in {inp} on the pull request checked
out here. There is no GitHub access and no network: read the issues from that file
instead of fetching comments. The PR diff is `git diff {base} HEAD` (history is shallow,
so diff against that SHA).
Title: {title}

PR description:
{body}

Run Phases 1-3 only: classify, investigate each issue against the code, and give a
verdict. Do not change any code and do not post replies. Write the verdicts to
{out}/verdicts.json as a JSON array with one entry per issue:
{{"id": <id>, "verdict": "VALID" | "PARTIALLY_VALID" | "INVALID" | "STYLE_PREFERENCE" | "GOOD_QUESTION",
  "actionable": "YES" | "NO" | "OPTIONAL", "evidence": "<file:line references and what they show>"}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prs")
    ap.add_argument("work")
    ap.add_argument("official")
    ap.add_argument("--tool", default="coderabbit")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    cands = json.load(open(Path(a.official) / "candidates.json"))
    runs = Path(__file__).resolve().parent / "runs-filter" / a.tool
    prs = json.load(open(a.prs))
    for pr in prs:
        pr["id"] = pr["golden_url"].split("github.com/")[1].replace("/pull/", "-").replace("/", "_")
    if a.ids:
        prs = [p for p in prs if p["id"] in a.ids.split(",")]

    def one(pr):
        out = runs / pr["id"]
        items = cands.get(pr["golden_url"], {}).get(a.tool, [])
        if not items or (out / "result.json").exists():
            return
        out.mkdir(parents=True, exist_ok=True)
        issues = [{"id": i, "path": c.get("path"), "line": c.get("line"), "issue": c["text"]}
                  for i, c in enumerate(items)]
        (out / "issues.json").write_text(json.dumps(issues, indent=1))
        try:
            wt = rr.checkout(pr, work)
        except Exception as e:  # noqa: BLE001
            print(f"[{pr['id']}] checkout failed: {e}", flush=True)
            return
        try:
            prompt = PROMPT.format(inp=out / "issues.json", base=pr["base"], title=pr["title"],
                                   body=pr["body"][:4000] or "(none)", out=out)
            m = rr.run_session(prompt, wt, out, plugin=True)
            print(f"[{pr['id']}] {len(issues)} issues: {m.get('seconds')}s cost=${m.get('cost_usd')} "
                  f"err={m.get('is_error') or m.get('parse_error') or ''}", flush=True)
        finally:
            rr.cleanup(pr, work, wt)

    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, prs))


if __name__ == "__main__":
    main()
