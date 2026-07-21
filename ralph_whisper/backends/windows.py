"""Windows backend.  UNTESTED — written blind; verify on Windows.

- Audio:  sounddevice (PortAudio).
- Typing: pynput keystrokes (works in Windows Terminal) or clipboard+Ctrl+V.
- Notify: best-effort toast via PowerShell; falls back to no-op.
- Hotkey: pynput global hotkey (no special permissions needed on Windows).
- Overlay: tkinter bubble (bundled with python).

Requires: pip install -r requirements-desktop.txt  (sounddevice pynput pyperclip)
"""
import os
import subprocess
import sys

from .base import Backend
from .. import config
from ._sounddevice import SoundDeviceCapture


class WindowsBackend(Backend):
    name = "windows"

    def audio_capture(self):
        return SoundDeviceCapture()

    def type_text(self, text):
        if config.TYPING == "paste":
            import pyperclip
            from pynput.keyboard import Controller, Key
            pyperclip.copy(text)
            kb = Controller()
            with kb.pressed(Key.ctrl):
                kb.tap("v")
        else:
            from pynput.keyboard import Controller
            Controller().type(text)

    def notify(self, text, expire_ms=1500):
        # best-effort; a proper toast lib (win10toast) is optional
        try:
            ps = (
                "powershell -NoProfile -Command "
                "[reflection.assembly]::LoadWithPartialName('System.Windows.Forms')"
                ">$null; "
                "$n=New-Object System.Windows.Forms.NotifyIcon; "
                "$n.Icon=[System.Drawing.SystemIcons]::Information; "
                "$n.Visible=$true; "
                "$n.ShowBalloonTip(%d,'ralph-whisper',%r,'Info')" % (expire_ms, text)
            )
            subprocess.Popen(ps, shell=True)
        except Exception:
            pass

    def start_hotkey(self, on_toggle):
        from pynput import keyboard
        combo = os.environ.get("WD_HOTKEY_PYNPUT", "<ctrl>+<alt>+d")
        hk = keyboard.GlobalHotKeys({combo: on_toggle})
        hk.start()
        return hk

    def overlay_command(self):
        if not config.BUBBLE:
            return None
        bubble = os.path.join(config.APPDIR, "bubble_tk.py")
        if not os.path.exists(bubble):
            return None
        return [sys.executable, bubble]
