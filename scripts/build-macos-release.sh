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
DIST_DIR="${DIST_DIR:-dist/macos-release}"
BUILD_DIR="${BUILD_DIR:-build/macos-release/$ARCH}"
PKG_IDENTIFIER="${PKG_IDENTIFIER:-io.github.google-finance-mcp.cli}"

case "$ARCH" in
  arm64|x86_64) ;;
  *)
    echo "Unsupported macOS architecture: $ARCH" >&2
    exit 1
    ;;
esac

PACKAGE_VERSION="${VERSION#v}"
PACKAGE_VERSION="${PACKAGE_VERSION%%+*}"
PACKAGE_VERSION="${PACKAGE_VERSION%%-*}"

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

if [[ "$(uname -s)" == "Darwin" ]]; then
  codesign --force --sign - --timestamp=none "$BINARY"
  codesign --verify --verbose "$BINARY"
fi

TARBALL="$DIST_DIR/google-finance-mcp-${VERSION}-macos-${ARCH}.tar.gz"
tar -C "$BUILD_DIR/bin" -czf "$TARBALL" google-finance-mcp

PKGROOT="$BUILD_DIR/pkgroot"
mkdir -p "$PKGROOT/usr/local/bin"
cp "$BINARY" "$PKGROOT/usr/local/bin/google-finance-mcp"

PKG="$DIST_DIR/google-finance-mcp-${VERSION}-macos-${ARCH}.pkg"
pkgbuild \
  --root "$PKGROOT" \
  --identifier "$PKG_IDENTIFIER" \
  --version "$PACKAGE_VERSION" \
  --install-location / \
  "$PKG"

(
  cd "$DIST_DIR"
  shasum -a 256 "$(basename "$TARBALL")" "$(basename "$PKG")" > "google-finance-mcp-${VERSION}-macos-${ARCH}.sha256"
)

echo "Built release artifacts:"
echo "  $TARBALL"
echo "  $PKG"
echo "  $DIST_DIR/google-finance-mcp-${VERSION}-macos-${ARCH}.sha256"
