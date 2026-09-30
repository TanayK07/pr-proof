#!/usr/bin/env bash
# Score all arms with Code Review Bench's pipeline, judged by Opus 4.5 via the local shim.
# Usage: bench/score_all.sh PATH_TO_code-review-benchmark/offline
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
offline="$1"
python3 "$here/judge_shim.py" --port 8787 --concurrency "${JUDGE_CONCURRENCY:-6}" & shim=$!
trap 'kill $shim 2>/dev/null' EXIT
sleep 2
cd "$offline"
export MARTIAN_API_KEY=shim MARTIAN_BASE_URL=http://127.0.0.1:8787/v1 MARTIAN_MODEL=shim/claude-opus-4-5-20251101
dir=results/shim_claude-opus-4-5-20251101
for pass in 1 2; do  # second pass retries anything that errored
  for t in claude-code opus-5.5-vanilla pr-proof-draft pr-proof; do  # claude-code = judge calibration
    echo "== pass $pass: $t"
    uv run python -m code_review_benchmark.step2_extract_comments --tool "$t" 2>&1 | grep -E "Successful|Errors"
    uv run python -m code_review_benchmark.step2_5_dedup_candidates --tool "$t" 2>&1 | grep -E "Errors"
    uv run python -m code_review_benchmark.step3_judge_comments --tool "$t" --force --dedup-groups "$dir/dedup_groups.json" 2>&1 | tail -3
  done
done
python3 "$here/check_scoring.py" "$dir" claude-code opus-5.5-vanilla pr-proof-draft pr-proof || exit 1
python3 "$here/score.py" "$dir/evaluations.json" results/anthropic_claude-opus-4-5-20251101/evaluations.json
