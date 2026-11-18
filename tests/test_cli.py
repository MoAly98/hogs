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
