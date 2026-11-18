"""Run the installed hogs command against the real process table."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

HOGS = str(Path(sys.executable).parent / "hogs")


@pytest.fixture
def sleeper():
    """A real child process with a command line we can recognise."""
    process = subprocess.Popen(["sleep", "4242"])
    yield process
    process.kill()
    process.wait()


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def fetch_snapshot(port):
    """Wait for the server to come up, then return its snapshot."""
    deadline = time.monotonic() + 15
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/snapshot", timeout=10) as response:
                return json.load(response)
        except (urllib.error.URLError, ConnectionError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


class TestTerminalRankingOfRealProcesses:
    def test_memory_ranking_lists_a_running_process_with_its_full_command(self, sleeper):
        result = subprocess.run(
            [HOGS, "mem", "-n", "100000"], capture_output=True, text=True, check=True
        )
        rows = [line.split() for line in result.stdout.splitlines()]
        sleeper_rows = [row for row in rows if row and row[0] == str(sleeper.pid)]
        assert len(sleeper_rows) == 1
        assert sleeper_rows[0][-2:] == ["sleep", "4242"]
        assert result.stderr == ""


class TestLiveViewOfRealProcesses:
    def test_snapshot_reports_a_running_process(self, sleeper):
        port = free_port()
        server = subprocess.Popen(
            [HOGS, "web", "--port", str(port), "--no-open"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            snapshot = fetch_snapshot(port)
        finally:
            server.terminate()
            output, errors = server.communicate(timeout=10)

        found = [p for p in snapshot["processes"] if p["pid"] == sleeper.pid]
        assert len(found) == 1
        assert found[0]["command"] == "sleep 4242"
        assert found[0]["name"] == "sleep"
        assert found[0]["ppid"] == os.getpid()
        assert snapshot["system"]["cores"] == os.cpu_count()
        assert output == f"hogs is live at http://127.0.0.1:{port} (Ctrl-C to stop)\n"
        assert errors == ""
