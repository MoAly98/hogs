"""Text tables for the terminal, plain or with ANSI colour."""

from hogs.processes import Process
from hogs.system import SystemStats

_BOLD = "1"
_DIM = "2"
_RED = "31"
_BLUE = "34"
_YELLOW = "33"
_GREEN = "32"
# Each metric keeps one colour in every table, like the browser view.
_METRIC_COLORS = {"cpu": _BLUE, "mem": _YELLOW, "energy": _GREEN}
# (title, width, the metric it reports if any) for the columns before COMMAND.
_COLUMNS = [
    ("PID", 7, None),
    ("%CPU", 6, "cpu"),
    ("%MEM", 6, "mem"),
    ("RSS_MB", 8, "mem"),
    ("POWER", 6, "energy"),
    ("ELAPSED", 15, None),
]


def _paint(text: str, color: bool, *codes: str) -> str:
    """Wrap `text` in ANSI style codes, or leave it alone when colour is off."""
    if not color:
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


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


def _fit(text: str, width: int | None) -> str:
    if width is None or len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _header_codes(column_metric: str | None) -> tuple[str, ...]:
    if column_metric is None:
        return (_BOLD,)
    return (_METRIC_COLORS[column_metric], _BOLD)


def _value_codes(column_metric: str | None, ranked_metric: str) -> tuple[str, ...]:
    """Metric columns take their colour, in bold for the one being ranked."""
    if column_metric is None:
        return (_DIM,)
    if column_metric == ranked_metric:
        return (_METRIC_COLORS[column_metric], _BOLD)
    return (_METRIC_COLORS[column_metric],)


def _join(cells: list[str], styles: list[tuple[str, ...]], color: bool) -> str:
    """Right-align and paint one cell per column, ending where COMMAND starts."""
    padded = [f"{cell:>{width}}" for cell, (_, width, _) in zip(cells, _COLUMNS)]
    return " ".join(_paint(cell, color, *codes) for cell, codes in zip(padded, styles)) + "  "


def _format_header(color: bool) -> str:
    titles = [title for title, _, _ in _COLUMNS]
    styles = [_header_codes(metric) for _, _, metric in _COLUMNS]
    return _join(titles, styles, color) + _paint("COMMAND", color, _BOLD)


def _format_row(process: Process, metric: str, width: int | None, color: bool) -> str:
    cells = [
        str(process.pid),
        f"{process.cpu:.1f}",
        f"{process.mem:.1f}",
        str(process.rss_kb // 1024),
        "-" if process.power is None else f"{process.power:.1f}",
        format_elapsed(process.elapsed_seconds),
    ]
    styles = [_value_codes(column_metric, metric) for _, _, column_metric in _COLUMNS]
    # The numbers always stay whole; only the command is cut.
    room = None if width is None else max(width - len(_join(cells, styles, False)), 1)
    return _join(cells, styles, color) + _fit(process.command, room)


def format_ranking(
    title: str, metric: str, processes: list[Process], width: int | None, color: bool
) -> str:
    """A titled table ranked by `metric`, one process per line.

    Commands are cut so lines fit `width` columns if given, and `color` adds
    ANSI styling.
    """
    if metric not in _METRIC_COLORS:
        raise ValueError(f"unknown metric '{metric}'")
    lines = [
        _paint(f"== {title} ==", color, _METRIC_COLORS[metric], _BOLD),
        _format_header(color),
    ]
    lines.extend(_format_row(process, metric, width, color) for process in processes)
    return "\n".join(lines)


def format_system(stats: SystemStats, color: bool) -> str:
    """Two lines summarising load and swap.

    With `color`, load beyond the core count is red and swap use takes the
    memory colour.
    """
    load = " ".join(
        _paint(f"{value:.2f}", color and value > stats.cores, _RED, _BOLD) for value in stats.load
    )
    swap_used = _paint(f"{stats.swap_used_mb:.0f}", color, _METRIC_COLORS["mem"])
    return (
        f"{_paint('load:', color, _BOLD)} {load} on {stats.cores} cores\n"
        f"{_paint('swap:', color, _BOLD)} {swap_used} of {stats.swap_total_mb:.0f} MB used"
    )


def format_footer(text: str, color: bool) -> str:
    """A side note under the tables, dimmed with `color`."""
    return _paint(text, color, _DIM)
