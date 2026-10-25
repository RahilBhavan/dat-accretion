#!/usr/bin/env bash
# Usage: alert_issue.sh <exact title> <body line>
# One open issue per title: comment on the open issue whose title is exactly <title>, else open one.
# Pages through every open issue instead of using search: the search index lags, so two quick failures could both miss,
# and a fixed --limit would miss an issue beyond it. Pull requests (which the issues API also returns) are skipped.
set -euo pipefail
title=$1 body=$2
repo=${GH_REPO:-${GITHUB_REPOSITORY:-'{owner}/{repo}'}}
n=$(gh api --paginate "repos/$repo/issues?state=open&per_page=100" \
      | jq -rs --arg t "$title" 'add // [] | map(select((.pull_request | not) and .title == $t)) | sort_by(.number) | .[0].number // empty')
if [ -n "$n" ]; then
  gh issue comment "$n" --body "Failed again: $body"
  echo "alert: commented on issue #$n ($title)"
else
  gh issue create --title "$title" --body "Run: $body"
  echo "alert: opened a new issue ($title)"
fi
