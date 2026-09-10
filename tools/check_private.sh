#!/usr/bin/env bash
# Refuse to commit anything matching a private marker.
#
# Material a custodian supplied but has not agreed to publish must not reach the tracked
# tree. This has been got wrong twice, in both cases because the check ran alongside the
# commit rather than gating it, so its output scrolled past unread. Run it as a gate:
#
#   ./tools/check_private.sh && git commit ...
#
# The marker list lives in configs/cohorts/local/private-markers.txt, which is gitignored:
# a list of private instrument names is itself private, so it cannot live in the repo.
set -uo pipefail
cd "$(dirname "$0")/.."
MARKERS="configs/cohorts/local/private-markers.txt"

if [[ ! -f "$MARKERS" ]]; then
  echo "no marker list at $MARKERS — nothing to check against, passing"
  exit 0
fi

fail=0
while IFS= read -r m; do
  [[ -z "$m" || "$m" == \#* ]] && continue
  hits=$(git grep -l -i -- "$m" -- . ':!configs/cohorts/local' 2>/dev/null || true)
  if [[ -n "$hits" ]]; then
    echo "PRIVATE MARKER IN TRACKED TREE: '$m'"
    echo "$hits" | sed 's/^/    /'
    fail=1
  fi
done < "$MARKERS"

if [[ $fail -eq 0 ]]; then
  echo "clean: no private markers in the tracked tree"
else
  echo
  echo "refusing to pass. Move the content to configs/cohorts/local/ or remove it."
fi
exit $fail
