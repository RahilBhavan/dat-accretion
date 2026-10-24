#!/usr/bin/env bash
# Usage: drop_unapproved_pr_runs.sh <owner/repo> <branch> <head sha> <pr url or number>
# A PR opened with GITHUB_TOKEN gets a pull_request CI run that waits for a human to approve it (GitHub changelog
# 2026-06-11). Nobody approves the bot's refresh PRs: the dispatched CI run is the real check. When the PR closes,
# GitHub concludes the waiting run as `failure` with zero jobs. With a squash merge that run belongs to the PR head
# commit, which is not on main, so deleting it only tidies the Actions list and the closed PR (decision O11).
# This deletes a run only when ALL hold: it is for exactly this branch and head commit, it started zero jobs, its
# conclusion is not `startup_failure` (that is evidence of a broken ci.yml), and it concluded at or after the PR closed.
# Best effort: it prints what it did and always exits 0, because the merge has already happened.
set -uo pipefail
repo=$1 branch=$2 sha=$3 pr=$4
closed=$(gh pr view "$pr" --json closedAt --jq '.closedAt // empty') || closed=
if [ -z "$closed" ]; then
  echo "warning: could not read when $pr closed (or it is still open); deleting no runs"
  exit 0
fi
for _ in 1 2 3 4 5 6; do
  if ! runs=$(gh api "repos/$repo/actions/workflows/ci.yml/runs?event=pull_request&branch=$branch&head_sha=$sha&per_page=20" \
                --jq '.workflow_runs[] | "\(.id) \(.status)"'); then
    echo "warning: could not list pull_request CI runs for $branch@$sha; will retry"
    runs=
    sleep "${POLL_WAIT:-5}"
    continue
  fi
  ids=$(printf '%s\n' "$runs" | awk '$2 == "completed" {print $1}')
  pending=$(printf '%s\n' "$runs" | awk 'NF && $2 != "completed"' | wc -l)
  for id in $ids; do
    jobs=$(gh api "repos/$repo/actions/runs/$id/jobs" --jq '.total_count') || continue
    if [ "$jobs" != 0 ]; then
      echo "kept pull_request CI run $id: it ran $jobs job(s)"
      continue
    fi
    info=$(gh api "repos/$repo/actions/runs/$id" --jq '"\(.conclusion) \(.updated_at)"') || info="unknown "
    conclusion=${info%% *} concluded=${info#* }
    if [ "$conclusion" = startup_failure ]; then
      echo "kept pull_request CI run $id: startup_failure means ci.yml is broken, which is evidence"
    elif [ -z "$concluded" ] || [[ "$concluded" < "$closed" ]]; then
      echo "kept pull_request CI run $id: it concluded ('$concluded') before the PR closed ($closed)"
    elif gh api -X DELETE "repos/$repo/actions/runs/$id" >/dev/null; then
      echo "deleted unapproved pull_request CI run $id ($conclusion, 0 jobs) for $branch@$sha"
    else
      echo "could not delete pull_request CI run $id ($conclusion, 0 jobs); it stays in the Actions list"
    fi
  done
  [ "$pending" -eq 0 ] && exit 0
  sleep "${POLL_WAIT:-5}"   # a run still waiting for approval is concluded a moment after the PR closes
done
echo "pull_request CI run(s) for $branch@$sha still not completed after 30 s, or the list call kept failing; left in place"
exit 0
