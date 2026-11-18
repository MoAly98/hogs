"""The `hogs` command."""

import argparse
import os
import shutil
import signal
import sys
import time
import webbrowser

from hogs.processes import rank
from hogs.report import format_footer, format_ranking, format_system
from hogs.sampler import take_snapshot
from hogs.server import HOST, make_server

# Terminal mode -> the (title, metric) rankings it prints.
RANKINGS = {
    "cpu": [("top CPU", "cpu")],
    "mem": [("top memory", "mem")],
    "energy": [("top energy", "energy")],
    "all": [("top CPU", "cpu"), ("top memory", "mem"), ("top energy", "energy")],
}
DEFAULT_PORT = 8765

# Live mode draws on the alternate screen with the cursor hidden, so the
# terminal's scrollback comes back untouched afterwards.
_ENTER_LIVE_SCREEN = "\033[?1049h\033[?25l"
_LEAVE_LIVE_SCREEN = "\033[?25h\033[?1049l"
_CURSOR_HOME = "\033[H"
_CLEAR_LINE = "\033[K"
_CLEAR_BELOW = "\033[J"


def _positive(text: str) -> int:
    if not text.isdigit() or int(text) == 0:
        raise argparse.ArgumentTypeError(f"must be a positive number, got '{text}'")
    return int(text)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hogs",
        description="Rank the processes using the most CPU, memory or energy.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=[*RANKINGS, "web"],
        help="which ranking to print, or 'web' for the live browser view (default: all)",
    )
    parser.add_argument("-n", "--count", type=_positive, default=10, help="rows per ranking (default: 10)")
    parser.add_argument("--full", action="store_true", help="print whole commands instead of cutting them to the terminal width")
    parser.add_argument("--live", action="store_true", help="keep redrawing the rankings in the terminal until Ctrl-C")
    parser.add_argument("--interval", type=_positive, default=2, help="seconds between redraws with --live (default: 2)")
    parser.add_argument("--port", type=_positive, default=DEFAULT_PORT, help=f"port for the browser view (default: {DEFAULT_PORT})")
    parser.add_argument("--no-open", action="store_true", help="start the browser view without opening a browser")
    return parser


def _format_report(mode: str, count: int, width: int | None, color: bool) -> str:
    """Sample the machine and lay out the rankings of `mode` and the system summary."""
    rankings = RANKINGS[mode]
    snapshot = take_snapshot(any(metric == "energy" for _, metric in rankings))
    parts = [
        format_ranking(title, metric, rank(snapshot.processes, metric, count), width, color) + "\n"
        for title, metric in rankings
    ]
    parts.append(format_system(snapshot.system, color))
    return "\n".join(parts)


def _wants_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _print_rankings(mode: str, count: int, full: bool) -> None:
    # Cut commands and add colour only for a person at a terminal, so pipes
    # still get everything as plain text.
    width = shutil.get_terminal_size().columns if sys.stdout.isatty() and not full else None
    print(_format_report(mode, count, width, _wants_color()))


def _rows_that_fit(mode: str, terminal_lines: int) -> int:
    """Rows per ranking that keep a live frame on one screen, at least one."""
    rankings = len(RANKINGS[mode])
    # Below the rankings: load, swap, a blank line and the footer.
    # Around each ranking's rows: its title, its header and a blank line.
    return max((terminal_lines - 4) // rankings - 3, 1)


def _watch_rankings(mode: str, count: int, interval: int) -> None:
    """Redraw the rankings in place every `interval` seconds until Ctrl-C."""
    color = _wants_color()
    footer = format_footer(f"live, every {interval}s (Ctrl-C to stop)", color)
    signal.signal(signal.SIGTERM, _stop_on_terminate)
    sys.stdout.write(_ENTER_LIVE_SCREEN)
    try:
        while True:
            size = shutil.get_terminal_size()
            rows = min(count, _rows_that_fit(mode, size.lines))
            frame = f"{_format_report(mode, rows, size.columns, color)}\n\n{footer}"
            # Overwrite the old frame line by line rather than clearing the
            # screen first, which would flicker.
            sys.stdout.write(
                _CURSOR_HOME + frame.replace("\n", _CLEAR_LINE + "\n") + _CLEAR_LINE + _CLEAR_BELOW
            )
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(_LEAVE_LIVE_SCREEN)
        sys.stdout.flush()


def _stop_on_terminate(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def _serve(port: int, open_browser: bool) -> None:
    server = make_server(port, lambda: take_snapshot(True))
    url = f"http://{HOST}:{port}"
    print(f"hogs is live at {url} (Ctrl-C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    signal.signal(signal.SIGTERM, _stop_on_terminate)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.live:
        if args.mode == "web":
            parser.error("--live is for the terminal rankings, not 'web'")
        if args.full:
            parser.error("--live cannot show whole commands, drop --full")
        if not sys.stdout.isatty():
            parser.error("--live needs a terminal")
        _watch_rankings(args.mode, args.count, args.interval)
    elif args.mode == "web":
        _serve(args.port, not args.no_open)
    else:
        _print_rankings(args.mode, args.count, args.full)
    return 0
