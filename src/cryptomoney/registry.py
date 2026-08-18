"""A registry of known assets and their precision."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .asset import Asset

__all__ = [
    "ASSETS",
    "AssetRegistry",
    "UnknownAsset",
    "BNB",
    "BTC",
    "DOGE",
    "ETH",
    "LTC",
    "SOL",
    "USDC",
    "USDT",
]


class UnknownAsset(KeyError):
    """Raised when a symbol is not present in a registry."""


class AssetRegistry:
    """A collection of assets keyed by symbol, extensible by the caller."""

    __slots__ = ("_assets",)

    def __init__(self, assets: Iterable[Asset] = ()) -> None:
        self._assets: dict[str, Asset] = {}
        for asset in assets:
            self.register(asset)

    def register(self, asset: Asset, *, replace: bool = False) -> Asset:
        """Add an asset and return it. Registering the same definition twice is fine."""
        if not isinstance(asset, Asset):
            raise TypeError(f"asset must be an Asset, got {type(asset).__name__}")
        known = self._assets.get(asset.symbol)
        if known is not None and known != asset and not replace:
            raise ValueError(
                f"{asset.symbol} is already registered with {known.decimals} "
                f"decimal places; pass replace=True to override it"
            )
        self._assets[asset.symbol] = asset
        return asset

    def get(self, symbol: str) -> Asset:
        """Return the asset registered under ``symbol``."""
        if not isinstance(symbol, str):
            raise TypeError(f"symbol must be a str, got {type(symbol).__name__}")
        try:
            return self._assets[symbol]
        except KeyError:
            raise UnknownAsset(f"{symbol} is not a registered asset") from None

    def copy(self) -> AssetRegistry:
        """Return an independent registry with the same assets."""
        return AssetRegistry(self._assets.values())

    def symbols(self) -> tuple[str, ...]:
        return tuple(self._assets)

    def __getitem__(self, symbol: str) -> Asset:
        return self.get(symbol)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, Asset):
            return self._assets.get(item.symbol) == item
        return item in self._assets

    def __iter__(self) -> Iterator[Asset]:
        return iter(tuple(self._assets.values()))

    def __len__(self) -> int:
        return len(self._assets)

    def __repr__(self) -> str:
        return f"AssetRegistry({list(self._assets.values())!r})"


BTC = Asset("BTC", 8)
ETH = Asset("ETH", 18)
USDT = Asset("USDT", 6)
USDC = Asset("USDC", 6)
LTC = Asset("LTC", 8)
DOGE = Asset("DOGE", 8)
SOL = Asset("SOL", 9)
BNB = Asset("BNB", 18)

ASSETS = AssetRegistry([BTC, ETH, USDT, USDC, LTC, DOGE, SOL, BNB])
