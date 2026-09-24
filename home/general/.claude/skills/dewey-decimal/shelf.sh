#!/usr/bin/env bash
# shelf.sh — resolve, open and log the scratch shelf for the current git branch,
# and keep the shelf's session-handoff ledger (HANDOFF.md).
#
#   shelf.sh [-y] [start]    resolve the shelf; print its path
#   shelf.sh handoff         print a new handoff document path; add its ledger row
#   shelf.sh read HANDOFF    mark a ledger row read (HANDOFF = path relative to shelf)
#
# Shelf: <toplevel>/.scratch/<branch>/, the branch name sanitised to one path
# segment (case kept). Detached HEAD -> detached-<short-sha>.
#
# Default and start both open the shelf (mkdir) and append
# "<iso8601>|<shelf>|<raw branch>" to .scratch/SESSION.md when the shelf differs
# from the last logged one. `start` also logs unconditionally and lists unread
# handoffs.
#
# stdout lines:  shelf: <abs path>
#                changed: <old> -> <new>
#                pending: <handoff> written_by=<id> written_at=<ts> [MISSING]
#
# Exit: 0 ok | 2 not a git repo | 3 trunk or detached: confirm, then rerun with -y

set -euo pipefail

YES=0
[[ ${1-} == -y ]] && { YES=1; shift; }
CMD=${1-}

top=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "not a git repo: ask the user for a shelf name" >&2
  exit 2
}
branch=$(git rev-parse --abbrev-ref HEAD)
if [[ $branch == HEAD ]]; then
  shelf=detached-$(git rev-parse --short HEAD)
else
  shelf=$(printf %s "$branch" | sed -E 's#[^A-Za-z0-9._-]#-#g; s/-+/-/g; s/^-+//; s/-+$//')
fi

root=$top/.scratch
dir=$root/$shelf
ledger=$dir/HANDOFF.md
sid=${CLAUDE_CODE_SESSION_ID:-unknown}

if [[ $YES == 0 && ! -d $dir ]] && [[ $branch == HEAD || $branch =~ ^(master|main|develop)$ ]]; then
  echo "confirm: shelving onto '$branch' ($dir) — ask the user, then rerun with -y" >&2
  exit 3
fi

mkdir -p "$dir"

log_visit() { printf '%s|%s|%s\n' "$(date -Iseconds)" "$shelf" "$branch" >>"$root/SESSION.md"; }

ensure_ledger() {
  [[ -f $ledger ]] || printf '%s\n' \
    '| handoff | written_by | written_at | read_by | read_at |' \
    '| ------- | ---------- | ---------- | ------- | ------- |' >"$ledger"
}

case $CMD in
  handoff)
    mkdir -p "$dir/handoff"
    rel=handoff/handoff.$(date +%Y%m%d-%H%M%S).md
    while [[ -e $dir/$rel ]] || grep -qF "| $rel |" "$ledger" 2>/dev/null; do
      sleep 1; rel=handoff/handoff.$(date +%Y%m%d-%H%M%S).md
    done
    ensure_ledger
    printf '| %s | %s | %s | - | - |\n' "$rel" "$sid" "$(date -Iseconds)" >>"$ledger"
    echo "$dir/$rel"
    exit 0
    ;;
  read)
    rel=${2:?usage: shelf.sh read HANDOFF}
    [[ -f $ledger ]] || { echo "no ledger at $ledger" >&2; exit 1; }
    # Fill read_by/read_at only on the matching row, and only if still unread.
    awk -v rel="$rel" -v sid="$sid" -v ts="$(date -Iseconds)" -F' *\\| *' '
      $2 == rel && $5 == "-" { printf "| %s | %s | %s | %s | %s |\n", $2, $3, $4, sid, ts; next }
      { print }' "$ledger" >"$ledger.tmp" && mv "$ledger.tmp" "$ledger"
    exit 0
    ;;
esac

echo "shelf: $dir"

last=$(tail -n1 "$root/SESSION.md" 2>/dev/null | cut -d'|' -f2 || true)
if [[ $CMD == start ]]; then
  log_visit
elif [[ $last != "$shelf" ]]; then
  [[ -n $last ]] && echo "changed: $last -> $shelf"
  log_visit
fi

if [[ $CMD == start && -f $ledger ]]; then
  awk -F' *\\| *' 'NR > 2 && $5 == "-" { print $2, $3, $4 }' "$ledger" |
    while read -r rel by at; do
      miss=; [[ -f $dir/$rel ]] || miss=' MISSING'
      echo "pending: $rel written_by=$by written_at=$at$miss"
    done
fi
