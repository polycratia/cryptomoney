"""Named base units of the assets that have one."""

from __future__ import annotations

from .asset import Asset
from .money import CurrencyMismatch, Money
from .registry import BTC, ETH

__all__ = ["from_satoshi", "from_wei", "to_satoshi", "to_wei"]


def _require_asset(money: Money, asset: Asset) -> None:
    if not isinstance(money, Money):
        raise TypeError(f"expected a Money, got {type(money).__name__}")
    if money.asset != asset:
        raise CurrencyMismatch(
            f"{money.asset.symbol} is not {asset.symbol}, "
            f"use Money.to_base_units() instead"
        )


def from_satoshi(units: int) -> Money:
    """An amount of BTC from a count of satoshi."""
    return Money.from_base_units(units, BTC)


def to_satoshi(money: Money) -> int:
    """The satoshi count of an amount of BTC."""
    _require_asset(money, BTC)
    return money.to_base_units()


def from_wei(units: int) -> Money:
    """An amount of ETH from a count of wei."""
    return Money.from_base_units(units, ETH)


def to_wei(money: Money) -> int:
    """The wei count of an amount of ETH."""
    _require_asset(money, ETH)
    return money.to_base_units()
