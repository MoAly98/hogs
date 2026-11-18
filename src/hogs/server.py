"""Local web server behind the live browser view."""

import json
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from hogs.sampler import Snapshot

HOST = "127.0.0.1"


class HogsServer(ThreadingHTTPServer):
    """An HTTP server that knows where to get snapshots from."""

    def __init__(self, port: int, snapshot_source: Callable[[], Snapshot]):
        super().__init__((HOST, port), HogsHandler)
        self.snapshot_source = snapshot_source


class HogsHandler(BaseHTTPRequestHandler):
    """Serves the page and the snapshot it polls."""

    server: HogsServer

    def do_GET(self) -> None:
        if not self._host_is_local():
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path == "/":
            page = resources.files("hogs").joinpath("index.html").read_bytes()
            self._send(page, "text/html; charset=utf-8")
        elif self.path == "/api/snapshot":
            snapshot = self.server.snapshot_source()
            self._send(json.dumps(snapshot.to_dict()).encode(), "application/json")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _host_is_local(self) -> bool:
        """Command lines can hold secrets, so only answer requests made to this machine by name."""
        port = self.server.server_address[1]
        return self.headers.get("Host") in {f"{HOST}:{port}", f"localhost:{port}"}

    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Stay quiet; the page polls every couple of seconds."""


def make_server(port: int, snapshot_source: Callable[[], Snapshot]) -> HogsServer:
    """A server on this machine only. Port 0 picks a free port."""
    return HogsServer(port, snapshot_source)
