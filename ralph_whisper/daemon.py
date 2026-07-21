"""Portable dictation daemon.

Toggle (via loopback socket, or an in-process hotkey on Win/Mac) starts/stops
recording; on stop the audio is transcribed and typed into the focused window.
The model stays loaded for instant response.
"""
import os
import threading
import time

import numpy as np
from faster_whisper import WhisperModel

from . import config
from .backends.base import get_backend
from .ipc import ToggleServer
from .util import log, spectrum


class Recorder:
    def __init__(self, backend):
        self.backend = backend
        self.cap = None
        self.chunks = []
        self.thread = None
        self.active = False
        self.started_at = 0.0
        self.bubble = None

    def start(self):
        if self.active:
            return
        self.active = True
        self.started_at = time.time()
        self.chunks = []
        self.cap = self.backend.audio_capture()
        self.cap.start()
        self._start_bubble()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        self.backend.notify("🎤 Recording… (toggle again to stop)",
                            config.MAX_SECONDS * 1000)
        log("recording started")

    def _start_bubble(self):
        self.bubble = None
        cmd = self.backend.overlay_command()
        if not cmd:
            return
        try:
            import subprocess
            self.bubble = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log("bubble launch failed:", repr(e))
            self.bubble = None

    def _feed_bubble(self, data):
        if not self.bubble or self.bubble.poll() is not None:
            return
        try:
            samples = np.frombuffer(data, dtype=np.int16)
            line = " ".join("%.3f" % v for v in spectrum(samples)) + "\n"
            self.bubble.stdin.write(line.encode())
            self.bubble.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            pass

    def _read(self):
        while self.active:
            data = self.cap.read()
            if not data:
                if self.active:
                    continue
                break
            self.chunks.append(data)
            self._feed_bubble(data)

    def stop(self):
        if not self.active:
            return None
        self.active = False
        if self.cap:
            self.cap.stop()
        if self.thread:
            self.thread.join(timeout=1)
        self._stop_bubble()
        raw = b"".join(self.chunks)
        log("recording stopped, %d bytes (%.1fs)" % (len(raw), len(raw) / 2 / config.RATE))
        if len(raw) < config.RATE // 2:
            return None
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    def _stop_bubble(self):
        if not self.bubble:
            return
        try:
            if self.bubble.stdin:
                self.bubble.stdin.close()
            self.bubble.terminate()
            try:
                self.bubble.wait(timeout=1)
            except Exception:
                self.bubble.kill()
        except Exception:
            pass
        self.bubble = None


def main():
    os.makedirs(config.APPDIR, exist_ok=True)
    open(config.LOG, "w").close()
    backend = get_backend()
    log("backend:", backend.name)

    log("loading model %s (%s/%s)…" % (config.MODEL, config.DEVICE, config.COMPUTE))
    backend.notify("Whisper: loading model…", 8000)
    model = WhisperModel(config.MODEL, device=config.DEVICE,
                         compute_type=config.COMPUTE, cpu_threads=config.CPU_THREADS)
    model.transcribe(np.zeros(config.RATE, dtype=np.float32),
                     language=config.LANG, beam_size=1)
    log("model ready.")
    backend.notify("✅ Whisper dictation ready", 3000)

    rec = Recorder(backend)
    last_action = [0.0]

    def transcribe_and_type(audio):
        if audio is None:
            backend.notify("(no audio)")
            return
        try:
            backend.notify("✍️ Transcribing…", 8000)
            t = time.time()
            lang = config.LANG
            if lang is None and config.ALLOWED:
                try:
                    _, _, probs = model.detect_language(audio, vad_filter=True)
                    d = dict(probs)
                    lang = max(config.ALLOWED, key=lambda l: d.get(l, 0.0))
                    log("lang=%s (%s)" % (lang, " ".join(
                        "%s=%.2f" % (l, d.get(l, 0.0)) for l in config.ALLOWED)))
                except Exception as e:
                    log("detect_language failed:", repr(e))
                    lang = None
            segments, _ = model.transcribe(audio, language=lang, beam_size=1,
                                           vad_filter=True)
            text = "".join(s.text for s in segments).strip()
            log("transcribed in %.1fs: %r" % (time.time() - t, text))
            if text:
                time.sleep(0.12)
                backend.type_text(text)
                log("typed:", repr(text))
                backend.notify("✅ " + text[:60], 2000)
            else:
                backend.notify("(nothing recognized)")
        except Exception as e:
            import traceback
            log("TRANSCRIBE ERROR:", repr(e))
            log(traceback.format_exc())
            backend.notify("⚠️ error: %s" % e, 4000)

    def do_toggle():
        now = time.time()
        if now - last_action[0] < config.DEBOUNCE:
            return
        last_action[0] = now
        if not rec.active:
            rec.start()
        else:
            audio = rec.stop()
            threading.Thread(target=transcribe_and_type, args=(audio,),
                             daemon=True).start()

    ToggleServer(do_toggle).start()          # loopback socket (all platforms)
    hk = backend.start_hotkey(do_toggle)     # in-process hotkey (Win/Mac); None on Linux
    log("ready. Toggle to dictate." + ("" if hk else " (bind a shortcut to the toggle client)"))

    # idle loop with max-seconds safety auto-stop
    while True:
        time.sleep(1)
        if rec.active and time.time() - rec.started_at > config.MAX_SECONDS:
            log("auto-stop (max seconds)")
            audio = rec.stop()
            threading.Thread(target=transcribe_and_type, args=(audio,),
                             daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
