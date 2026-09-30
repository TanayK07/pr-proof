"""Run the review arms on Code Review Bench PRs in isolated headless Claude Code sessions.

Arms (all on the same checkout, same model):
  vanilla    plain Claude Code, no plugin, asked to review the diff
  pr-proof   /pr-proof:pr-review in draft mode; we keep both the raw drafts
             (before self-validation) and the validated set

Sessions load no user settings, hooks, MCP servers or other plugins. Web tools, gh and
curl are blocked so a session cannot read the original PR discussion (the golden
comments came from there).

Usage: python run_reviews.py prs.json WORKDIR [--only N] [--jobs 4] [--arms vanilla,pr-proof]
"""
import argparse, json, os, shutil, subprocess, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
MODEL = "claude-opus-5-5"
TIMEOUT_S = 60 * 60
DENY = ["WebFetch", "WebSearch", "Bash(gh:*)", "Bash(curl:*)", "Bash(wget:*)",
        "Bash(git push:*)", "Bash(git fetch:*)", "Bash(git pull:*)"]

VANILLA_PROMPT = """Review the code changes in this repository: `git diff {base} HEAD` is the pull request.
Title: {title}

PR description:
{body}

Find real problems a careful senior reviewer would flag: bugs, logic errors, security
issues, broken contracts, performance problems. Read whatever code you need.
You have no network access; do not try to use GitHub.

Write your review comments to {out}/comments.json as a JSON array of
{{"path": "<file relative to repo root>", "line": <line in the new code>, "body": "<comment>"}}.
Write only that file. Do not modify the repository."""

PRPROOF_PROMPT = """/pr-proof:pr-review

Review the pull request checked out here, in DRAFT MODE: do not post anything, do not call
GitHub (there is no network access). The PR diff is `git diff {base} HEAD` (base commit
{base}; history is shallow, so use two-dot diffs against that SHA instead of a base branch).
Title: {title}

PR description:
{body}

Use {out}/drafts.json as the drafts file. As soon as Phase 5 is complete, and before
Phase 6 starts, copy it to {out}/drafts_raw.json. After Phase 6, drafts.json must hold
{{"kept": [...], "dropped": [...]}}. Do not modify the repository."""


HOME = str(Path.home())


def scrub(text: str) -> str:
    """Remove local machine paths from anything we keep, so logs don't leak the operator's setup."""
    text = text.replace(str(Path(__file__).resolve().parent), "bench")
    return text.replace(HOME, "~").replace(HOME.replace("/", "-"), "-HOME")


def sh(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


repo_locks: dict[str, threading.Lock] = {}


def checkout(pr, work: Path) -> Path:
    name = pr["source_repo"].split("-")[0]
    store = work / "repos" / f"{name}.git"
    wt = work / "wt" / pr["id"]
    with repo_locks.setdefault(name, threading.Lock()):
        if not store.exists():
            sh(["git", "init", "-q", "--bare", str(store)])
            sh(["git", "remote", "add", "origin", "x"], cwd=store)
            sh(["git", "config", "remote.origin.promisor", "true"], cwd=store)
            sh(["git", "config", "remote.origin.partialclonefilter", "blob:none"], cwd=store)
        sh(["git", "remote", "set-url", "origin", f"https://github.com/{pr['fork_repo']}"], cwd=store)
        sh(["git", "fetch", "-q", "--filter=blob:none", "--depth=1", "origin", pr["base"], pr["head"]], cwd=store)
        if wt.exists():
            sh(["git", "worktree", "remove", "--force", str(wt)], cwd=store, check=False)
            shutil.rmtree(wt, ignore_errors=True)
        sh(["git", "worktree", "add", "-q", "--detach", str(wt), pr["head"]], cwd=store)
        # Lazy blob fetches for the base tree happen now, while origin points at this fork.
        sh(["git", "diff", "--stat", pr["base"], "HEAD"], cwd=wt)
    return wt


def cleanup(pr, work: Path, wt: Path):
    name = pr["source_repo"].split("-")[0]
    store = work / "repos" / f"{name}.git"
    with repo_locks[name]:
        sh(["git", "worktree", "remove", "--force", str(wt)], cwd=store, check=False)
    shutil.rmtree(wt, ignore_errors=True)


def run_session(prompt: str, wt: Path, out: Path, plugin: bool, meta: dict | None = None) -> dict:
    """Run one isolated headless session in `wt`; it may only write to `out`."""
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", "--model", MODEL, "--setting-sources", "", "--strict-mcp-config",
           "--no-session-persistence", "--permission-mode", "bypassPermissions",
           "--add-dir", str(out), "--output-format", "json",
           "--disallowedTools", *DENY]
    if plugin:
        cmd += ["--plugin-dir", str(PLUGIN_DIR)]
    cmd += ["--", prompt]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_") and k != "CLAUDECODE"}
    env.pop("GH_TOKEN", None)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=wt, capture_output=True, text=True, timeout=TIMEOUT_S, env=env)
        raw, err = p.stdout, p.stderr[-2000:]
    except subprocess.TimeoutExpired:
        raw, err = "", "timeout"
    meta = {**(meta or {}), "seconds": round(time.time() - t0), "stderr": err}
    try:
        events = json.loads(raw)
        res = next(e for e in events if e.get("type") == "result")
        meta.update(cost_usd=res.get("total_cost_usd"), is_error=res.get("is_error"),
                    num_turns=res.get("num_turns"), models=list(res.get("modelUsage", {})),
                    final=res.get("result", "")[-3000:])
    except Exception as e:  # noqa: BLE001
        meta.update(parse_error=str(e), raw_tail=raw[-2000:])
    (out / "result.json").write_text(scrub(json.dumps(meta, indent=1)))
    for f in out.glob("*.json"):
        f.write_text(scrub(f.read_text()))
    return meta


def run_arm(arm, pr, wt: Path, out: Path):
    if (out / "result.json").exists():
        return json.loads((out / "result.json").read_text())
    fmt = dict(base=pr["base"], title=pr["title"], body=pr["body"][:4000] or "(none)", out=out)
    prompt = (VANILLA_PROMPT if arm == "vanilla" else PRPROOF_PROMPT).format(**fmt)
    return run_session(prompt, wt, out, plugin=arm == "pr-proof", meta={"arm": arm, "id": pr["id"]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prs")
    ap.add_argument("work")
    ap.add_argument("--only", type=int, default=0, help="first N PRs")
    ap.add_argument("--ids", default="", help="comma-separated PR ids")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--arms", default="vanilla,pr-proof")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    runs = Path(__file__).resolve().parent / "runs"
    prs = json.load(open(a.prs))
    for pr in prs:
        pr["id"] = pr["golden_url"].split("github.com/")[1].replace("/pull/", "-").replace("/", "_")
    if a.ids:
        prs = [p for p in prs if p["id"] in a.ids.split(",")]
    if a.only:
        prs = prs[: a.only]
    arms = a.arms.split(",")

    def one(pr):
        if all((runs / pr["id"] / arm / "result.json").exists() for arm in arms):
            return
        try:
            wt = checkout(pr, work)
        except subprocess.CalledProcessError as e:
            print(f"[{pr['id']}] checkout failed: {e.stderr[-500:]}", flush=True)
            return
        try:
            with ThreadPoolExecutor(len(arms)) as ex:
                for m in ex.map(lambda arm: run_arm(arm, pr, wt, runs / pr["id"] / arm), arms):
                    print(f"[{pr['id']}] {m['arm']}: {m.get('seconds')}s cost=${m.get('cost_usd')} "
                          f"err={m.get('is_error') or m.get('parse_error') or ''}", flush=True)
        finally:
            cleanup(pr, work, wt)

    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(one, prs))


if __name__ == "__main__":
    main()
