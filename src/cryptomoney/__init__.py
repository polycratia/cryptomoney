"""Crypto amounts without float bugs."""

from .asset import Asset
from .money import CurrencyMismatch, Money
from .registry import (
    ASSETS,
    BNB,
    BTC,
    DOGE,
    ETH,
    LTC,
    SOL,
    USDC,
    USDT,
    AssetRegistry,
    UnknownAsset,
)

__all__ = [
    "ASSETS",
    "Asset",
    "AssetRegistry",
    "BNB",
    "BTC",
    "CurrencyMismatch",
    "DOGE",
    "ETH",
    "LTC",
    "Money",
    "SOL",
    "USDC",
    "USDT",
    "UnknownAsset",
    "__version__",
]

__version__ = "0.1.0"
