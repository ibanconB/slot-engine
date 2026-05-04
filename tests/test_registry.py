"""Tests for the engine registry: registration, lookup, error cases."""
import pytest

from slot_engine.engines import registry as registry_mod


@pytest.fixture(autouse=True)
def isolated_registry():
    """Snapshot the registry around each test to keep tests independent.

    Module-level state pollutes across tests if not isolated. We back up
    the current registry, run with a clean slate, then restore.
    """
    snapshot = dict(registry_mod._REGISTRY)
    registry_mod._REGISTRY.clear()
    yield
    registry_mod._REGISTRY.clear()
    registry_mod._REGISTRY.update(snapshot)


def test_registered_engine_can_be_retrieved() -> None:
    @registry_mod.register_engine("test_engine")
    class TestEngine:
        def play(self) -> object:
            return None

    assert registry_mod.get_engine_class("test_engine") is TestEngine


def test_registering_same_name_twice_raises() -> None:
    @registry_mod.register_engine("dup")
    class First:
        def play(self) -> object:
            return None

    with pytest.raises(ValueError, match="already registered"):
        @registry_mod.register_engine("dup")
        class Second:
            def play(self) -> object:
                return None


def test_lookup_unknown_engine_raises_with_available_list() -> None:
    @registry_mod.register_engine("known")
    class Known:
        def play(self) -> object:
            return None

    with pytest.raises(KeyError, match="known"):
        registry_mod.get_engine_class("unknown")


def test_available_engines_returns_sorted_tuple() -> None:
    @registry_mod.register_engine("zeta")
    class Z:
        def play(self) -> object:
            return None

    @registry_mod.register_engine("alpha")
    class A:
        def play(self) -> object:
            return None

    assert registry_mod.available_engines() == ("alpha", "zeta")