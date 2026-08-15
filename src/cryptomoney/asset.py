"""Assets that a monetary amount can be bound to."""

from __future__ import annotations

from dataclasses import dataclass

_MAX_DECIMALS = 36


@dataclass(frozen=True, slots=True)
class Asset:
    """A crypto asset and the number of decimal places it is divisible into."""

    symbol: str
    decimals: int

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be a str, got {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.strip() != self.symbol:
            raise ValueError(f"symbol must be non-empty and unpadded, got {self.symbol!r}")
        if isinstance(self.decimals, bool) or not isinstance(self.decimals, int):
            raise TypeError(f"decimals must be an int, got {type(self.decimals).__name__}")
        if not 0 <= self.decimals <= _MAX_DECIMALS:
            raise ValueError(
                f"decimals must be between 0 and {_MAX_DECIMALS}, got {self.decimals}"
            )

    def __str__(self) -> str:
        return self.symbol
