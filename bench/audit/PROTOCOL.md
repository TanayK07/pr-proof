# Noise audit: protocol

Committed before any audit session was run. Every result is reported against this protocol, including results that don't favour pr-proof. Any deviation will be listed in the results file with the reason.

## Question

Code Review Bench counts a review issue as a false positive ("noise") when it doesn't match one of the PR's 2–5 human-written golden comments. Some of those issues may be real problems the golden list doesn't include. **What share of each tool's "noise" is actually a real problem, and does that share differ between tools?**

## Tools

| Tool | Source of issues and labels |
|---|---|
| cubic-v2 (#1 on the published board) | published results, Claude Opus 4.5 judge |
| CodeRabbit | published results, Claude Opus 4.5 judge |
| GitHub Copilot | published results, Claude Opus 4.5 judge |
| Claude Code (published run) | published results, Claude Opus 4.5 judge |
| pr-proof `pr-review` (current skill) | our run, judged by the calibrated shim (Opus 4.5) |
| Plain Claude Code, Opus 5.5 | our run, judged by the calibrated shim (Opus 4.5) |

## Sample

- `random.Random(20261002)`. Tools in the order above; within a tool, issues sorted by (PR URL, issue text) before sampling.
- **Noise sample:** 40 issues per tool, drawn uniformly from that tool's false positives across all 50 PRs.
- **Control sample:** 15 issues per tool, drawn uniformly from its true positives (issues the benchmark matched to a golden comment). This measures whether the auditor is biased against or towards issues in general.
- Total: 330 issues.

## Auditor

- One headless Claude Code session per issue: `claude-opus-5-5`, no user settings, hooks, MCP servers or plugins, and no web, `gh` or `curl`.
- It is given the PR checked out at its head commit, the base SHA, the PR title, and the issue's text. The benchmark's extracted issues carry no file or line, so the auditor locates the code itself.
- **It is blind:**
  - It is not told which tool wrote the issue or how the benchmark labelled it.
  - Issues are shuffled across tools before being run.
  - The prompt is identical for every issue.
- It does **not** use the pr-proof skills, so pr-proof never grades itself.
- Verdicts:
  - `REAL_BUG`: the problem exists in this PR's code and would cause incorrect behaviour, a crash, a security issue, data loss, or a meaningful performance problem.
  - `REAL_MINOR`: the claim is correct, but the impact is small (maintainability, a misleading name, a missing test, a small inefficiency).
  - `WRONG`: the claim is false, doesn't apply to this code, or rests on a misreading. The auditor must cite the code that shows this.
  - `CANT_TELL`: it cannot be settled from the code available.
- Every verdict must cite file:line evidence.

## Human check

The repo owner labels 30 issues drawn with `random.Random(20261003)` from the 330, with the same verdict definitions and the same blindness. We report auditor–human agreement (exact match and Cohen's kappa on REAL vs not-REAL). The human labels are committed before the auditor's verdicts for those 30 are revealed to the labeller.

## Metrics

Per tool:

- **Real-noise rate:** the share of noise-sample issues judged `REAL_BUG` or `REAL_MINOR`. Also reported for `REAL_BUG` alone.
- **Control confirmation rate:** the share of control issues judged REAL. A low rate means the auditor is strict, and all rates should be read in that light.
- **Adjusted precision:** (TP + FP × real-noise rate) / (TP + FP), using each tool's full benchmark counts.
- 95% intervals by bootstrap over sampled issues (2,000 resamples).

## Commitments

- Same sample sizes, prompt and auditor for every tool.
- The sample (`samples.json`, drawn by `sample.py`) is committed together with this protocol, before any audit session runs.
- All 330 verdicts, the sampled issue lists and the scripts are published in `bench/audit/`.
- No re-running of individual issues to get a different verdict. A session that crashes or times out is retried at most twice and then recorded as `CANT_TELL`.
