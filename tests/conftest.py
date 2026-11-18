import pytest

from hogs.processes import Process
from hogs.sampler import Snapshot
from hogs.system import SystemStats


@pytest.fixture
def worker():
    return Process(
        pid=96413,
        ppid=96405,
        cpu=99.5,
        mem=2.5,
        rss_kb=2097152,
        elapsed_seconds=5,
        command="/opt/env/bin/python -c from multiprocessing.spawn import spawn_main",
        power=63.1,
    )


@pytest.fixture
def chat_app():
    return Process(
        pid=334,
        ppid=1,
        cpu=12.0,
        mem=4.0,
        rss_kb=3145728,
        elapsed_seconds=3723,
        command="/Applications/Chat.app/Contents/MacOS/Chat --type=renderer",
        power=8.4,
    )


@pytest.fixture
def launchd():
    return Process(
        pid=1,
        ppid=0,
        cpu=0.2,
        mem=0.0,
        rss_kb=28768,
        elapsed_seconds=176523,
        command="/sbin/launchd",
    )


@pytest.fixture
def stats():
    return SystemStats(
        load=(3.35, 2.98, 4.7),
        cores=16,
        memory_mb=65536,
        swap_used_mb=3190.69,
        swap_total_mb=4096.0,
    )


@pytest.fixture
def snapshot(stats, worker, chat_app, launchd):
    return Snapshot(taken_at=1795000000.0, system=stats, processes=[launchd, chat_app, worker])
