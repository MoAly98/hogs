import pytest

from hogs.report import format_elapsed, format_ranking, format_system

HEADER = "    PID   %CPU   %MEM   RSS_MB  POWER         ELAPSED  COMMAND"


class TestFormatElapsed:
    @pytest.mark.parametrize(
        "seconds, text",
        [
            (5, "00:05"),
            (754, "12:34"),
            (3723, "01:02:03"),
            (176523, "2d 01:02:03"),
        ],
    )
    def test_shows_only_the_units_that_are_needed(self, seconds, text):
        assert format_elapsed(seconds) == text


class TestFormatRanking:
    def test_lists_a_title_a_header_and_one_aligned_row_per_process(self, worker, chat_app):
        assert format_ranking("top CPU", [worker, chat_app], width=None) == "\n".join(
            [
                "== top CPU ==",
                HEADER,
                "  96413   99.5    2.5     2048   63.1           00:05  "
                "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main",
                "    334   12.0    4.0     3072    8.4        01:02:03  "
                "/Applications/Chat.app/Contents/MacOS/Chat --type=renderer",
            ]
        )

    def test_unsampled_power_shows_a_dash(self, launchd):
        row = format_ranking("top CPU", [launchd], width=None).splitlines()[2]
        assert row == "      1    0.2    0.0       28      -     2d 01:02:03  /sbin/launchd"

    def test_long_rows_are_cut_to_the_width_with_an_ellipsis(self, worker):
        row = format_ranking("top CPU", [worker], width=63).splitlines()[2]
        assert row == "  96413   99.5    2.5     2048   63.1           00:05  /opt/en…"

    def test_rows_that_fit_the_width_are_left_alone(self, launchd):
        row = format_ranking("top CPU", [launchd], width=68).splitlines()[2]
        assert row == "      1    0.2    0.0       28      -     2d 01:02:03  /sbin/launchd"

    def test_no_processes_still_prints_title_and_header(self):
        assert format_ranking("top CPU", [], width=None) == f"== top CPU ==\n{HEADER}"


class TestFormatSystem:
    def test_summarises_load_and_swap(self, stats):
        assert format_system(stats) == (
            "load: 3.35 2.98 4.70 on 16 cores\nswap: 3191 of 4096 MB used"
        )
