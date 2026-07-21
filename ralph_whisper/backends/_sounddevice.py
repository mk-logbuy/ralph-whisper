"""Shared PortAudio capture for the macOS/Windows backends.

Delivers raw s16le mono 16k in the same shape as the Linux pw-record path.
Requires: pip install sounddevice
"""
import queue

from .base import AudioCapture
from .. import config


class SoundDeviceCapture(AudioCapture):
    def __init__(self):
        self._q = queue.Queue()
        self._stream = None

    def start(self):
        import sounddevice as sd
        self._q = queue.Queue()
        self._stream = sd.RawInputStream(
            samplerate=config.RATE, channels=1, dtype="int16",
            blocksize=config.CHUNK // 2,          # frames (2 bytes each)
            callback=self._cb,
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):
        self._q.put(bytes(indata))

    def read(self):
        try:
            return self._q.get(timeout=0.5)
        except queue.Empty:
            return b""

    def stop(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
