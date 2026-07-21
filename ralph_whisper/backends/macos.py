"""macOS backend.  UNTESTED — written blind; verify on a Mac.

- Audio:  sounddevice (PortAudio).
- Typing: pynput keystrokes (works in Terminal.app) or clipboard+Cmd+V.
- Notify: osascript.
- Hotkey: pynput global hotkey (needs Accessibility + Input Monitoring perms
          granted to the app running Python, in System Settings > Privacy).
- Overlay: tkinter bubble (bundled with python).

Requires: pip install -r requirements-desktop.txt  (sounddevice pynput pyperclip)
"""
import os
import subprocess
import sys

from .base import Backend
from .. import config
from ._sounddevice import SoundDeviceCapture


class MacBackend(Backend):
    name = "macos"

    def audio_capture(self):
        return SoundDeviceCapture()

    def type_text(self, text):
        if config.TYPING == "paste":
            import pyperclip
            from pynput.keyboard import Controller, Key
            pyperclip.copy(text)
            kb = Controller()
            with kb.pressed(Key.cmd):
                kb.tap("v")
        else:
            from pynput.keyboard import Controller
            Controller().type(text)

    def notify(self, text, expire_ms=1500):
        try:
            safe = text.replace('"', "'")
            subprocess.run(
                ["osascript", "-e",
                 'display notification "%s" with title "ralph-whisper"' % safe],
                check=False)
        except FileNotFoundError:
            pass

    def start_hotkey(self, on_toggle):
        from pynput import keyboard
        combo = os.environ.get("WD_HOTKEY_PYNPUT", "<cmd>+<shift>+d")
        hk = keyboard.GlobalHotKeys({combo: on_toggle})
        hk.start()
        return hk

    def overlay_command(self):
        if not config.BUBBLE:
            return None
        bubble = os.path.join(config.APPDIR, "bubble_tk.py")
        if not os.path.exists(bubble):
            return None
        return [sys.executable, bubble]   # venv python has tkinter
