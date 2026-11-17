#!/bin/sh
# Clone pinned upstream sources into ./ext and download RoboCasa kitchen assets (~10GB).
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/ext" "$ROOT/outputs"
grep -v '^#' "$ROOT/ext.lock" | while read -r name url rev; do
  [ -z "$name" ] && continue
  dir="$ROOT/ext/$name"
  if [ ! -d "$dir/.git" ]; then git clone -q "$url" "$dir"; fi
  git -C "$dir" fetch -q origin
  git -C "$dir" checkout -q "$rev" 2>/dev/null || git -C "$dir" checkout -q "origin/$rev"
  echo "$name $(git -C "$dir" rev-parse HEAD)"
done
[ -f "$ROOT/ext/robocasa/robocasa/macros_private.py" ] || \
  cp "$ROOT/ext/robocasa/robocasa/macros.py" "$ROOT/ext/robocasa/robocasa/macros_private.py"
[ -f "$ROOT/ext/robosuite/robosuite/macros_private.py" ] || \
  cp "$ROOT/ext/robosuite/robosuite/macros.py" "$ROOT/ext/robosuite/robosuite/macros_private.py"
# numba JIT segfaults inside llvmlite in this image (261117); robosuite runs fine without it
sed -i 's/^ENABLE_NUMBA = True/ENABLE_NUMBA = False/' "$ROOT/ext/robosuite/robosuite/macros_private.py"
if [ "$1" = "--assets" ]; then
  yes y | "$ROOT/scripts/run.sh" python -m robocasa.scripts.download_kitchen_assets
fi
