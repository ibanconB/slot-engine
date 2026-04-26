"""Resultado de un giro: la rejilla de símbolos visible y dónde paró cada carrete."""

from dataclasses import dataclass

from slot_engine.domain.symbol import Symbol


@dataclass(frozen=True, slots=True)
class SpinResult:
    """Snapshot inmutable del resultado de un giro.

    Attributes:
        columns: Una tupla de columnas. Cada columna es a su vez una tupla
            de símbolos visibles (de arriba a abajo) en ese carrete.
        stop_positions: Posición en la que paró cada carrete (índice dentro
            del strip original). Útil para auditoría y para reproducir giros.
    """

    columns: tuple[tuple[Symbol, ...], ...]
    stop_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.columns:
            raise ValueError("SpinResult must contain at least one column")
        if len(self.columns) != len(self.stop_positions):
            raise ValueError("columns and stop_positions must have the same length")
        expected_rows = len(self.columns[0])
        if expected_rows == 0:
            raise ValueError("Each column must contain at least one symbol")
        if any(len(col) != expected_rows for col in self.columns):
            raise ValueError("All columns must have the same number of rows")

    @property
    def num_columns(self) -> int:
        """Número de carretes visibles."""
        return len(self.columns)

    @property
    def num_rows(self) -> int:
        """Número de filas visibles (window size)."""
        return len(self.columns[0])

    def row(self, index: int) -> tuple[Symbol, ...]:
        """Devuelve los símbolos de una fila concreta a lo largo de todas las columnas."""
        if not 0 <= index < self.num_rows:
            raise IndexError(f"Row index {index} out of range [0, {self.num_rows})")
        return tuple(column[index] for column in self.columns)

    def render(self) -> str:
        """Representación legible de la rejilla, fila a fila."""
        lines = []
        for row_index in range(self.num_rows):
            cells = [f"{symbol.name:<8}" for symbol in self.row(row_index)]
            lines.append(" | ".join(cells))
        return "\n".join(lines)
