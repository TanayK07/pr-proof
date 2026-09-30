"""Map each Code Review Bench PR to a fork PR we can check out (base/head SHAs)."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BENCH = sys.argv[1]  # path to offline/results/benchmark_data.json
data = json.load(open(BENCH))

def resolve(item):
    golden_url, entry = item
    for review in entry["reviews"]:
        url = review.get("pr_url") or ""
        if "github.com/code-review-benchmark/" not in url:
            continue
        out = subprocess.run(
            ["gh", "pr", "view", url, "--json", "baseRefOid,headRefOid,title,body,commits"],
            capture_output=True, text=True)
        if out.returncode:
            continue
        pr = json.loads(out.stdout)
        repo = url.split("github.com/")[1].split("/pull/")[0]
        return {"golden_url": golden_url, "source_repo": entry["source_repo"],
                "fork_repo": repo, "fork_pr": url, "base": pr["baseRefOid"],
                "head": pr["headRefOid"], "commits": len(pr["commits"]),
                "title": entry["pr_title"], "body": pr["body"] or ""}
    return {"golden_url": golden_url, "error": "no reachable fork PR"}

with ThreadPoolExecutor(8) as ex:
    prs = list(ex.map(resolve, data.items()))
json.dump(prs, open("prs.json", "w"), indent=1)
bad = [p for p in prs if "error" in p]
print(f"{len(prs) - len(bad)} resolved, {len(bad)} failed")
for p in bad: print("  FAIL", p["golden_url"])
