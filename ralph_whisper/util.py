"""Small shared helpers: logging and audio spectrum."""
import os
import time

import numpy as np

from . import config

_band_cache = {}


def log(*a):
    msg = "[%s] %s" % (time.strftime("%H:%M:%S"), " ".join(str(x) for x in a))
    print(msg, flush=True)
    try:
        with open(config.LOG, "a") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def _bands_for(nbins):
    edges = _band_cache.get(nbins)
    if edges is None:
        edges = np.unique(
            np.logspace(0, np.log10(max(2, nbins - 1)), config.NBARS + 1).astype(int)
        )
        _band_cache[nbins] = edges
    return edges


def spectrum(int16):
    """NBARS floats in [0,1] from a chunk of int16 samples (for the bubble)."""
    n = len(int16)
    if n < 16:
        return [0.0] * config.NBARS
    x = int16.astype(np.float32) / 32768.0
    x = x * np.hanning(n)
    mag = np.abs(np.fft.rfft(x))
    edges = _bands_for(len(mag))
    out = []
    for i in range(config.NBARS):
        lo = edges[min(i, len(edges) - 1)]
        hi = edges[min(i + 1, len(edges) - 1)]
        band = mag[lo:hi]
        v = float(band.mean()) if band.size else 0.0
        out.append(min(1.0, (v ** 0.5) * config.BUBBLE_GAIN))
    return out
