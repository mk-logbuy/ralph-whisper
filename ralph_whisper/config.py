"""Central configuration, all overridable via environment variables."""
import os

APPDIR = os.path.expanduser(os.environ.get("WD_HOME", "~/.local/share/whisper-dictation"))

MODEL = os.environ.get("WD_MODEL", "large-v3")          # e.g. small.en, medium.en, large-v3
DEVICE = os.environ.get("WD_DEVICE", "cpu")             # cpu | cuda
COMPUTE = os.environ.get("WD_COMPUTE", "int8")          # int8 (cpu) | float16 (cuda)
CPU_THREADS = int(os.environ.get("WD_THREADS", "8"))

_lang = os.environ.get("WD_LANG", "auto")
LANG = None if _lang in ("auto", "", "detect") else _lang
# When auto-detecting, only choose among these (avoids short-clip mis-detects).
ALLOWED = [x.strip() for x in os.environ.get("WD_LANGS", "en,da").split(",") if x.strip()]

RATE = 16000
CHUNK = 1024          # bytes per audio read (512 s16 samples ≈ 32ms)
NBARS = 28
MAX_SECONDS = 120     # safety auto-stop
DEBOUNCE = 0.6        # ignore toggles closer than this (key autorepeat)

BUBBLE = os.environ.get("WD_BUBBLE", "1") == "1"
BUBBLE_GAIN = float(os.environ.get("WD_BUBBLE_GAIN", "1.4"))

# typing method: "keystroke" (works in terminals) or "paste" (clipboard + Ctrl/Cmd+V)
TYPING = os.environ.get("WD_TYPING", "keystroke")

LOG = os.path.join(APPDIR, "dictate.log")
PORTFILE = os.path.join(APPDIR, "port")   # loopback port for the toggle client
