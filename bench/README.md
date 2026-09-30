# Benchmark harness

Reproduces the numbers in the main README on [Code Review Bench](https://github.com/withmartian/code-review-benchmark) (offline, 50 PRs).

Everything runs on a logged-in Claude Code subscription through `claude -p`. No API key is needed.

## Setup

```bash
git clone https://github.com/withmartian/code-review-benchmark
cp -r code-review-benchmark/offline work/offline && (cd work/offline && uv sync)
# The judge's 30s per-call timeout is too short for claude -p; raise it (scoring is unchanged):
sed -i 's/^LLM_CALL_TIMEOUT = 30/LLM_CALL_TIMEOUT = 600/' \
  work/offline/code_review_benchmark/step{3_judge_comments,2_5_dedup_candidates}.py
python prepare.py code-review-benchmark/offline/results/benchmark_data.json   # -> prs.json
```

## pr-comment-validation as a filter on another tool

```bash
python run_filter.py prs.json work/checkouts \
  code-review-benchmark/offline/results/anthropic_claude-opus-4-5-20251101 --tool coderabbit
python score_filter.py code-review-benchmark/offline/results/anthropic_claude-opus-4-5-20251101 --tool coderabbit
```

Scoring uses the benchmark's published labels, so no judge calls are needed.

## pr-review against plain Claude Code

```bash
python run_reviews.py prs.json work/checkouts --jobs 4          # vanilla + pr-proof arms
python to_benchmark.py work/offline/results/benchmark_data.json work/offline/results/benchmark_data.json
./score_all.sh work/offline                                     # extract, dedup, judge, check, leaderboard
```

## Files

| File | Purpose |
|---|---|
| `prepare.py` | Maps each benchmark PR to a fork PR with base and head SHAs |
| `run_reviews.py` | Runs the review arms in isolated headless sessions: no settings, hooks, MCP, web, `gh` or `curl` |
| `run_filter.py` / `score_filter.py` | Runs and scores pr-comment-validation over another tool's issues |
| `judge_shim.py` | OpenAI-compatible endpoint over `claude -p` for the benchmark's judge, with a disk cache |
| `to_benchmark.py` | Adds our arms to the benchmark's data file |
| `score_all.sh` | Full scoring pipeline plus the consistency check |
| `check_scoring.py` | Fails if any review was judged on raw comments instead of its extracted issues. The benchmark falls back to raw comments silently. |
| `score.py` | Leaderboard with bootstrap confidence intervals |
