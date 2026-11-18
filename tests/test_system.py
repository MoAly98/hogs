import pytest

from hogs.system import parse_swap


class TestParseSwap:
    def test_reads_used_and_total_megabytes(self):
        output = "total = 4096.00M  used = 3190.69M  free = 905.31M  (encrypted)\n"
        assert parse_swap(output) == (3190.69, 4096.0)

    def test_swap_that_is_off_reads_as_zero(self):
        output = "total = 0.00M  used = 0.00M  free = 0.00M  (encrypted)\n"
        assert parse_swap(output) == (0.0, 0.0)

    def test_unrecognised_output_is_rejected(self):
        with pytest.raises(ValueError, match="cannot read swap usage from 'nonsense'"):
            parse_swap("nonsense")
