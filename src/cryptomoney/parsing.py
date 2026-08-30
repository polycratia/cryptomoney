"""Text written by people and APIs, read into amounts."""

from __future__ import annotations

import re
from decimal import Decimal

from .asset import Asset
from .money import Money, _check_rounding, _decimals_used, _quantize
from .registry import ASSETS, AssetRegistry, UnknownAsset

__all__ = ["ParseError", "parse_amount", "parse_money"]

_MAX_LENGTH = 256
_MAX_EXPONENT = 64

_SEPARATORS = re.compile(r"[ _,'\u00a0\u202f]")
_NUMBER = re.compile(
    r"(?P<sign>[+-])?"
    r"(?P<int>\d{1,3}(?:[ _,'\u00a0\u202f]\d{3})+|\d*)"
    r"(?:\.(?P<frac>\d+))?"
    r"(?:[eE](?P<exp>[+-]?\d+))?"
)
_SYMBOL = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_ATTACHED = re.compile(r"(?P<number>[^A-Za-z]+)(?P<symbol>[A-Za-z][A-Za-z0-9]*)")


class ParseError(ValueError):
    """Raised when text does not describe one amount."""


def _parse_decimal(text: str) -> Decimal:
    if isinstance(text, float):
        raise TypeError(
            "float is refused: parse the text the user or the API sent, not a float"
        )
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    if len(text) > _MAX_LENGTH:
        raise ParseError(f"text is longer than {_MAX_LENGTH} characters")
    stripped = text.strip()
    match = _NUMBER.fullmatch(stripped)
    if match is None:
        raise ParseError(f"{stripped!r} is not a plain decimal number")
    integer = _SEPARATORS.sub("", match["int"])
    fraction = match["frac"]
    if not integer and not fraction:
        raise ParseError(f"{stripped!r} has no digits")
    exponent = int(match["exp"] or 0)
    if abs(exponent) > _MAX_EXPONENT:
        raise ParseError(
            f"exponent {exponent} is outside the accepted range of "
            f"-{_MAX_EXPONENT} to {_MAX_EXPONENT}"
        )
    mantissa = (match["sign"] or "") + (integer or "0")
    if fraction:
        mantissa += f".{fraction}"
    return Decimal(f"{mantissa}E{exponent}")


def parse_amount(text: str, asset: Asset, *, rounding: str | None = None) -> Money:
    """Read one amount of ``asset`` from untrusted text."""
    if not isinstance(asset, Asset):
        raise TypeError(f"asset must be an Asset, got {type(asset).__name__}")
    if rounding is not None:
        _check_rounding(rounding)
    value = _parse_decimal(text)
    used = _decimals_used(value)
    if used > asset.decimals:
        if rounding is None:
            raise ParseError(
                f"{text.strip()!r} needs {used} decimal places and {asset.symbol} "
                f"has {asset.decimals}, pass rounding=... to accept the loss"
            )
        value = _quantize(value, asset.decimals, rounding)
    return Money(value, asset)


def _split_symbol(text: str) -> tuple[str, str]:
    tokens = text.split()
    if len(tokens) > 1:
        if _SYMBOL.fullmatch(tokens[-1]):
            return " ".join(tokens[:-1]), tokens[-1]
        if _SYMBOL.fullmatch(tokens[0]):
            return " ".join(tokens[1:]), tokens[0]
    elif tokens:
        attached = _ATTACHED.fullmatch(tokens[0])
        if attached is not None:
            return attached["number"], attached["symbol"]
    raise ParseError(f"{text.strip()!r} is not an amount followed by an asset symbol")


def _lookup(assets: AssetRegistry, symbol: str) -> Asset:
    for candidate in (symbol, symbol.upper()):
        try:
            return assets.get(candidate)
        except UnknownAsset:
            continue
    raise UnknownAsset(f"{symbol} is not a registered asset")


def parse_money(
    text: str,
    *,
    assets: AssetRegistry = ASSETS,
    rounding: str | None = None,
) -> Money:
    """Read an amount and its asset symbol, as in ``"0.5 BTC"``."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    if not isinstance(assets, AssetRegistry):
        raise TypeError(f"assets must be an AssetRegistry, got {type(assets).__name__}")
    if rounding is not None:
        _check_rounding(rounding)
    if len(text) > _MAX_LENGTH:
        raise ParseError(f"text is longer than {_MAX_LENGTH} characters")
    number, symbol = _split_symbol(text)
    return parse_amount(number, _lookup(assets, symbol), rounding=rounding)
