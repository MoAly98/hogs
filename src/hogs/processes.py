"""The process record, and how to read and rank it."""

import re
from dataclasses import dataclass, replace

# Ranking metric name -> the Process field it sorts by.
METRICS = {"cpu": "cpu", "mem": "rss_kb", "energy": "power"}

_APP_BUNDLE = re.compile(r"/([^/]+)\.app/")


@dataclass(frozen=True)
class Process:
    """One running process at the moment it was sampled."""

    pid: int
    ppid: int
    cpu: float
    mem: float
    rss_kb: int
    elapsed_seconds: int
    command: str
    power: float | None = None

    @property
    def name(self) -> str:
        return app_name(self.command)


def app_name(command: str) -> str:
    """Short name for a command: its app bundle if it has one, else its executable."""
    bundle = _APP_BUNDLE.search(command)
    if bundle:
        return bundle.group(1)
    # Login shells show up with a leading dash, as in "-zsh".
    return command.split()[0].rsplit("/", 1)[-1].lstrip("-")


def parse_elapsed(etime: str) -> int:
    """Convert ps elapsed time, [[dd-]hh:]mm:ss, to seconds."""
    days, _, clock = etime.rpartition("-")
    seconds = 0
    for part in clock.split(":"):
        seconds = seconds * 60 + int(part)
    return int(days or 0) * 86400 + seconds


def parse_ps(output: str) -> list[Process]:
    """Read the rows of `ps -o pid=,ppid=,%cpu=,%mem=,rss=,etime=,command=`."""
    processes = []
    for line in output.splitlines():
        if not line.strip():
            continue
        pid, ppid, cpu, mem, rss, etime, command = line.split(None, 6)
        processes.append(
            Process(
                pid=int(pid),
                ppid=int(ppid),
                cpu=float(cpu),
                mem=float(mem),
                rss_kb=int(rss),
                elapsed_seconds=parse_elapsed(etime),
                command=command.rstrip(),
            )
        )
    return processes


def parse_power(output: str) -> dict[int, float]:
    """Read pid -> power from the last sample of `top -stats pid,power`."""
    power: dict[int, float] = {}
    in_sample = False
    for line in output.splitlines():
        fields = line.split()
        if fields[:1] == ["PID"]:
            power = {}
            in_sample = True
        elif in_sample and len(fields) == 2 and fields[0].isdigit():
            power[int(fields[0])] = float(fields[1])
        else:
            in_sample = False
    return power


def with_power(processes: list[Process], power: dict[int, float]) -> list[Process]:
    """Attach sampled power to each process; ones top did not list get zero."""
    return [replace(process, power=power.get(process.pid, 0.0)) for process in processes]


def rank(processes: list[Process], metric: str, count: int) -> list[Process]:
    """The `count` processes that use the most of `metric`, heaviest first."""
    if metric not in METRICS:
        raise ValueError(f"unknown metric '{metric}'")
    field = METRICS[metric]
    return sorted(processes, key=lambda p: getattr(p, field) or 0.0, reverse=True)[:count]
