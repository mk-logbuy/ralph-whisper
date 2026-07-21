"""Entry points:

  python -m ralph_whisper           # run the daemon
  python -m ralph_whisper toggle    # send a start/stop toggle to a running daemon
"""
import sys


def _run():
    if len(sys.argv) > 1 and sys.argv[1] == "toggle":
        from .ipc import send_toggle
        try:
            send_toggle()
        except Exception as e:
            print("toggle failed (is the daemon running?):", e, file=sys.stderr)
            sys.exit(1)
    else:
        from .daemon import main
        main()


if __name__ == "__main__":
    _run()
