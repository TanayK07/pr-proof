---
name: pr-review
description: >
  Deep PR review with inline GitHub comments — gap analysis, issue detection,
  optimization analysis. Each comment includes theory, proof, research, and
  concrete recommendations. Use when asked to "review PR", "analyze PR",
  "comment on PR", "pr review", or "review this pull request".
---

# Deep PR Review with Inline GitHub Comments

You are performing a **research-grade PR review**. Every comment you post must include
solid theory, proof from the codebase, external research, and a concrete recommendation.
No vague observations — every finding must be backed by evidence.

## When to Use

- User asks to review a PR (by number, URL, or current branch)
- User says "review", "analyze", "gap analysis", "find issues" about a PR
- User wants inline comments posted on a GitHub PR

## Phase 0: Identify the PR

1. Detect the current branch:
   ```bash
   git branch --show-current
   ```

2. Find the PR for this branch:
   ```bash
   gh pr view --json number,baseRefName,url,title,body,headRefName
   ```

3. If a PR number or URL was provided, use that instead.

4. Get the base branch from the PR metadata. Fetch it:
   ```bash
   git fetch origin <base> --quiet
   ```

5. Get the HEAD commit SHA (needed for posting inline comments):
   ```bash
   git rev-parse HEAD
   ```

## Phase 1: Understand the Diff Holistically

Do NOT start reviewing line-by-line yet. First, build a mental model.

1. **Diff stats** — what files changed and how much:
   ```bash
   git diff origin/<base> --stat
   ```

2. **Commit history** — understand the narrative arc of the PR:
   ```bash
   git log origin/<base>..HEAD --oneline
   ```

3. **Full diff** — read it all:
   ```bash
   git diff origin/<base>
   ```

4. **PR description** — what did the author say this does:
   ```bash
   gh pr view --json body -q .body
   ```

## Phase 2: Read Every Changed File IN FULL

This is critical. Do not review only diff hunks — read the complete file for every
changed file. You need surrounding context to spot:

- Patterns the new code should follow but doesn't
- Existing utilities/helpers that should have been reused
- Naming conventions that were violated
- Architectural patterns that were broken

For each new/modified file, use the Read tool on the full file path.

## Phase 3: Read Adjacent Code for Context

For each significant new file, find and read:

1. **Sibling implementations** — if the PR adds `DdsActionClient`, read `DdsServiceClient`.
   Look for patterns that should be consistent.
   ```
   Use Grep to find similar classes/functions in the codebase.
   ```

2. **Interfaces/base classes** — read the interface the new code implements.
   Understand what methods exist and which the new code uses vs. ignores.

3. **Callers** — who calls the new code? Read those files to understand usage patterns.

4. **Type registries / config files** — if the new code registers types or adds config,
   check the registry/config for consistency.

## Phase 4: Multi-Dimensional Analysis

Apply ALL of these lenses to every significant file in the diff. Not just the first
one that finds something — apply all of them.

### 4a. Gap Analysis

Compare against the canonical/reference implementation:

- **Protocol compliance** — does this implement the protocol correctly?
  Research the actual protocol spec (ROS2 REP, HTTP RFC, gRPC spec, etc.)
- **API contract** — does the new code fulfill the interface contract fully?
  Check for methods defined but not wired, classes defined but not used
- **Feature parity** — compare against equivalent implementations in other languages
  (e.g., rclpy vs this Kotlin implementation)
- **Missing error paths** — what happens on timeout, disconnection, invalid input?

### 4b. Issue Detection

Look for real bugs, not style nits:

- **Race conditions** — shared mutable state accessed from multiple threads/coroutines
  without synchronization. Trace the threading model explicitly.
- **Resource leaks** — native handles, file descriptors, connections opened but not
  closed on all paths (success, error, cancellation)
- **Silent data corruption** — endianness mismatches, encoding assumptions, truncation,
  integer overflow. Trace data through the full serialize-deserialize pipeline.
- **Fragile patterns** — code that works today but will break under reasonable future changes.
  Explain the specific change that would break it.
- **Wire compatibility** — do type names, topic names, QoS settings match what the
  counterpart expects? Verify against actual protocol specs.

### 4c. Optimization Analysis

Focus on meaningful optimizations, not micro-optimizations:

- **Unnecessary allocations in hot paths** — object creation inside polling loops,
  repeated byte array copies
- **Polling vs event-driven** — is the code polling when it could be event-driven?
  What's the cost on mobile (battery, CPU wake-ups)?
- **API ergonomics** — is the API harder to use correctly than incorrectly?
  Could a builder pattern, extension function, or default parameter prevent misuse?

## Phase 5: Write Inline Comments

For EACH finding, post an inline GitHub comment using the `gh` API.voi



Avoid using emojis

### Comment Quality Requirements

Every comment MUST include ALL of these sections:

1. **Title** — `##[One-line summary]`
   - Categories: `GAP ANALYSIS`, `ISSUE`, `OPTIMIZATION`, `RACE CONDITION`
   - Emojis: Use a microscope emoji for all

2. **Severity** — `**Severity:** HIGH | MEDIUM | LOW — [one-line impact]`

3. **The Problem** — Show the problematic code, explain what's wrong.
   Be specific — reference exact line numbers and variable names.

4. **Theory / Proof** — WHY this is a problem. Include:
   - Protocol specs, RFC references, language docs
   - Behaviour of the underlying runtime/library (with source references)
   - Mathematical analysis where relevant (collision probability, complexity)
   - Comparison with canonical implementations (rclpy, rclcpp, official SDKs)

5. **What happens today vs. what will break** — Explain why the code works now
   (if it does) and the specific scenario that breaks it.

6. **Research** — What do other implementations do? Cite specific projects/docs.

7. **Recommendation** — Concrete fix with code example. Not "consider doing X" —
   show the actual code change.

### Posting Comments

Use the GitHub API to post inline comments:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="$(cat <<'BODY'
## [Comment body here — use the structure above]
BODY
)" \
  -f commit_id="{HEAD_SHA}" \
  -f path="{file_path_relative_to_repo_root}" \
  -F line={line_number} \
  -f side="RIGHT"
```

**Important:**
- `line` must be a line number that exists in the diff (RIGHT side = new code)
- `path` is relative to repo root (e.g., `src/main/kotlin/com/example/Foo.kt`)
- `commit_id` is the full SHA from `git rev-parse HEAD`
- Use a HEREDOC for the body to handle multi-line markdown with code blocks
- Post comments in parallel where possible for speed

### Comment Targeting

- Place each comment on the most relevant line — the line where the fix should go
- For architectural issues that span multiple files, pick the primary file
- For missing code (gaps), comment on the line closest to where code should be added

## Phase 6: Summary

After posting all inline comments, provide a summary to the user:

```
## PR Review Summary: N inline comments posted

### HIGH severity (X)
- [one-line summary per finding]

### MEDIUM severity (Y)
- [one-line summary per finding]

### LOW severity (Z)
- [one-line summary per finding]
```

Include a link to the PR so the user can see all comments.

## Anti-Patterns to Avoid

- **DO NOT** comment on style, formatting, or naming conventions unless they cause bugs
- **DO NOT** post vague comments like "consider adding error handling"
- **DO NOT** flag things that are already handled in the diff (read the full diff first!)
- **DO NOT** suggest changes that would break existing tests
- **DO NOT** comment on documentation files unless they contain technical errors
- **DO NOT** post more than 15 comments — prioritize by severity
- **DO NOT** post duplicate findings (same issue in multiple places = one comment on the worst instance)

## Prioritization

If you find more than 15 issues, post only the top 15 by this priority:

1. Bugs that will cause crashes or data corruption
2. Race conditions and resource leaks
3. Wire/protocol incompatibilities
4. API contract violations (unused classes, missing implementations)
5. Performance issues with measurable impact
6. Fragile patterns that will break under specific future changes
7. Informational findings with research value
