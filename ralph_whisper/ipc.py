"""Cross-platform toggle IPC over a loopback TCP socket.

Unix signals don't exist on Windows, so instead of SIGUSR1 the daemon listens
on 127.0.0.1:<ephemeral-port> and the toggle client connects and sends "toggle".
The port is written to config.PORTFILE.
"""
import socket
import threading

from . import config


def send_toggle():
    with open(config.PORTFILE) as f:
        port = int(f.read().strip())
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s:
        s.sendall(b"toggle\n")


class ToggleServer(threading.Thread):
    def __init__(self, on_toggle):
        super().__init__(daemon=True)
        self.on_toggle = on_toggle
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))          # localhost only
        self.port = self.sock.getsockname()[1]
        self.sock.listen(8)
        with open(config.PORTFILE, "w") as f:
            f.write(str(self.port))

    def run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                break
            with conn:
                try:
                    if b"toggle" in conn.recv(64):
                        self.on_toggle()
                except OSError:
                    pass
