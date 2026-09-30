#!/usr/bin/env bash
# Fails if the repo (working tree or any commit) contains private identifiers or secrets.
# Add your own private terms to .leak-terms (one regex per line, gitignored).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
patterns='ghp_[A-Za-z0-9]{20,}|github_pat_|sk-ant-|AKIA[0-9A-Z]{16}|ATATT[0-9A-Za-z_-]{10,}|xox[abprs]-|BEGIN [A-Z ]*PRIVATE KEY'
patterns="$patterns|$HOME/|${HOME//\//-}"
if [[ -f .leak-terms ]]; then
  patterns="$patterns|$(grep -v '^\s*$' .leak-terms | paste -sd'|')"
fi
status=0
if git grep -nIiE "$patterns" -- ':!scripts/leak-check.sh' ; then status=1; fi
if git ls-files --others --exclude-standard -z | grep -zv '^scripts/leak-check.sh$' | xargs -0 -r grep -nIiE "$patterns" ; then status=1; fi
if git log --all -p | grep -qIiE "$patterns"; then echo "match found in git history"; status=1; fi
[[ $status -eq 0 ]] && echo "leak-check: clean" || { echo "leak-check: FAILED"; exit 1; }
