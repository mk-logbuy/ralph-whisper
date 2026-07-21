#!/usr/bin/env python3
"""Cross-platform level bubble (tkinter) for macOS/Windows.

Reads spectrum frames from stdin (one line: space-separated floats in [0,1]),
draws a small dark pill with white bars, always-on-top, bottom-center of the
screen. Exits on stdin EOF. tkinter ships with standard python.

NOTE: transparency/rounded corners vary by platform; this uses a dark rounded
rectangle drawn on a canvas with a transparent color-key where supported.
UNTESTED on Win/Mac — tweak WIDTH/HEIGHT if it looks off.
"""
import sys
import threading
import tkinter as tk

WIDTH, HEIGHT = 200, 34
NBARS = 28
BG = "#111114"
BAR = "#ffffff"

levels = [0.0] * NBARS


def main():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.92)
    except tk.TclError:
        pass
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - WIDTH) // 2
    y = sh - HEIGHT - 90
    root.geometry("%dx%d+%d+%d" % (WIDTH, HEIGHT, x, y))

    cv = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, bg=BG)
    cv.pack()

    def draw():
        cv.delete("all")
        cv.create_oval(8, HEIGHT / 2 - 4, 16, HEIGHT / 2 + 4, fill="#f04448", width=0)
        pad_l, pad_r = 24, 12
        bw = (WIDTH - pad_l - pad_r) / NBARS
        gap = bw * 0.4
        cy = HEIGHT / 2
        max_h = HEIGHT * 0.6
        for i in range(NBARS):
            lvl = levels[i]
            bh = max(1.5, lvl * max_h)
            bx = pad_l + i * bw + gap / 2
            cv.create_rectangle(bx, cy - bh / 2, bx + (bw - gap), cy + bh / 2,
                                fill=BAR, width=0)

    def tick():
        for i in range(NBARS):
            levels[i] *= 0.82
        draw()
        root.after(33, tick)

    def reader():
        for line in sys.stdin:
            try:
                vals = [float(v) for v in line.split()]
                for i in range(min(NBARS, len(vals))):
                    levels[i] = max(levels[i], min(1.0, vals[i]))
            except ValueError:
                pass
        root.after(0, root.destroy)  # EOF -> close

    threading.Thread(target=reader, daemon=True).start()
    tick()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
