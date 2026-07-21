"""Linux backend (X11 / GNOME). Tested on Pop!_OS 22.04.

- Audio:  pw-record (PipeWire). Note: parec returns 0 bytes on some PipeWire
          setups, so pw-record is used deliberately.
- Typing: xdotool (real keystrokes -> works in terminals too).
- Notify: notify-send.
- Hotkey: none in-process; a GNOME custom shortcut runs `dictation-toggle`.
- Overlay: GTK3 bubble via the system python3 (the venv lacks PyGObject).
"""
import os
import subprocess

from .base import AudioCapture, Backend
from .. import config


class PwRecordCapture(AudioCapture):
    def __init__(self):
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            ["pw-record", "--rate=%d" % config.RATE, "--channels=1",
             "--format=s16", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def read(self):
        if not self.proc or not self.proc.stdout:
            return b""
        return self.proc.stdout.read(config.CHUNK)

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


class LinuxBackend(Backend):
    name = "linux"

    def audio_capture(self):
        return PwRecordCapture()

    def type_text(self, text):
        if config.TYPING == "paste":
            _paste_linux(text)
        else:
            subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text],
                           check=False)

    def notify(self, text, expire_ms=1500):
        try:
            subprocess.run(
                ["notify-send", "-t", str(expire_ms),
                 "-h", "string:x-canonical-private-synchronous:whisper-dictation",
                 text], check=False)
        except FileNotFoundError:
            pass

    def overlay_command(self):
        if not config.BUBBLE:
            return None
        bubble = os.path.join(config.APPDIR, "bubble_gtk.py")
        if not os.path.exists(bubble):
            return None
        return ["/usr/bin/python3", bubble]  # system python (has PyGObject/GTK)


def _paste_linux(text):
    import subprocess as sp
    sp.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=False)
    # Ctrl+Shift+V for terminals is not universal; plain Ctrl+V for GUI apps.
    sp.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=False)
