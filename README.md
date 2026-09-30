# pr-proof

**AI code review that fact-checks its own comments before you see them.**

Most AI review bots post everything they think of. Half of it is wrong, and you spend the time you saved arguing with a bot. pr-proof is three Claude Code skills that treat every review comment as a claim that needs evidence: from the diff, from the rest of the codebase, or from the official docs. Comments that can't back themselves up get dropped.

<!-- TODO: demo GIF here — one real PR, comments drafted, 2 rejected with evidence, rest posted inline. Under 30s. -->

## The pipeline

| Skill | What it does | Say |
|---|---|---|
| `pr-review` | Reviews a PR and posts inline GitHub comments. Each one carries the reasoning, the proof, and a concrete fix. | "review PR #123" |
| `pr-comment-validation` | Takes review comments (from a human, a bot, or `pr-review`) and gives each a verdict (valid, partly valid, or wrong) with evidence. Changes no code. | "are these comments valid?" |
| `pr-validation` | End to end: checks out the PR in a worktree, validates every comment in parallel, shows you the verdicts, applies the ones you approve, and replies on each thread. | "handle the comments on PR #123" |

Use them together, or just point `pr-comment-validation` at whatever CodeRabbit or Copilot left on your PR.

## Install

As a Claude Code plugin:

```
/plugin marketplace add TanayK07/pr-proof
/plugin install pr-proof@pr-proof
```

Or copy the folders under `skills/` into `~/.claude/skills/`.

**Needs:** [Claude Code](https://code.claude.com) and an authenticated [`gh` CLI](https://cli.github.com).

## Benchmark

<!-- TODO: results on Code Review Bench (https://codereview.withmartian.com): precision, recall, and how many comments validation rejected, next to CodeRabbit / Copilot. Publish the run scripts so anyone can reproduce them. -->

Coming soon. Numbers will be reproducible, with the scripts in this repo.

## License

Apache-2.0
