"""The `hogs` command."""

import argparse
import os
import shutil
import signal
import sys
import webbrowser

from hogs.processes import rank
from hogs.report import format_ranking, format_system
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
    parser.add_argument("--port", type=_positive, default=DEFAULT_PORT, help=f"port for the browser view (default: {DEFAULT_PORT})")
    parser.add_argument("--no-open", action="store_true", help="start the browser view without opening a browser")
    return parser


def _print_rankings(mode: str, count: int, full: bool) -> None:
    rankings = RANKINGS[mode]
    snapshot = take_snapshot(any(metric == "energy" for _, metric in rankings))
    # Cut commands and add colour only for a person at a terminal, so pipes
    # still get everything as plain text.
    on_terminal = sys.stdout.isatty()
    width = shutil.get_terminal_size().columns if on_terminal and not full else None
    color = on_terminal and not os.environ.get("NO_COLOR")
    for title, metric in rankings:
        print(format_ranking(title, metric, rank(snapshot.processes, metric, count), width, color))
        print()
    print(format_system(snapshot.system, color))


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
    args = _parser().parse_args(argv)
    if args.mode == "web":
        _serve(args.port, not args.no_open)
    else:
        _print_rankings(args.mode, args.count, args.full)
    return 0
