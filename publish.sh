#!/bin/bash
# Runs on the machine every 30 min: record a beat, render, replace the single commit on the pulse branch.
# The branch keeps one force-pushed commit, so it never grows and never counts as a contribution.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

HERE="$(cd "$(dirname "$0")" && pwd)"
REMOTE="${PULSE_REMOTE:-https://github.com/lkyxuan/lkyxuan.git}"
WORK="$HERE/pulse"
GIT=(git -C "$WORK" -c credential.helper= -c 'credential.helper=!gh auth git-credential'
     -c user.name=lkyxuan -c user.email=lkyxuan@users.noreply.github.com)

rm -rf "$WORK"
git init -q "$WORK"
"${GIT[@]}" remote add origin "$REMOTE"
if "${GIT[@]}" fetch -q --depth 1 origin pulse 2>/dev/null; then
  "${GIT[@]}" checkout -q -B pulse FETCH_HEAD
else
  "${GIT[@]}" checkout -q --orphan pulse
fi

python3 "$HERE/render.py" beat "$WORK"

"${GIT[@]}" add state.json pulse.svg
if [ -n "$("${GIT[@]}" rev-parse --verify -q HEAD || true)" ]; then
  "${GIT[@]}" commit -q --amend -m "pulse"
else
  "${GIT[@]}" commit -q -m "pulse"
fi
"${GIT[@]}" push -q --force origin pulse
