#!/usr/bin/env bash
# Remove ralph-whisper (keeps nothing except, optionally, the model cache).
set -u
APP="$HOME/.local/share/whisper-dictation"
BIN="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE="whisper-dictation.service"

systemctl --user disable --now "$SERVICE" 2>/dev/null || true
rm -f "$UNIT_DIR/$SERVICE"
rm -rf "$UNIT_DIR/$SERVICE.d"
systemctl --user daemon-reload 2>/dev/null || true

rm -f "$BIN/dictation-ctl" "$BIN/dictation-toggle" "$BIN/dictation-switch-to-gpu"

# remove GNOME shortcut entry
if command -v gsettings >/dev/null; then
  SCHEMA=org.gnome.settings-daemon.plugins.media-keys
  BASE=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings
  OURS="$BASE/ralph-whisper/"
  NEWLIST=$(python3 - "$OURS" "$SCHEMA" <<'PY'
import ast, subprocess, sys
ours, schema = sys.argv[1], sys.argv[2]
cur = subprocess.check_output(["gsettings","get",schema,"custom-keybindings"]).decode().strip()
try: lst = ast.literal_eval(cur) if cur not in ("@as []","") else []
except Exception: lst = []
print(str([x for x in lst if x != ours]))
PY
)
  gsettings set $SCHEMA custom-keybindings "$NEWLIST" 2>/dev/null || true
fi

echo "Removed service, scripts, and shortcut."
read -r -p "Also delete $APP (venv + model cache)? [y/N] " ans
[ "$ans" = "y" ] && rm -rf "$APP" && echo "Deleted $APP" || echo "Kept $APP"
