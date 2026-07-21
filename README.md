# ralph-whisper

Push-to-talk voice dictation using [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Toggle a hotkey, speak, toggle again — the transcription is typed into whatever
window is focused (terminal, editor, browser, chat…). The model stays loaded in
a background daemon for near-instant response, and a small level bubble shows
while recording.

Built originally for dictating prompts into terminal apps, so it types **real
keystrokes** (works inside terminals, not just GUI text fields).

## Platform status

| Platform | Status | Audio | Typing | Hotkey | Autostart |
|----------|--------|-------|--------|--------|-----------|
| **Linux** (X11/GNOME) | ✅ tested | `pw-record` | `xdotool` | GNOME shortcut → toggle | systemd user service |
| **macOS** | ⚠️ experimental, untested | `sounddevice` | `pynput` | `pynput` global hotkey | launchd (manual) |
| **Windows** | ⚠️ experimental, untested | `sounddevice` | `pynput` | `pynput` global hotkey | Startup shortcut (manual) |

The core (model, record→transcribe→type loop, toggle IPC) is OS-agnostic; each
OS plugs in a small backend under `ralph_whisper/backends/`.

## Install

### Linux (X11 / GNOME) — tested

```bash
sudo apt install pipewire-bin xdotool libnotify-bin python3-venv \
    python3-gi gir1.2-gtk-3.0 python3-gi-cairo xclip
git clone https://github.com/mk-logbuy/ralph-whisper && cd ralph-whisper
./installers/linux/install.sh          # or: ./installers/linux/install.sh --gpu
```

Binds **Super+V** by default (override with `WD_HOTKEY='<Super>d'`). Tap it to
start/stop. Manage the daemon with `dictation-ctl {status|restart|stop|log}`.

> Wayland note: typing relies on `xdotool` (X11). On a Wayland session it won't
> type into apps; use an X11 session, or swap in a `wtype`/`ydotool` backend.

### macOS / Windows — experimental

```bash
git clone https://github.com/mk-logbuy/ralph-whisper && cd ralph-whisper
python -m venv .venv && . .venv/bin/activate      # (Windows: .venv\Scripts\activate)
pip install -e ".[desktop]"                        # add ",gpu" on NVIDIA
python -m ralph_whisper                            # runs the daemon
```

Default hotkey: **⌘+Shift+D** (mac) / **Ctrl+Alt+D** (win), override with
`WD_HOTKEY_PYNPUT`. On macOS grant the terminal/Python **Accessibility** and
**Input Monitoring** permissions (System Settings → Privacy & Security).
Autostart: add a launchd plist (mac) or a Startup shortcut (win) that runs
`python -m ralph_whisper` — helpers under `installers/` are stubs to adapt.

## Configuration (environment variables)

| Var | Default | Meaning |
|-----|---------|---------|
| `WD_MODEL` | `large-v3` | whisper model (`small.en`, `medium.en`, `large-v3`, …) |
| `WD_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WD_COMPUTE` | `int8` | `int8` (cpu) / `float16` (cuda) |
| `WD_LANG` | `auto` | force a language (`en`, `da`) or auto-detect |
| `WD_LANGS` | `en,da` | when auto: only choose among these (avoids mis-detects) |
| `WD_TYPING` | `keystroke` | `keystroke` (terminals ok) or `paste` (clipboard+Ctrl/⌘V) |
| `WD_BUBBLE` | `1` | show the level bubble (`0` to disable) |
| `WD_BUBBLE_GAIN` | `1.4` | bubble bar sensitivity |
| `WD_THREADS` | `8` | CPU inference threads |

On Linux these are set via systemd drop-ins in
`~/.config/systemd/user/whisper-dictation.service.d/`.

## GPU (NVIDIA, Linux)

1. Install the proprietary driver (e.g. Pop!_OS: `sudo apt install system76-driver-nvidia`) and reboot.
2. `./installers/linux/install.sh --gpu` (or `venv/bin/pip install -r requirements-gpu.txt`).
3. `dictation-switch-to-gpu` — verifies CUDA, flips to `cuda/float16`, and
   **auto-reverts to CPU** if the model fails to load.

`large-v3` on a modern GPU transcribes a sentence in well under a second.

## How it works

- **Daemon** (`ralph_whisper/daemon.py`): loads the model once, records on
  toggle, transcribes, types the result. Language auto-detect is restricted to
  `WD_LANGS` via `detect_language` to avoid short-clip mis-detection.
- **Toggle IPC** (`ipc.py`): a loopback TCP socket (cross-platform; no Unix
  signals). The `dictation-toggle` client sends "toggle".
- **Bubble**: the daemon computes an FFT spectrum from the mic and streams it to
  a small overlay process (GTK on Linux, tkinter on Win/Mac).

## Uninstall (Linux)

```bash
./installers/linux/uninstall.sh
```

## License

MIT
