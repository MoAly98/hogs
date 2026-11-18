import sys

import pytest

from hogs import cli

HEADER = "    PID   %CPU   %MEM   RSS_MB  POWER         ELAPSED  COMMAND"
WORKER_ROW = (
    "  96413   99.5    2.5     2048   63.1           00:05  "
    "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main"
)
CHAT_ROW = (
    "    334   12.0    4.0     3072    8.4        01:02:03  "
    "/Applications/Chat.app/Contents/MacOS/Chat --type=renderer"
)
SYSTEM_LINES = "load: 3.35 2.98 4.70 on 16 cores\nswap: 3191 of 4096 MB used\n"


@pytest.fixture
def sampled(monkeypatch, snapshot):
    """Replace the real sampler and record whether power was requested."""
    calls = []

    def fake_take_snapshot(with_power):
        calls.append(with_power)
        return snapshot

    monkeypatch.setattr(cli, "take_snapshot", fake_take_snapshot)
    return calls


class TestRankingModes:
    def test_cpu_mode_prints_the_cpu_ranking_and_system_summary(self, sampled, capsys):
        assert cli.main(["cpu", "-n", "1"]) == 0
        assert capsys.readouterr().out == (
            f"== top CPU ==\n{HEADER}\n{WORKER_ROW}\n\n{SYSTEM_LINES}"
        )

    def test_mem_mode_ranks_by_memory(self, sampled, capsys):
        cli.main(["mem", "-n", "2"])
        assert capsys.readouterr().out == (
            f"== top memory ==\n{HEADER}\n{CHAT_ROW}\n{WORKER_ROW}\n\n{SYSTEM_LINES}"
        )

    def test_default_mode_prints_all_three_rankings(self, sampled, capsys):
        cli.main(["-n", "1"])
        assert capsys.readouterr().out == (
            f"== top CPU ==\n{HEADER}\n{WORKER_ROW}\n\n"
            f"== top memory ==\n{HEADER}\n{CHAT_ROW}\n\n"
            f"== top energy ==\n{HEADER}\n{WORKER_ROW}\n\n"
            f"{SYSTEM_LINES}"
        )

    @pytest.mark.parametrize(
        "mode, wants_power",
        [("cpu", False), ("mem", False), ("energy", True), ("all", True)],
    )
    def test_power_is_sampled_only_when_an_energy_ranking_is_shown(
        self, sampled, mode, wants_power
    ):
        cli.main([mode])
        assert sampled == [wants_power]


def pretend_stdout_is_a_terminal(monkeypatch):
    """Make the captured stdout look like a 200 column terminal.

    Call this from the test itself: pytest swaps sys.stdout after fixtures run.
    """
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.delenv("NO_COLOR", raising=False)


class TestTerminalOutput:
    def test_a_terminal_gets_color(self, sampled, monkeypatch, capsys):
        pretend_stdout_is_a_terminal(monkeypatch)
        cli.main(["cpu", "-n", "1"])
        assert capsys.readouterr().out == (
            "\033[34;1m== top CPU ==\033[0m\n"
            "\033[1m    PID\033[0m \033[34;1m  %CPU\033[0m \033[33;1m  %MEM\033[0m "
            "\033[33;1m  RSS_MB\033[0m \033[32;1m POWER\033[0m \033[1m        ELAPSED\033[0m  "
            "\033[1mCOMMAND\033[0m\n"
            "\033[2m  96413\033[0m \033[34;1m  99.5\033[0m \033[33m   2.5\033[0m "
            "\033[33m    2048\033[0m \033[32m  63.1\033[0m \033[2m          00:05\033[0m  "
            "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main\n"
            "\n"
            "\033[1mload:\033[0m 3.35 2.98 4.70 on 16 cores\n"
            "\033[1mswap:\033[0m \033[33m3191\033[0m of 4096 MB used\n"
        )

    def test_no_color_in_the_environment_turns_color_off(self, sampled, monkeypatch, capsys):
        pretend_stdout_is_a_terminal(monkeypatch)
        monkeypatch.setenv("NO_COLOR", "1")
        cli.main(["cpu", "-n", "1"])
        assert capsys.readouterr().out == (
            f"== top CPU ==\n{HEADER}\n{WORKER_ROW}\n\n{SYSTEM_LINES}"
        )

    def test_commands_are_cut_to_the_terminal_width(self, sampled, monkeypatch, capsys):
        pretend_stdout_is_a_terminal(monkeypatch)
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("COLUMNS", "63")
        cli.main(["cpu", "-n", "1"])
        assert capsys.readouterr().out.splitlines()[2] == (
            "  96413   99.5    2.5     2048   63.1           00:05  /opt/en…"
        )

    def test_full_keeps_whole_commands_and_color(self, sampled, monkeypatch, capsys):
        pretend_stdout_is_a_terminal(monkeypatch)
        monkeypatch.setenv("COLUMNS", "63")
        cli.main(["cpu", "-n", "1", "--full"])
        assert capsys.readouterr().out.splitlines()[2] == (
            "\033[2m  96413\033[0m \033[34;1m  99.5\033[0m \033[33m   2.5\033[0m "
            "\033[33m    2048\033[0m \033[32m  63.1\033[0m \033[2m          00:05\033[0m  "
            "/opt/env/bin/python -c from multiprocessing.spawn import spawn_main"
        )


@pytest.fixture
def interrupted_sleeps(monkeypatch):
    """Record each sleep, and press Ctrl-C during the second one."""
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli.time, "sleep", fake_sleep)
    return sleeps


class TestLiveMode:
    def test_redraws_in_place_on_the_alternate_screen_until_interrupted(
        self, sampled, interrupted_sleeps, monkeypatch, capsys
    ):
        pretend_stdout_is_a_terminal(monkeypatch)
        monkeypatch.setenv("NO_COLOR", "1")
        frame = (
            "\033[H"
            "== top CPU ==\033[K\n"
            f"{HEADER}\033[K\n"
            f"{WORKER_ROW}\033[K\n"
            "\033[K\n"
            "load: 3.35 2.98 4.70 on 16 cores\033[K\n"
            "swap: 3191 of 4096 MB used\033[K\n"
            "\033[K\n"
            "live, every 2s (Ctrl-C to stop)\033[K\033[J"
        )
        assert cli.main(["cpu", "-n", "1", "--live"]) == 0
        assert capsys.readouterr().out == (
            f"\033[?1049h\033[?25l{frame}{frame}\033[?25h\033[?1049l"
        )
        assert interrupted_sleeps == [2, 2]
        assert sampled == [False, False]

    def test_interval_sets_the_seconds_between_redraws(
        self, sampled, interrupted_sleeps, monkeypatch, capsys
    ):
        pretend_stdout_is_a_terminal(monkeypatch)
        cli.main(["cpu", "-n", "1", "--live", "--interval", "5"])
        assert interrupted_sleeps == [5, 5]
        assert "\033[2mlive, every 5s (Ctrl-C to stop)\033[0m\033[K\033[J" in capsys.readouterr().out

    @pytest.mark.parametrize(
        "mode, lines, titles_and_rows",
        [
            # 9 lines: title, header, 2 rows, blank, load, swap, blank, footer.
            ("mem", "9", ["== top memory ==", CHAT_ROW, WORKER_ROW]),
            # 19 lines: three rankings of 2 rows (5 lines each), then the last 4.
            (
                "all",
                "19",
                [
                    "== top CPU ==", WORKER_ROW, CHAT_ROW,
                    "== top memory ==", CHAT_ROW, WORKER_ROW,
                    "== top energy ==", WORKER_ROW, CHAT_ROW,
                ],
            ),
            # Too short for even one row: still show one.
            ("mem", "3", ["== top memory ==", CHAT_ROW]),
        ],
    )
    def test_rows_are_dropped_to_fit_the_terminal_height(
        self, sampled, interrupted_sleeps, monkeypatch, capsys, mode, lines, titles_and_rows
    ):
        pretend_stdout_is_a_terminal(monkeypatch)
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("LINES", lines)
        cli.main([mode, "-n", "3", "--live"])
        first_frame = capsys.readouterr().out.split("\033[H")[1].removesuffix("\033[J")
        shown = [line.removesuffix("\033[K") for line in first_frame.split("\n")]
        assert [line for line in shown if line and line != HEADER] == [
            *titles_and_rows,
            "load: 3.35 2.98 4.70 on 16 cores",
            "swap: 3191 of 4096 MB used",
            "live, every 2s (Ctrl-C to stop)",
        ]

    def test_live_needs_a_terminal(self, sampled, capsys):
        with pytest.raises(SystemExit) as error:
            cli.main(["cpu", "--live"])
        assert error.value.code == 2
        assert "--live needs a terminal" in capsys.readouterr().err
        assert sampled == []

    @pytest.mark.parametrize(
        "arguments, message",
        [
            (["cpu", "--live", "--full"], "--live cannot show whole commands, drop --full"),
            (["web", "--live"], "--live is for the terminal rankings, not 'web'"),
        ],
    )
    def test_live_rejects_what_it_cannot_combine_with(
        self, sampled, monkeypatch, capsys, arguments, message
    ):
        pretend_stdout_is_a_terminal(monkeypatch)
        with pytest.raises(SystemExit) as error:
            cli.main(arguments)
        assert error.value.code == 2
        assert message in capsys.readouterr().err
        assert sampled == []

    def test_interval_must_be_a_positive_number(self, sampled, capsys):
        with pytest.raises(SystemExit) as error:
            cli.main(["cpu", "--live", "--interval", "0"])
        assert error.value.code == 2
        assert "must be a positive number" in capsys.readouterr().err


class TestArguments:
    @pytest.mark.parametrize("count", ["0", "-3", "many"])
    def test_count_must_be_a_positive_number(self, sampled, capsys, count):
        with pytest.raises(SystemExit) as error:
            cli.main(["cpu", "-n", count])
        assert error.value.code == 2
        assert "must be a positive number" in capsys.readouterr().err

    def test_unknown_mode_is_rejected(self, sampled, capsys):
        with pytest.raises(SystemExit) as error:
            cli.main(["disk"])
        assert error.value.code == 2
        assert "invalid choice: 'disk'" in capsys.readouterr().err
