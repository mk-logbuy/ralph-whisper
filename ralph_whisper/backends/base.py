"""Platform backend interface.

A backend supplies the OS-specific pieces; the daemon core stays portable.
Audio is always delivered as raw signed-16-bit little-endian, mono, 16 kHz.
"""


class AudioCapture:
    def start(self):
        raise NotImplementedError

    def read(self):
        """Return the next chunk of raw s16le mono 16k bytes, or b'' when done."""
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class Backend:
    name = "base"

    def audio_capture(self) -> AudioCapture:
        raise NotImplementedError

    def type_text(self, text: str):
        raise NotImplementedError

    def notify(self, text: str, expire_ms: int = 1500):
        pass  # best-effort; ok to no-op

    def start_hotkey(self, on_toggle):
        """Optional in-process global hotkey. Return a handle or None.

        Linux/X11 returns None (a desktop shortcut calls the toggle client
        instead, because pynput can't suppress the key on X11). Windows/macOS
        start a pynput hotkey here.
        """
        return None

    def overlay_command(self):
        """argv to spawn the level-bubble overlay (reads spectrum on stdin),
        or None to disable the overlay."""
        return None


def get_backend() -> Backend:
    import sys
    if sys.platform.startswith("linux"):
        from .linux import LinuxBackend
        return LinuxBackend()
    if sys.platform == "darwin":
        from .macos import MacBackend
        return MacBackend()
    if sys.platform.startswith("win"):
        from .windows import WindowsBackend
        return WindowsBackend()
    raise RuntimeError("unsupported platform: %s" % sys.platform)
