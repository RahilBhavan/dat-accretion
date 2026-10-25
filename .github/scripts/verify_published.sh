#!/usr/bin/env bash
# Usage: verify_published.sh <site url ending in /> <commit>
# Passes when every data/*.csv at <commit> is byte-identical to <site>data/<name>.csv (pages.yml publishes them
# there). The Pages CDN serves each file with `cache-control: max-age=600` and a query string does not bypass it
# (observed: x-cache HIT), so an edge that cached the old copy just before the deploy can keep serving it for up to
# 10 minutes. It therefore retries for about RETRIES x WAIT = 24 x 30 s = 12 minutes (decision O14).
set -uo pipefail
site=$1 sha=$2
retries=${RETRIES:-24} wait=${WAIT:-30}
dir=$(mktemp -d)
names=$(git ls-tree --name-only "$sha" data/ | grep '\.csv$' | sed 's|^data/||')
[ -n "$names" ] || { echo "no data/*.csv at $sha"; exit 1; }
for attempt in $(seq "$retries"); do
  bad=
  for f in $names; do
    git show "$sha:data/$f" > "$dir/want"
    if ! curl -fsS -o "$dir/got" "${site}data/$f" || ! cmp -s "$dir/want" "$dir/got"; then
      bad="$bad $f"
    fi
  done
  if [ -z "$bad" ]; then
    echo "published: all $(echo "$names" | wc -w) CSVs at ${site}data/ match $sha"
    exit 0
  fi
  echo "attempt $attempt: live differs from $sha for:$bad"
  [ "$attempt" -lt "$retries" ] && sleep "$wait"
done
echo "published site does not match $sha after $retries attempts"
exit 1
