"""Pydantic models for Slot Engine configuration"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base model with strict configuration for all models

    - extra="forbid": rejects unknown fields in the TOML
    - frozen=True: inmutable instances after validation
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class GameMeta(StrictModel):
    """Game Metadata"""

    name: str = Field(min_length=1)
    engine: str = Field(min_length=1)
    window_size: int = Field(ge=1)


class SymbolConfig(StrictModel):
    """Definition of a symbol inside the catalog"""

    is_wild: bool = False
    is_scatter: bool = False


class ReelConfig(StrictModel):
    """A reel strip: ordered list of symbol name"""

    strip: tuple[str, ...] = Field(min_length=1)


class PaylineConfig(StrictModel):
    """Definition of a payline: name + reels by column"""

    name: str = Field(min_length=1)
    rows: tuple[int, ...] = Field(min_length=1)


class GameConfig(StrictModel):
    """Complete configuration of a game loaded from TOML"""

    game: GameMeta
    symbols: dict[str, SymbolConfig]
    reels: tuple[ReelConfig, ...] = Field(min_length=1)
    paytable: dict[str, dict[int, Decimal]]
    paylines: tuple[PaylineConfig, ...] = Field(min_length=1)
    cascade: CascadeConfig | None = None

class CascadeConfig(StrictModel):
    """Cascade rules: multiplier values per cascade step.

    Step 0 uses multipliers[0], step 1 uses multipliers[1], etc.
    Engines decide overflow policy when cascade exceeds list length
    (typically clamp to last value).
    """

    multipliers: tuple[int, ...] = Field(min_length=1)

    @field_validator("multipliers")
    @classmethod
    def all_positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if any(m <= 0 for m in v):
            raise ValueError("All multipliers must be positive integers")
        return v