import http.client
import json
import threading

import pytest

from hogs.server import make_server


@pytest.fixture
def port(snapshot):
    """Serve a fixed snapshot on a free local port."""
    server = make_server(0, lambda: snapshot)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join()


def get(port, path, host=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("GET", path, headers={"Host": host or f"127.0.0.1:{port}"})
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response, body


class TestSnapshotEndpoint:
    def test_returns_the_snapshot_as_json(self, port):
        response, body = get(port, "/api/snapshot")
        assert response.status == 200
        assert response.getheader("Content-Type") == "application/json"
        assert json.loads(body) == {
            "taken_at": 1795000000.0,
            "system": {
                "load": [3.35, 2.98, 4.7],
                "cores": 16,
                "memory_mb": 65536,
                "swap_used_mb": 3190.69,
                "swap_total_mb": 4096.0,
            },
            "processes": [
                {
                    "pid": 1,
                    "ppid": 0,
                    "cpu": 0.2,
                    "mem": 0.0,
                    "rss_kb": 28768,
                    "elapsed_seconds": 176523,
                    "command": "/sbin/launchd",
                    "power": None,
                    "name": "launchd",
                },
                {
                    "pid": 334,
                    "ppid": 1,
                    "cpu": 12.0,
                    "mem": 4.0,
                    "rss_kb": 3145728,
                    "elapsed_seconds": 3723,
                    "command": "/Applications/Chat.app/Contents/MacOS/Chat --type=renderer",
                    "power": 8.4,
                    "name": "Chat",
                },
                {
                    "pid": 96413,
                    "ppid": 96405,
                    "cpu": 99.5,
                    "mem": 2.5,
                    "rss_kb": 2097152,
                    "elapsed_seconds": 5,
                    "command": "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main",
                    "power": 63.1,
                    "name": "python",
                },
            ],
        }


class TestPage:
    def test_root_serves_the_html_page(self, port):
        response, body = get(port, "/")
        assert response.status == 200
        assert response.getheader("Content-Type") == "text/html; charset=utf-8"
        assert "<title>hogs</title>" in body.decode()


class TestRejections:
    def test_unknown_path_is_not_found(self, port):
        response, _ = get(port, "/etc/passwd")
        assert response.status == 404

    def test_localhost_name_is_accepted(self, port):
        response, _ = get(port, "/api/snapshot", host=f"localhost:{port}")
        assert response.status == 200

    def test_requests_for_another_host_name_are_forbidden(self, port):
        response, _ = get(port, "/api/snapshot", host=f"evil.example:{port}")
        assert response.status == 403
