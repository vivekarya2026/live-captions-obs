#!/usr/bin/env bash
# Rebuilds every Live Captions icon from the SVG sources in this folder.
#   app icon  : app.svg -> desktop/src-tauri/icons/* (via `tauri icon`)
#   tray icons: glyph drawn below -> desktop/src-tauri/resources/tray_*.png
# Needs: rsvg-convert (brew install librsvg), node deps in desktop/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
ICONS="$ROOT/desktop/src-tauri/icons"
RES="$ROOT/desktop/src-tauri/resources"
TMP="$(mktemp -d)"

# App icon (1024 master, then every platform size).
rsvg-convert -w 1024 -h 1024 "$HERE/app.svg" -o "$ICONS/logo.png"
(cd "$ROOT/desktop" && npx tauri icon "$ICONS/logo.png" -o "$ICONS" >/dev/null)
rm -rf "$ICONS/android" "$ICONS/ios"

# Tray glyph: the same wave-to-text mark, 64px, one colour.
glyph() { # $1 colour, $2 warning badge (0/1)
  local c="$1" badge=""
  if [ "$2" = 1 ]; then
    # "!" is cut out of the badge so it reads in any single colour.
    badge="<mask id='b'><rect width='64' height='64' fill='#fff'/>
             <rect x='47' y='40' width='4' height='11' rx='2' fill='#000'/>
             <circle cx='49' cy='56' r='2.3' fill='#000'/></mask>
           <circle cx='49' cy='49' r='13' fill='$c' mask='url(#b)'/>"
  fi
  cat <<EOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <mask id="m"><rect width="64" height="64" fill="#fff"/>$( [ "$2" = 1 ] && echo "<circle cx='49' cy='49' r='17' fill='#000'/>")</mask>
  <g stroke="$c" stroke-width="6" stroke-linecap="round" mask="url(#m)">
    <line x1="9" y1="27" x2="9" y2="37"/>
    <line x1="18" y1="17" x2="18" y2="47"/>
    <line x1="27" y1="22" x2="27" y2="42"/>
    <line x1="38" y1="20" x2="56" y2="20"/>
    <line x1="38" y1="32" x2="53" y2="32"/>
    <line x1="38" y1="44" x2="47" y2="44"/>
  </g>
  $badge
</svg>
EOF
}
render() { glyph "$1" "$2" > "$TMP/g.svg"; rsvg-convert -w 64 -h 64 "$TMP/g.svg" -o "$RES/$3"; }
render "#ffffff" 0 tray_idle.png
render "#000000" 0 tray_idle_dark.png
render "#305cde" 0 tray_app.png
render "#ffffff" 1 tray_idle_warning.png
render "#000000" 1 tray_idle_warning_dark.png
render "#305cde" 1 tray_app_warning.png
rm -rf "$TMP"
echo "icons rebuilt"
