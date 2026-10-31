#!/bin/bash
# Builds "LiveCaptions-<version>-macOS-<arch>.pkg".
#
#   installer/macos/build.sh                 # this Mac's chip, version from __init__.py
#   ARCH=x86_64 installer/macos/build.sh     # Intel Macs (works on Apple Silicon via Rosetta)
#   ARCH=arm64  installer/macos/build.sh     # Apple Silicon (M1 or newer)
#   VERSION=1.2.0 installer/macos/build.sh
#
# The package contains its own Python with the small packages (translation,
# vocabulary); PyTorch + the speech and translation models download on first
# start, with progress in the Live Captions window.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
VERSION="${VERSION:-$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/app/livecaptions/__init__.py")}"
ARCH="${ARCH:-$(uname -m)}"   # arm64 (Apple Silicon) or x86_64 (Intel)
case "$ARCH" in
  arm64)  PBS_ARCH="aarch64"; CHIP="Apple Silicon (M1 or newer)" ;;
  x86_64) PBS_ARCH="x86_64";  CHIP="an Intel processor" ;;
  *) echo "unknown ARCH=$ARCH (use arm64 or x86_64)"; exit 1 ;;
esac
# Run pip etc. as the target CPU (an Intel build on Apple Silicon goes through Rosetta)
RUN=(arch "-$ARCH")
PBS_TAG="20261026"
PY_VERSION="3.11.18"
PY_TARBALL="cpython-${PY_VERSION}+${PBS_TAG}-${PBS_ARCH}-apple-darwin-install_only.tar.gz"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PY_TARBALL}"

BUILD="$ROOT/build/macos-$ARCH"
CACHE="$ROOT/build/cache"
PKGROOT="$BUILD/root"
APP="$PKGROOT/Applications/Live Captions.app"
RES="$APP/Contents/Resources"
OUT="$ROOT/dist/LiveCaptions-${VERSION}-macOS-${ARCH}.pkg"

echo "== Live Captions $VERSION for macOS ($ARCH)"
rm -rf "$BUILD"
mkdir -p "$CACHE" "$RES" "$APP/Contents/MacOS" "$ROOT/dist"

# 1. Python
if [ ! -f "$CACHE/$PY_TARBALL" ]; then
  echo "-- downloading Python $PY_VERSION"
  curl -fL --retry 3 -o "$CACHE/$PY_TARBALL.part" "$PY_URL"
  mv "$CACHE/$PY_TARBALL.part" "$CACHE/$PY_TARBALL"
fi
tar -xzf "$CACHE/$PY_TARBALL" -C "$RES"          # -> Resources/python
PY="$RES/python/bin/python3"
echo "-- installing packages"
EXTRA=()
if [ "$ARCH" = "x86_64" ]; then EXTRA=("numpy<2" --only-binary=:all:); fi  # PyTorch 2.2.2 needs NumPy 1.x
"${RUN[@]}" "$PY" -m pip install --quiet --disable-pip-version-check --no-cache-dir --no-warn-script-location \
  -r "$ROOT/requirements.txt" ${EXTRA[@]+"${EXTRA[@]}"}
# Trim: test suites, idle/tk, caches
rm -rf "$RES/python/lib/python3.11/test" "$RES/python/lib/python3.11/idlelib" \
       "$RES/python/lib/python3.11/tkinter" "$RES/python/lib/python3.11/turtledemo"
find "$RES/python" -name "__pycache__" -type d -prune -exec rm -rf {} +

# 2. Live Captions itself + the OBS script
rsync -a --exclude "__pycache__" --exclude "*.pyc" "$ROOT/app/livecaptions" "$RES/app/"
rsync -a "$ROOT/obs" "$RES/"
cp "$ROOT/LICENSE" "$RES/LICENSE.txt"
cp "$HERE/uninstall.sh" "$RES/uninstall.sh"
chmod +x "$RES/uninstall.sh"
"${RUN[@]}" "$PY" -m compileall -q "$RES/app" >/dev/null

# 3. The app bundle (opens the Live Captions window; OBS starts it too)
cat > "$APP/Contents/MacOS/LiveCaptions" <<'EOF'
#!/bin/bash
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$RES/app" && exec "$RES/python/bin/python3" -m livecaptions "$@"
EOF
chmod +x "$APP/Contents/MacOS/LiveCaptions"
sed -e "s/@VERSION@/$VERSION/g" -e "s/@ARCH@/$ARCH/g" "$HERE/Info.plist" > "$APP/Contents/Info.plist"
if [ -f "$HERE/AppIcon.icns" ]; then cp "$HERE/AppIcon.icns" "$RES/AppIcon.icns"; fi
# Apple Silicon only runs signed code: ad-hoc signature (not an Apple Developer ID)
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || codesign --force --sign - "$APP"

# 4. The installer package
pkgbuild --analyze --root "$PKGROOT" "$BUILD/component.plist" >/dev/null
/usr/libexec/PlistBuddy -c "Set :0:BundleIsRelocatable false" "$BUILD/component.plist"
pkgbuild --root "$PKGROOT" --component-plist "$BUILD/component.plist" \
  --identifier org.livecaptions.obs --version "$VERSION" \
  --scripts "$HERE/scripts" --install-location / "$BUILD/LiveCaptions.pkg"
mkdir -p "$BUILD/resources"
sed "s/@CHIP@/$CHIP/g" "$HERE/welcome.html" > "$BUILD/resources/welcome.html"
cp "$ROOT/LICENSE" "$BUILD/resources/LICENSE.txt"
sed -e "s/@VERSION@/$VERSION/g" -e "s/@ARCH@/$ARCH/g" "$HERE/distribution.xml" > "$BUILD/distribution.xml"
productbuild --distribution "$BUILD/distribution.xml" --resources "$BUILD/resources" \
  --package-path "$BUILD" "$OUT"
echo "== built $OUT ($(du -h "$OUT" | cut -f1))"

# 5. The same installer inside a .dmg (what Mac users expect to download)
DMG="${OUT%.pkg}.dmg"
STAGE="$BUILD/dmg"
rm -rf "$STAGE" "$DMG" && mkdir -p "$STAGE"
cp "$OUT" "$STAGE/Install Live Captions.pkg"
cat > "$STAGE/Read me.txt" <<EOF
Live Captions $VERSION for Macs with $CHIP

1. Quit OBS if it is open.
2. Double-click "Install Live Captions.pkg".
   If macOS says it can't be opened: System Settings -> Privacy & Security -> Open Anyway.
3. The Live Captions window opens and downloads the models once (about 5 GB).

Guide: https://github.com/vivekarya2026/live-captions-obs/blob/main/docs/SETUP_GUIDE.md
EOF
hdiutil create -quiet -volname "Live Captions $VERSION" -srcfolder "$STAGE" -fs HFS+ -format UDZO -ov "$DMG"
echo "== built $DMG ($(du -h "$DMG" | cut -f1))"
