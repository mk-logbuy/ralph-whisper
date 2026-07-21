#!/usr/bin/env bash
# Flip the dictation daemon to GPU (CUDA). Verifies the NVIDIA driver is present
# and that the model actually loads on CUDA; rolls back to CPU on any failure.
#
# Prereqs: proprietary NVIDIA driver active (nvidia-smi works) and the CUDA
# runtime wheels installed in the venv (install.sh --gpu, or:
#   ~/.local/share/whisper-dictation/venv/bin/pip install \
#       nvidia-cublas-cu12 nvidia-cudnn-cu12)
set -u
APP="$HOME/.local/share/whisper-dictation"
PY="$APP/venv/bin/python"
DROPIN_DIR="$HOME/.config/systemd/user/whisper-dictation.service.d"
GPU_CONF="$DROPIN_DIR/gpu.conf"

if ! command -v nvidia-smi >/dev/null || ! nvidia-smi >/dev/null 2>&1; then
  echo "❌ nvidia-smi not working — proprietary NVIDIA driver not active."
  echo "   Install it and reboot, then re-run this. Staying on CPU."
  exit 1
fi
echo "✅ NVIDIA driver active:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

# locate the cuDNN/cuBLAS lib dirs shipped by the pip wheels (version-agnostic)
LIBS=$("$PY" - <<'PY'
import os
dirs = []
try:
    import nvidia.cudnn, nvidia.cublas
    for m in (nvidia.cudnn, nvidia.cublas):
        dirs.append(os.path.join(os.path.dirname(m.__file__), "lib"))
except Exception:
    pass
print(":".join(dirs))
PY
)
if [ -z "$LIBS" ]; then
  echo "❌ CUDA runtime wheels not found in venv. Run:"
  echo "   $APP/venv/bin/pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"
  exit 1
fi

echo "→ enabling CUDA in the service…"
mkdir -p "$DROPIN_DIR"
cat > "$GPU_CONF" <<EOF
[Service]
Environment=WD_DEVICE=cuda
Environment=WD_COMPUTE=float16
Environment=LD_LIBRARY_PATH=$LIBS
EOF
systemctl --user daemon-reload
: > "$APP/dictate.log"
systemctl --user restart whisper-dictation.service

echo "→ waiting for model load on CUDA…"
for i in $(seq 1 45); do
  sleep 2
  grep -q "model ready" "$APP/dictate.log" 2>/dev/null && break
  grep -qiE "error|cuda|cudnn|cublas|traceback|failed" "$APP/dictate.log" 2>/dev/null && break
done

if grep -q "model ready" "$APP/dictate.log" 2>/dev/null && \
   ! grep -qiE "error|traceback|failed" "$APP/dictate.log" 2>/dev/null; then
  echo "🎉 GPU active. Model loaded on CUDA."
  grep -E "loading model|model ready" "$APP/dictate.log"
else
  echo "⚠️ CUDA load failed — rolling back to CPU. Log tail:"
  tail -15 "$APP/dictate.log"
  rm -f "$GPU_CONF"
  systemctl --user daemon-reload
  systemctl --user restart whisper-dictation.service
  echo "reverted to CPU."
  exit 1
fi
