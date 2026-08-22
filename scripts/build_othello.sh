#!/bin/sh
# Build the browser version of the Othello game.
#
#   scripts/build_othello.sh              -> docs/games/othello.html
#   scripts/build_othello.sh /tmp/out.html
#
# The result is one self-contained page: the sources go in as base64 and
# Pyodide runs them in the browser, so nothing is executed server side.
set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
# Deliberately outside SRC. Building into it would feed the previous
# result back in as a source file on the next run.
OUT=${1:-$REPO/docs/games/othello.html}
SRC=$REPO/docs/games/othello
PYXEL=$REPO/.venv/bin/pyxel

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# The app root has to hold the package at the path its imports name, so
# that `docs.games.othello.*` resolves once the root is on sys.path.
mkdir -p "$WORK/othello/docs/games"
cp -r "$SRC" "$WORK/othello/docs/games/othello"

# Only the sources are ever needed, and dropping the rest keeps stray
# .DS_Store and cache files out of the page.
find "$WORK" -type f ! -name '*.py' -delete
find "$WORK" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# pyxel puts the startup script's own directory on sys.path rather than
# the app root, so the script has to sit at the root to put it there.
cat > "$WORK/othello/launch.py" <<'EOF'
"""Startup script for the packaged web build."""

from docs.games.othello.main import main

main()
EOF

cd "$WORK"
"$PYXEL" package othello othello/launch.py >/dev/null
"$PYXEL" app2html othello.pyxapp >/dev/null

cp "$WORK/othello.html" "$OUT"
echo "wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
