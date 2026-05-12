"""Free spins module: per-(player, game) counter of available free spins."""
from slot_engine.free_spins.operations import (
    NoFreeSpinsAvailableError,
    grant,
    peek,
    use_one,
)
from slot_engine.free_spins.store import FreeSpinsStore

__all__ = [
    "FreeSpinsStore",
    "NoFreeSpinsAvailableError",
    "grant",
    "peek",
    "use_one",
]