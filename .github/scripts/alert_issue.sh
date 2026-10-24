#!/usr/bin/env bash
# Usage: alert_issue.sh <exact title> <body line>
# One open issue per title: comment on the open issue whose title is exactly <title>, else open one.
# Lists open issues instead of using search: the search index lags, so two quick failures could both miss.
set -euo pipefail
title=$1 body=$2
n=$(gh issue list --state open --limit 200 --json number,title \
      --jq "map(select(.title == \"$title\")) | sort_by(.number) | .[0].number // empty")
if [ -n "$n" ]; then
  gh issue comment "$n" --body "Failed again: $body"
  echo "alert: commented on issue #$n ($title)"
else
  gh issue create --title "$title" --body "Run: $body"
  echo "alert: opened a new issue ($title)"
fi
