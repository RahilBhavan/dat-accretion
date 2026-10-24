#!/usr/bin/env bash
# Usage: drop_unapproved_pr_runs.sh <owner/repo> <branch> <head sha>
# A PR opened with GITHUB_TOKEN gets a pull_request CI run that waits for a human to approve it (GitHub changelog
# 2026-06-11). Nobody approves the bot's refresh PRs: the dispatched CI run is the real check. When the PR merges
# and its branch is deleted, GitHub concludes the waiting run as `failure` with zero jobs: a red X that tested nothing.
# This deletes such runs for exactly this branch and commit. A run that started any job is never touched.
# Best effort: it prints what it did and always exits 0, because the merge has already happened.
set -uo pipefail
repo=$1 branch=$2 sha=$3
for _ in 1 2 3 4 5 6; do
  runs=$(gh api "repos/$repo/actions/workflows/ci.yml/runs?event=pull_request&branch=$branch&head_sha=$sha&per_page=20" \
           --jq '.workflow_runs[] | "\(.id) \(.status)"') || runs=
  ids=$(printf '%s\n' "$runs" | awk '$2 == "completed" {print $1}')
  pending=$(printf '%s\n' "$runs" | awk 'NF && $2 != "completed"' | wc -l)
  for id in $ids; do
    jobs=$(gh api "repos/$repo/actions/runs/$id/jobs" --jq '.total_count') || continue
    if [ "$jobs" = 0 ]; then
      conclusion=$(gh api "repos/$repo/actions/runs/$id" --jq '.conclusion') || conclusion=unknown
      if gh api -X DELETE "repos/$repo/actions/runs/$id" >/dev/null; then
        echo "deleted unapproved pull_request CI run $id ($conclusion, 0 jobs) for $branch@$sha"
      else
        echo "could not delete pull_request CI run $id ($conclusion, 0 jobs); it stays as a red X"
      fi
    else
      echo "kept pull_request CI run $id: it ran $jobs job(s)"
    fi
  done
  [ "$pending" -eq 0 ] && exit 0
  sleep "${POLL_WAIT:-5}"   # a run still waiting for approval is concluded a moment after the PR closes
done
echo "pull_request CI run(s) for $branch@$sha still not completed after 30 s; left in place"
exit 0
