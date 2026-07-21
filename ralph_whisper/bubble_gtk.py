#!/usr/bin/env python3
"""Floating audio-level bubble for whisper dictation.

Runs under the SYSTEM python3 (needs GTK3). Reads spectrum frames from stdin,
one line per frame: space-separated floats in [0,1]. Draws a small dark
rounded, always-on-top, non-focus-stealing bubble with animated bars.
Exits when stdin closes (EOF) — the daemon closes it when recording stops.
"""
import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa: E402
import cairo  # noqa: E402

WIDTH, HEIGHT = 160, 30
RADIUS = HEIGHT // 2   # full radius -> pill / stadium shape
MARGIN_BOTTOM = 90
NBARS = 28

# smoothed bar heights
levels = [0.0] * NBARS


def rounded_rect(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.14159)
    cr.arc(x + r, y + r, r, 3.14159, 4.71239)
    cr.close_path()


class Bubble(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)   # never steal focus from the text field
        self.set_can_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.set_default_size(WIDTH, HEIGHT)
        self.set_size_request(WIDTH, HEIGHT)
        self.resize(WIDTH, HEIGHT)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # bottom-center of the monitor the cursor is on
        display = screen.get_display()
        mon = None
        try:
            _, px, py = display.get_default_seat().get_pointer().get_position()
            mon = display.get_monitor_at_point(px, py)
        except Exception:
            pass
        if mon is None:
            mon = display.get_primary_monitor() or display.get_monitor(0)
        geo = mon.get_geometry()
        x = geo.x + (geo.width - WIDTH) // 2
        y = geo.y + geo.height - HEIGHT - MARGIN_BOTTOM
        self.move(x, y)

        self.area = Gtk.DrawingArea()
        self.area.set_size_request(WIDTH, HEIGHT)
        self.area.set_halign(Gtk.Align.FILL)
        self.area.set_valign(Gtk.Align.FILL)
        self.area.connect("draw", self.on_draw)
        self.add(self.area)

        # ~60 fps redraw; watch stdin for new frames
        GLib.timeout_add(33, self.tick)
        GLib.io_add_watch(sys.stdin.fileno(),
                          GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.on_stdin)
        self.connect("destroy", Gtk.main_quit)

    def on_stdin(self, source, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            Gtk.main_quit()
            return False
        line = sys.stdin.readline()
        if not line:  # EOF
            Gtk.main_quit()
            return False
        try:
            vals = [float(v) for v in line.split()]
            for i in range(min(NBARS, len(vals))):
                # attack fast, decay handled in tick()
                levels[i] = max(levels[i], min(1.0, vals[i]))
        except ValueError:
            pass
        return True

    def tick(self):
        for i in range(NBARS):
            levels[i] *= 0.82  # smooth decay
        self.area.queue_draw()
        return True

    def on_draw(self, widget, cr):
        w, h = WIDTH, HEIGHT   # draw at fixed size regardless of allocation
        # transparent clear
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # dark rounded background
        rounded_rect(cr, 0, 0, w, h, RADIUS)
        cr.set_source_rgba(0.07, 0.07, 0.09, 0.86)
        cr.fill()

        # small red "rec" dot
        cr.arc(13, h / 2, 3.5, 0, 6.2832)
        cr.set_source_rgba(0.95, 0.25, 0.28, 1.0)
        cr.fill()

        # white bars (mirrored around vertical center)
        pad_l, pad_r = 24, 12
        bw = (w - pad_l - pad_r) / NBARS
        gap = bw * 0.4
        cy = h / 2
        max_h = h * 0.62
        for i in range(NBARS):
            lvl = levels[i]
            bh = max(1.5, lvl * max_h)
            x = pad_l + i * bw + gap / 2
            rw = max(1.0, bw - gap)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.92)
            rounded_rect(cr, x, cy - bh / 2, rw, bh, min(rw / 2, 2))
            cr.fill()
        return False


def main():
    b = Bubble()
    b.show_all()
    Gtk.main()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
