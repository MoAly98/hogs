import pytest

from hogs.processes import Process, app_name, parse_elapsed, parse_power, parse_ps, rank, with_power

PS_OUTPUT = """\
    1     0   0.2  0.0  28768 2-01:02:03 /sbin/launchd
  334     1   0.0  0.0  11936 01:02:03 /usr/libexec/UserEventAgent (System)

96413 96405  99.5  2.5 2097152 00:05 /opt/env/bin/python -c import a;  a.run(fd=7)
"""

TOP_OUTPUT = """\
Processes: 910 total, 3 running, 907 sleeping, 6466 threads
Load Avg: 3.15, 2.93, 4.70

PID    POWER
96413  0.0
334    0.0
Processes: 910 total, 3 running, 907 sleeping, 6466 threads
Load Avg: 3.15, 2.93, 4.70

PID    POWER
96413  63.1
334    26.6
1      0.0
"""


class TestParsePs:
    def test_reads_every_column_of_a_row(self):
        assert parse_ps(PS_OUTPUT)[0] == Process(
            pid=1,
            ppid=0,
            cpu=0.2,
            mem=0.0,
            rss_kb=28768,
            elapsed_seconds=176523,
            command="/sbin/launchd",
        )

    def test_skips_blank_lines(self):
        assert [p.pid for p in parse_ps(PS_OUTPUT)] == [1, 334, 96413]

    def test_keeps_the_command_exactly_including_inner_spacing(self):
        assert parse_ps(PS_OUTPUT)[2].command == "/opt/env/bin/python -c import a;  a.run(fd=7)"

    def test_power_is_unknown_until_sampled(self):
        assert parse_ps(PS_OUTPUT)[2].power is None

    def test_empty_output_gives_no_processes(self):
        assert parse_ps("") == []


class TestParseElapsed:
    @pytest.mark.parametrize(
        "etime, seconds",
        [
            ("00:05", 5),
            ("12:34", 754),
            ("01:02:03", 3723),
            ("2-01:02:03", 176523),
        ],
    )
    def test_converts_ps_elapsed_time_to_seconds(self, etime, seconds):
        assert parse_elapsed(etime) == seconds


class TestParsePower:
    def test_uses_only_the_last_sample(self):
        assert parse_power(TOP_OUTPUT) == {96413: 63.1, 334: 26.6, 1: 0.0}

    def test_output_without_a_sample_gives_no_power(self):
        assert parse_power("Processes: 910 total\n") == {}


class TestWithPower:
    def test_attaches_power_by_pid(self, launchd, chat_app):
        updated = with_power([launchd, chat_app], {1: 0.5, 334: 9.0})
        assert [p.power for p in updated] == [0.5, 9.0]

    def test_process_missing_from_the_power_sample_gets_zero(self, launchd):
        assert with_power([launchd], {})[0].power == 0.0


class TestAppName:
    @pytest.mark.parametrize(
        "command, name",
        [
            ("/sbin/launchd", "launchd"),
            ("claude --resume", "claude"),
            ("-zsh", "zsh"),
            ("/opt/env/bin/python -c import a", "python"),
            ("/usr/libexec/UserEventAgent (System)", "UserEventAgent"),
            ("/Applications/Chat.app/Contents/MacOS/Chat --type=renderer", "Chat"),
            (
                "/Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper (Renderer).app"
                "/Contents/MacOS/Code Helper (Renderer) --type=renderer",
                "Visual Studio Code",
            ),
        ],
    )
    def test_names_a_process_by_its_app_bundle_or_executable(self, command, name):
        assert app_name(command) == name

    def test_process_exposes_its_name(self, chat_app):
        assert chat_app.name == "Chat"


class TestRank:
    def test_cpu_ranking_puts_the_busiest_first(self, launchd, chat_app, worker):
        ranked = rank([launchd, chat_app, worker], "cpu", 3)
        assert [p.pid for p in ranked] == [96413, 334, 1]

    def test_memory_ranking_uses_resident_size(self, launchd, chat_app, worker):
        ranked = rank([launchd, chat_app, worker], "mem", 3)
        assert [p.pid for p in ranked] == [334, 96413, 1]

    def test_energy_ranking_treats_unsampled_power_as_zero(self, launchd, chat_app, worker):
        ranked = rank([launchd, chat_app, worker], "energy", 3)
        assert [p.pid for p in ranked] == [96413, 334, 1]

    def test_count_limits_the_ranking(self, launchd, chat_app, worker):
        assert [p.pid for p in rank([launchd, chat_app, worker], "cpu", 1)] == [96413]

    def test_count_larger_than_the_list_returns_everything(self, launchd):
        assert rank([launchd], "cpu", 10) == [launchd]

    def test_unknown_metric_is_rejected(self, launchd):
        with pytest.raises(ValueError, match="unknown metric 'disk'"):
            rank([launchd], "disk", 1)
