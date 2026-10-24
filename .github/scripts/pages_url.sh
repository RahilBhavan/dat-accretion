#!/usr/bin/env bash
# Usage: pages_url.sh <owner/repo>
# Prints the live Pages URL, ending in /. Asks the API first (it knows custom domains), else builds it from the
# repository name. The argument must come from `github.repository`, which every event carries. Do not use
# `github.event.repository.name`: a `schedule` event payload has no `repository` object, so the name is empty and the
# URL becomes https://<owner>.github.io// (a 404 that raised a false weekly alert).
set -uo pipefail
repo=${1:?usage: pages_url.sh <owner/repo>}
owner=${repo%%/*} name=${repo#*/}
[ -n "$owner" ] && [ -n "$name" ] && [ "$owner" != "$repo" ] || { echo "bad repo '$repo' (want owner/name)" >&2; exit 1; }
url=$(gh api "repos/$repo/pages" --jq .html_url 2>/dev/null) || url=
case "$url" in https://*) ;; *) url="https://$owner.github.io/$name/" ;; esac
printf '%s\n' "${url%/}/"
