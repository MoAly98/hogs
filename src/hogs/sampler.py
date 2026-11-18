"""Take a snapshot of the machine by running ps, top and sysctl."""

import os
import subprocess
import time
from dataclasses import asdict, dataclass

from hogs.processes import Process, parse_power, parse_ps, with_power
from hogs.system import SystemStats, parse_swap

PS_COMMAND = ["ps", "-Aww", "-o", "pid=,ppid=,%cpu=,%mem=,rss=,etime=,command="]
# top needs two samples, since the first has no power data.
TOP_COMMAND = ["top", "-l", "2", "-s", "1", "-o", "power", "-stats", "pid,power"]


@dataclass(frozen=True)
class Snapshot:
    """Every process and the system stats at one moment."""

    taken_at: float
    system: SystemStats
    processes: list[Process]

    def to_dict(self) -> dict:
        """Plain data for JSON, with each process's short name added."""
        data = asdict(self)
        for entry, process in zip(data["processes"], self.processes):
            entry["name"] = process.name
        return data


def _run(command: list[str]) -> str:
    environment = {**os.environ, "LC_ALL": "C"}
    return subprocess.run(
        command, capture_output=True, text=True, check=True, env=environment
    ).stdout


def _system_stats() -> SystemStats:
    swap_used, swap_total = parse_swap(_run(["sysctl", "-n", "vm.swapusage"]))
    memory_bytes = int(_run(["sysctl", "-n", "hw.memsize"]))
    return SystemStats(
        load=os.getloadavg(),
        cores=os.cpu_count() or 1,
        memory_mb=memory_bytes // (1024 * 1024),
        swap_used_mb=swap_used,
        swap_total_mb=swap_total,
    )


def take_snapshot(with_power_sample: bool) -> Snapshot:
    """Sample the machine. Power takes about a second, so it is optional."""
    own_pid = os.getpid()
    # Leave out the ps and top helpers this function starts.
    processes = [p for p in parse_ps(_run(PS_COMMAND)) if p.ppid != own_pid]
    if with_power_sample:
        processes = with_power(processes, parse_power(_run(TOP_COMMAND)))
    return Snapshot(taken_at=time.time(), system=_system_stats(), processes=processes)
