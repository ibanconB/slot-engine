"""Demo del motor de slot — script reejecutable para probar a mano."""

from slot_engine.domain import Reel, Symbol
from slot_engine.engine import SpinEngine
from slot_engine.rng import SecureRng, SeededRng


def build_demo_reels() -> tuple[Reel, ...]:
    """Construye 5 carretes simples con los símbolos clásicos."""
    cherry, lemon, bell, bar, seven = (
        Symbol("cherry"),
        Symbol("lemon"),
        Symbol("bell"),
        Symbol("bar"),
        Symbol("seven"),
    )
    base_strip = [cherry, lemon, bell, bar, seven, cherry, lemon, bell] * 4
    return tuple(Reel.from_symbol(base_strip) for _ in range(5))


def main() -> None:
    reels = build_demo_reels()

    print("=" * 50)
    print("Spin determinista (seed=42)")
    print("=" * 50)
    engine = SpinEngine.create(reels, window_size=3, rng=SeededRng(42))
    result = engine.spin()
    print(result.render())
    print(f"\nstop_positions = {result.stop_positions}")

    print("\n" + "=" * 50)
    print("Tres spins de producción (RNG seguro)")
    print("=" * 50)
    prod_engine = SpinEngine.create(reels, window_size=3, rng=SecureRng())
    for i in range(3):
        print(f"\n--- Spin {i + 1} ---")
        print(prod_engine.spin().render())


if __name__ == "__main__":
    main()
