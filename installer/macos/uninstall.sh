#!/bin/bash
# Removes Live Captions from this Mac:
#   "/Applications/Live Captions.app/Contents/Resources/uninstall.sh"
# Add --all to also delete the downloaded models and settings (~/.livecaptions).
# Your saved sessions in Documents/Live Captions are never deleted.
set -u
RES="$(cd "$(dirname "$0")" && pwd)"
echo "Removing Live Captions…"
touch "$HOME/.livecaptions/stop_translator" 2>/dev/null; sleep 2
if pgrep -x OBS >/dev/null; then echo "Please quit OBS first, then run this again."; exit 1; fi
PYTHONPATH="$RES/app" "$RES/python/bin/python3" -m livecaptions.obs_setup --remove || true
if [ "${1:-}" = "--all" ]; then rm -rf "$HOME/.livecaptions"; echo "Deleted models and settings."; fi
sudo rm -rf "/Applications/Live Captions.app" && sudo pkgutil --forget org.livecaptions.obs >/dev/null 2>&1
echo "Done. (The LocalVocal OBS plugin was left in place.)"
