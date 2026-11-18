from dataclasses import replace

import pytest

from hogs.report import format_elapsed, format_footer, format_ranking, format_system

HEADER = "    PID   %CPU   %MEM   RSS_MB  POWER         ELAPSED  COMMAND"
COLOR_HEADER = (
    "\033[1m    PID\033[0m \033[34;1m  %CPU\033[0m \033[33;1m  %MEM\033[0m "
    "\033[33;1m  RSS_MB\033[0m \033[32;1m POWER\033[0m \033[1m        ELAPSED\033[0m  "
    "\033[1mCOMMAND\033[0m"
)


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
        assert format_ranking("top CPU", "cpu", [worker, chat_app], width=None, color=False) == "\n".join(
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
        row = format_ranking("top CPU", "cpu", [launchd], width=None, color=False).splitlines()[2]
        assert row == "      1    0.2    0.0       28      -     2d 01:02:03  /sbin/launchd"

    def test_long_rows_are_cut_to_the_width_with_an_ellipsis(self, worker):
        row = format_ranking("top CPU", "cpu", [worker], width=63, color=False).splitlines()[2]
        assert row == "  96413   99.5    2.5     2048   63.1           00:05  /opt/en…"

    def test_rows_that_fit_the_width_are_left_alone(self, launchd):
        row = format_ranking("top CPU", "cpu", [launchd], width=68, color=False).splitlines()[2]
        assert row == "      1    0.2    0.0       28      -     2d 01:02:03  /sbin/launchd"

    def test_no_processes_still_prints_title_and_header(self):
        assert format_ranking("top CPU", "cpu", [], width=None, color=False) == f"== top CPU ==\n{HEADER}"

    def test_a_width_narrower_than_the_numbers_keeps_them_and_cuts_the_whole_command(self, launchd):
        row = format_ranking("top CPU", "cpu", [launchd], width=20, color=False).splitlines()[2]
        assert row == "      1    0.2    0.0       28      -     2d 01:02:03  …"


class TestFormatRankingInColor:
    def test_cpu_ranking_is_titled_in_blue_with_its_own_column_in_bold(self, worker):
        assert format_ranking("top CPU", "cpu", [worker], width=None, color=True) == "\n".join(
            [
                "\033[34;1m== top CPU ==\033[0m",
                COLOR_HEADER,
                "\033[2m  96413\033[0m \033[34;1m  99.5\033[0m \033[33m   2.5\033[0m "
                "\033[33m    2048\033[0m \033[32m  63.1\033[0m \033[2m          00:05\033[0m  "
                "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main",
            ]
        )

    def test_memory_ranking_is_titled_in_yellow_with_both_memory_columns_in_bold(self, chat_app):
        assert format_ranking("top memory", "mem", [chat_app], width=None, color=True) == "\n".join(
            [
                "\033[33;1m== top memory ==\033[0m",
                COLOR_HEADER,
                "\033[2m    334\033[0m \033[34m  12.0\033[0m \033[33;1m   4.0\033[0m "
                "\033[33;1m    3072\033[0m \033[32m   8.4\033[0m \033[2m       01:02:03\033[0m  "
                "/Applications/Chat.app/Contents/MacOS/Chat --type=renderer",
            ]
        )

    def test_energy_ranking_is_titled_in_green_with_the_power_column_in_bold(self, chat_app):
        title, _, row = format_ranking("top energy", "energy", [chat_app], width=None, color=True).splitlines()
        assert title == "\033[32;1m== top energy ==\033[0m"
        assert row == (
            "\033[2m    334\033[0m \033[34m  12.0\033[0m \033[33m   4.0\033[0m "
            "\033[33m    3072\033[0m \033[32;1m   8.4\033[0m \033[2m       01:02:03\033[0m  "
            "/Applications/Chat.app/Contents/MacOS/Chat --type=renderer"
        )

    def test_color_codes_do_not_count_towards_the_width(self, worker):
        row = format_ranking("top CPU", "cpu", [worker], width=63, color=True).splitlines()[2]
        assert row == (
            "\033[2m  96413\033[0m \033[34;1m  99.5\033[0m \033[33m   2.5\033[0m "
            "\033[33m    2048\033[0m \033[32m  63.1\033[0m \033[2m          00:05\033[0m  "
            "/opt/en…"
        )

    def test_unknown_metric_is_rejected(self, worker):
        with pytest.raises(ValueError, match="unknown metric 'disk'"):
            format_ranking("top disk", "disk", [worker], width=None, color=True)


class TestFormatSystem:
    def test_summarises_load_and_swap(self, stats):
        assert format_system(stats, color=False) == (
            "load: 3.35 2.98 4.70 on 16 cores\nswap: 3191 of 4096 MB used"
        )

    def test_color_marks_the_labels_in_bold_and_swap_in_the_memory_yellow(self, stats):
        assert format_system(stats, color=True) == (
            "\033[1mload:\033[0m 3.35 2.98 4.70 on 16 cores\n"
            "\033[1mswap:\033[0m \033[33m3191\033[0m of 4096 MB used"
        )

    def test_color_marks_load_beyond_the_core_count_in_red(self, stats):
        busy = replace(stats, load=(17.5, 16.0, 16.01))
        assert format_system(busy, color=True).splitlines()[0] == (
            "\033[1mload:\033[0m \033[31;1m17.50\033[0m 16.00 \033[31;1m16.01\033[0m on 16 cores"
        )


class TestFormatFooter:
    def test_plain_footer_is_the_text_itself(self):
        assert format_footer("live, every 2s", color=False) == "live, every 2s"

    def test_color_dims_the_footer(self):
        assert format_footer("live, every 2s", color=True) == "\033[2mlive, every 2s\033[0m"
