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
