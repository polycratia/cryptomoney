"""Immutable decimal amounts bound to a single asset."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
    InvalidOperation,
    localcontext,
)
from typing import Union

from .asset import Asset

AmountLike = Union[Decimal, int, str]

_ROUNDING_MODES = frozenset(
    {
        ROUND_05UP,
        ROUND_CEILING,
        ROUND_DOWN,
        ROUND_FLOOR,
        ROUND_HALF_DOWN,
        ROUND_HALF_EVEN,
        ROUND_HALF_UP,
        ROUND_UP,
    }
)


class CurrencyMismatch(TypeError):
    """Raised when amounts of different assets are combined or compared."""


def _refuse_float(value: float) -> TypeError:
    return TypeError(
        f"float is refused: {value!r} is a binary float and cannot represent "
        "decimal fractions exactly. Pass a str or a Decimal instead."
    )


def _to_decimal(value: AmountLike, asset: Asset) -> Decimal:
    if isinstance(value, float):
        raise _refuse_float(value)
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise TypeError(
            f"amount must be a Decimal, int or str, got {type(value).__name__}"
        )
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"amount is not a valid decimal: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"amount must be finite, got {value!r}")
    used = -int(amount.as_tuple().exponent)
    if used > asset.decimals:
        raise ValueError(
            f"{asset.symbol} is divisible into {asset.decimals} decimal places, "
            f"but {value!r} needs {used}"
        )
    return amount


def _operand(value: AmountLike, name: str) -> Decimal:
    if isinstance(value, float):
        raise _refuse_float(value)
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise TypeError(
            f"{name} must be a Decimal, int or str, got {type(value).__name__}"
        )
    try:
        operand = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} is not a valid decimal: {value!r}") from exc
    if not operand.is_finite():
        raise ValueError(f"{name} must be finite, got {value!r}")
    return operand


def _check_rounding(rounding: str) -> None:
    if not isinstance(rounding, str):
        raise TypeError(f"rounding must be a str, got {type(rounding).__name__}")
    if rounding not in _ROUNDING_MODES:
        raise ValueError(
            f"unknown rounding mode {rounding!r}, expected one of "
            f"{', '.join(sorted(_ROUNDING_MODES))}"
        )


def _working_precision(asset: Asset, *values: Decimal) -> int:
    digits = max(len(value.as_tuple().digits) for value in values)
    return digits + asset.decimals + 10


def _quantize(amount: Decimal, asset: Asset, rounding: str) -> Decimal:
    quantum = Decimal((0, (1,), -asset.decimals))
    with localcontext() as ctx:
        ctx.prec = _working_precision(asset, amount)
        return amount.quantize(quantum, rounding=rounding)


@dataclass(frozen=True, slots=True)
class Money:
    """A decimal amount of a single asset. A float never enters this type."""

    amount: Decimal
    asset: Asset

    def __post_init__(self) -> None:
        if not isinstance(self.asset, Asset):
            raise TypeError(f"asset must be an Asset, got {type(self.asset).__name__}")
        object.__setattr__(self, "amount", _to_decimal(self.amount, self.asset))

    @classmethod
    def zero(cls, asset: Asset) -> Money:
        return cls(Decimal(0), asset)

    @classmethod
    def from_base_units(cls, units: int, asset: Asset) -> Money:
        """Build an amount from an integer count of the asset's smallest unit."""
        if isinstance(units, float):
            raise _refuse_float(units)
        if isinstance(units, bool) or not isinstance(units, int):
            raise TypeError(f"units must be an int, got {type(units).__name__}")
        if not isinstance(asset, Asset):
            raise TypeError(f"asset must be an Asset, got {type(asset).__name__}")
        digits = tuple(int(digit) for digit in str(abs(units)))
        return cls(Decimal((1 if units < 0 else 0, digits, -asset.decimals)), asset)

    def to_base_units(self) -> int:
        """The amount as an integer count of the asset's smallest unit."""
        sign, digits, exponent = self.amount.as_tuple()
        value = int("".join(str(digit) for digit in digits))
        # Construction rejects amounts finer than the asset, so the shift is never
        # negative and nothing is ever rounded away here.
        units = value * 10 ** (int(exponent) + self.asset.decimals)
        return -units if sign else units

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    def _require_same_asset(self, other: Money) -> None:
        if self.asset != other.asset:
            raise CurrencyMismatch(
                f"{self.asset.symbol} and {other.asset.symbol} are different assets"
            )

    def multiply(self, factor: AmountLike, *, rounding: str) -> Money:
        """Multiply by a factor and round the result to the asset's precision."""
        _check_rounding(rounding)
        operand = _operand(factor, "factor")
        with localcontext() as ctx:
            ctx.prec = _working_precision(self.asset, self.amount, operand)
            ctx.rounding = rounding
            product = self.amount * operand
        return Money(_quantize(product, self.asset, rounding), self.asset)

    def divide(self, divisor: AmountLike, *, rounding: str) -> Money:
        """Divide by a divisor and round the result to the asset's precision."""
        _check_rounding(rounding)
        operand = _operand(divisor, "divisor")
        if operand == 0:
            raise ZeroDivisionError(f"cannot divide {self} by zero")
        with localcontext() as ctx:
            ctx.prec = _working_precision(self.asset, self.amount, operand)
            ctx.rounding = rounding
            quotient = self.amount / operand
        return Money(_quantize(quotient, self.asset, rounding), self.asset)

    def split(self, parts: int) -> list[Money]:
        """Split into parts that add back up to this amount, exactly."""
        if isinstance(parts, bool) or not isinstance(parts, int):
            raise TypeError(f"parts must be an int, got {type(parts).__name__}")
        if parts < 1:
            raise ValueError(f"parts must be at least 1, got {parts}")
        total = self.to_base_units()
        sign = -1 if total < 0 else 1
        share, remainder = divmod(abs(total), parts)
        return [
            Money.from_base_units(
                sign * (share + (1 if index < remainder else 0)), self.asset
            )
            for index in range(parts)
        ]

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return Money(self.amount + other.amount, self.asset)

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return Money(self.amount - other.amount, self.asset)

    def __mul__(self, factor: int) -> Money:
        if isinstance(factor, float):
            raise _refuse_float(factor)
        if isinstance(factor, (Decimal, str)):
            raise TypeError(
                f"multiplying by {factor!r} can land below the precision of "
                f"{self.asset.symbol}. Use .multiply(factor, rounding=...) instead."
            )
        if isinstance(factor, bool) or not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount * factor, self.asset)

    def __rmul__(self, factor: int) -> Money:
        return self.__mul__(factor)

    def __truediv__(self, divisor: object) -> Money:
        raise TypeError(
            "/ is refused because the rounding of the result would be implicit. "
            "Use .divide(divisor, rounding=...) or .split(parts)."
        )

    def __neg__(self) -> Money:
        return Money(-self.amount, self.asset)

    def __pos__(self) -> Money:
        return self

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.asset)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_asset(other)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount:f} {self.asset.symbol}"
