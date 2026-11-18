"""Machine-wide numbers that put the process list in context."""

import re
from dataclasses import dataclass

_SWAP = re.compile(r"total = ([\d.]+)M\s+used = ([\d.]+)M")


@dataclass(frozen=True)
class SystemStats:
    """Load, core count, memory size and swap use."""

    load: tuple[float, float, float]
    cores: int
    memory_mb: int
    swap_used_mb: float
    swap_total_mb: float


def parse_swap(output: str) -> tuple[float, float]:
    """Read (used, total) megabytes from `sysctl -n vm.swapusage`."""
    match = _SWAP.search(output)
    if not match:
        raise ValueError(f"cannot read swap usage from '{output.strip()}'")
    return float(match.group(2)), float(match.group(1))
