"""RNG - Random number generator
slot engine receives a RNG via dependency injection
for the tests be able to use a determinist one (with seeds)
while production uses a random number generator
"""

import random
import secrets
from typing import Protocol, runtime_checkable


@runtime_checkable
class RandomNumberGenerator(Protocol):
    """Mininal interface for random number generator that engines use

    An object with a methos `randrange(stop) -> int` that returns an
    int in [0, stop] fulfills this protocol, without heritage
    """

    def randrange(self, stop: int) -> int:
        """Returns a random integer between 0 and `stop`"""
        ...


class SecureRNG:
    """Production RNG bases in `secrets"""

    def randrange(self, stop: int) -> int:
        if stop <= 0:
            raise ValueError(f"stop must be > 0, got {stop}")
        return secrets.randbelow(stop)


class SeededRng:
    """Deterministic RNG for tests, with seed.

    Using the same seed always produces the same sequence of numbers.
    This enables writing tests for non-deterministic code.
    """

    def __init__(self, seed: int) -> None:  # antes: -> int
        self._random = random.Random(seed)

    def randrange(self, stop: int) -> int:  # antes: randrange
        if stop <= 0:
            raise ValueError(f"stop must be > 0, got {stop}.")
        return self._random.randrange(stop)
