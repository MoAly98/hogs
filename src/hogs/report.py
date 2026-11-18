"""Plain-text tables for the terminal."""

from hogs.processes import Process
from hogs.system import SystemStats

_ROW = "{:>7} {:>6} {:>6} {:>8} {:>6} {:>15}  {}"
_HEADER = _ROW.format("PID", "%CPU", "%MEM", "RSS_MB", "POWER", "ELAPSED", "COMMAND")


def format_elapsed(seconds: int) -> str:
    """Elapsed time as mm:ss, hh:mm:ss or 'Nd hh:mm:ss'."""
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{secs:02}"
    if hours:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"


def _fit(line: str, width: int | None) -> str:
    if width is None or len(line) <= width:
        return line
    return line[: width - 1] + "…"


def _format_row(process: Process) -> str:
    return _ROW.format(
        process.pid,
        f"{process.cpu:.1f}",
        f"{process.mem:.1f}",
        process.rss_kb // 1024,
        "-" if process.power is None else f"{process.power:.1f}",
        format_elapsed(process.elapsed_seconds),
        process.command,
    )


def format_ranking(title: str, processes: list[Process], width: int | None) -> str:
    """A titled table, one process per line, cut to `width` columns if given."""
    lines = [f"== {title} ==", _HEADER]
    lines.extend(_fit(_format_row(process), width) for process in processes)
    return "\n".join(lines)


def format_system(stats: SystemStats) -> str:
    """Two lines summarising load and swap."""
    one, five, fifteen = stats.load
    return (
        f"load: {one:.2f} {five:.2f} {fifteen:.2f} on {stats.cores} cores\n"
        f"swap: {stats.swap_used_mb:.0f} of {stats.swap_total_mb:.0f} MB used"
    )
