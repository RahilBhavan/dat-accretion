#!/usr/bin/env bash
# Usage: verify_published.sh <site url ending in /> <commit>
# Passes when every data/*.csv at <commit> is byte-identical to <site>data/<name>.csv (pages.yml publishes them
# there). The Pages CDN can serve the old copy for a few minutes, so it retries for up to RETRIES x WAIT seconds.
set -uo pipefail
site=$1 sha=$2
retries=${RETRIES:-12} wait=${WAIT:-15}
dir=$(mktemp -d)
names=$(git ls-tree --name-only "$sha" data/ | grep '\.csv$' | sed 's|^data/||')
[ -n "$names" ] || { echo "no data/*.csv at $sha"; exit 1; }
for attempt in $(seq "$retries"); do
  bad=
  for f in $names; do
    git show "$sha:data/$f" > "$dir/want"
    if ! curl -fsS -o "$dir/got" "${site}data/$f?commit=$sha&try=$attempt" || ! cmp -s "$dir/want" "$dir/got"; then
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
