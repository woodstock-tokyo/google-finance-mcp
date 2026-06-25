#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${VERSION:-$(python - <<'PY'
import tomllib

with open("pyproject.toml", "rb") as project_file:
    print(tomllib.load(project_file)["project"]["version"])
PY
)}"
ARCH="${ARCH:-$(uname -m)}"
DIST_DIR="${DIST_DIR:-dist/linux-release}"
BUILD_DIR="${BUILD_DIR:-build/linux-release/$ARCH}"

case "$ARCH" in
  x86_64|aarch64|arm64) ;;
  *)
    echo "Unsupported Linux architecture: $ARCH" >&2
    exit 1
    ;;
esac

if [[ "$ARCH" == "arm64" ]]; then
  ARCH="aarch64"
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

python -m pip install --upgrade pip
python -m pip install ".[release]"

PYINSTALLER_EXCLUDES=(
  --exclude-module astroid
  --exclude-module black
  --exclude-module docutils
  --exclude-module IPython
  --exclude-module ipykernel
  --exclude-module jedi
  --exclude-module jupyter_client
  --exclude-module matplotlib
  --exclude-module nbformat
  --exclude-module notebook
  --exclude-module numpy
  --exclude-module PIL
  --exclude-module PyQt5
  --exclude-module pytest
  --exclude-module sphinx
  --exclude-module tkinter
  --exclude-module zmq
)

python -m PyInstaller \
  --clean \
  --noconfirm \
  --onefile \
  --strip \
  --name google-finance-mcp \
  --distpath "$BUILD_DIR/bin" \
  --workpath "$BUILD_DIR/pyinstaller-work" \
  --specpath "$BUILD_DIR/spec" \
  --copy-metadata mcp \
  --copy-metadata httpx \
  --copy-metadata anyio \
  "${PYINSTALLER_EXCLUDES[@]}" \
  packaging/pyinstaller/entrypoint.py

BINARY="$BUILD_DIR/bin/google-finance-mcp"
chmod 755 "$BINARY"

TARBALL="$DIST_DIR/google-finance-mcp-${VERSION}-linux-${ARCH}.tar.gz"
tar -C "$BUILD_DIR/bin" -czf "$TARBALL" google-finance-mcp

(
  cd "$DIST_DIR"
  shasum -a 256 "$(basename "$TARBALL")" > "google-finance-mcp-${VERSION}-linux-${ARCH}.sha256"
)

echo "Built release artifacts:"
echo "  $TARBALL"
echo "  $DIST_DIR/google-finance-mcp-${VERSION}-linux-${ARCH}.sha256"
