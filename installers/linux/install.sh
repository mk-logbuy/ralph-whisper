#!/usr/bin/env bash
# Install ralph-whisper: voice dictation for Linux (X11 / GNOME).
#   ./install.sh          # CPU
#   ./install.sh --gpu    # also install CUDA runtime wheels (see README)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"      # repo root (installers/linux/ -> ../../)
APP="$HOME/.local/share/whisper-dictation"
BIN="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE="whisper-dictation.service"
HOTKEY="${WD_HOTKEY:-<Super>v}"     # gsettings binding string
GPU=0
[ "${1:-}" = "--gpu" ] && GPU=1

say() { printf '\033[1;36m→ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }

# --- prerequisites -----------------------------------------------------------
missing=()
command -v pw-record  >/dev/null || missing+=("pipewire-bin (pw-record)")
command -v xdotool    >/dev/null || missing+=("xdotool")
command -v notify-send >/dev/null || missing+=("libnotify-bin")
python3 -c "import venv"  >/dev/null 2>&1 || missing+=("python3-venv")
python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk" \
    >/dev/null 2>&1 || missing+=("python3-gi gir1.2-gtk-3.0 python3-gi-cairo (bubble UI)")
if [ "${#missing[@]}" -gt 0 ]; then
  warn "Missing system packages:"
  for m in "${missing[@]}"; do echo "    - $m"; done
  echo "  Install them (Debian/Ubuntu/Pop!_OS), e.g.:"
  echo "    sudo apt install pipewire-bin xdotool libnotify-bin python3-venv \\"
  echo "        python3-gi gir1.2-gtk-3.0 python3-gi-cairo"
  echo
  read -r -p "Continue anyway? [y/N] " ans
  [ "$ans" = "y" ] || exit 1
fi

if [ "${XDG_SESSION_TYPE:-}" != "x11" ]; then
  warn "Session is '${XDG_SESSION_TYPE:-unknown}', not x11 — xdotool typing needs X11."
fi

# --- files -------------------------------------------------------------------
say "Installing to $APP"
mkdir -p "$APP" "$BIN" "$UNIT_DIR"
# python package (daemon is run as `python -m ralph_whisper` with cwd=$APP)
rm -rf "$APP/ralph_whisper"
cp -r "$REPO/ralph_whisper" "$APP/ralph_whisper"
# standalone overlay scripts spawned as subprocesses
install -m 644 "$REPO/ralph_whisper/bubble_gtk.py" "$APP/bubble_gtk.py"
install -m 644 "$REPO/ralph_whisper/bubble_tk.py"  "$APP/bubble_tk.py"
install -m 755 "$REPO/bin/dictation-ctl"    "$APP/dictation-ctl"
install -m 755 "$REPO/bin/dictation-toggle" "$APP/dictation-toggle"
install -m 755 "$HERE/switch-to-gpu.sh"     "$APP/switch-to-gpu.sh"
ln -sf "$APP/dictation-ctl"    "$BIN/dictation-ctl"
ln -sf "$APP/dictation-toggle" "$BIN/dictation-toggle"
ln -sf "$APP/switch-to-gpu.sh" "$BIN/dictation-switch-to-gpu"

# --- venv --------------------------------------------------------------------
if [ ! -x "$APP/venv/bin/python" ]; then
  say "Creating venv"
  python3 -m venv "$APP/venv"
fi
say "Installing Python deps"
"$APP/venv/bin/pip" install --upgrade pip -q
"$APP/venv/bin/pip" install -q -r "$REPO/requirements.txt"
if [ "$GPU" = 1 ]; then
  say "Installing CUDA runtime wheels (GPU)"
  "$APP/venv/bin/pip" install -q -r "$REPO/requirements-gpu.txt"
fi

# --- systemd unit ------------------------------------------------------------
say "Installing systemd user service"
sed -e "s|@DISPLAY@|${DISPLAY:-:0}|" \
    -e "s|@XAUTHORITY@|${XAUTHORITY:-$HOME/.Xauthority}|" \
    "$HERE/whisper-dictation.service.in" > "$UNIT_DIR/$SERVICE"
systemctl --user import-environment DISPLAY XAUTHORITY 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE"

# --- GNOME shortcut ----------------------------------------------------------
if command -v gsettings >/dev/null; then
  say "Binding GNOME shortcut ($HOTKEY) → dictation-toggle"
  SCHEMA=org.gnome.settings-daemon.plugins.media-keys
  BASE=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings
  OURS="$BASE/ralph-whisper/"
  NEWLIST=$(python3 - "$OURS" "$SCHEMA" <<'PY'
import ast, subprocess, sys
ours, schema = sys.argv[1], sys.argv[2]
cur = subprocess.check_output(["gsettings","get",schema,"custom-keybindings"]).decode().strip()
try:
    lst = ast.literal_eval(cur) if cur not in ("@as []","") else []
except Exception:
    lst = []
if ours not in lst: lst.append(ours)
print(str(lst))
PY
)
  gsettings set $SCHEMA custom-keybindings "$NEWLIST"
  CK="$SCHEMA.custom-keybinding:$OURS"
  gsettings set "$CK" name 'ralph-whisper dictation toggle'
  gsettings set "$CK" command "$APP/dictation-toggle"
  gsettings set "$CK" binding "$HOTKEY"
else
  warn "gsettings not found — bind a shortcut to '$APP/dictation-toggle' manually."
fi

echo
say "Done. Tap ${HOTKEY//[<>]/ } to start/stop dictation."
echo "  Manage:  dictation-ctl {status|restart|stop|log}"
[ "$GPU" = 1 ] && echo "  GPU:     dictation-switch-to-gpu   (after NVIDIA driver + reboot)"
