"""Every rounding mode, checked by the direction it prescribes.

The reference is the exact result counted in the base units it was rounded to,
kept as a ``Fraction`` because the quotient of two decimals need not be one. A
mode may move the last unit below or above that value, towards zero or away
from it, but never by more than one unit.
"""

from __future__ import annotations

import math
import random
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
)
from fractions import Fraction

import pytest

from cryptomoney import Asset, Money, ParseError, parse_amount
from cryptomoney.money import _ROUNDING_MODES, _significant_decimals

SEED = 20261108

ROUNDING_MODES = tuple(sorted(_ROUNDING_MODES))
ROUNDING_IDS = tuple(mode.removeprefix("ROUND_").lower() for mode in ROUNDING_MODES)

HALF_MODES = frozenset({ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP})

# Operands that land the result exactly between two base units, where the mode
# is the only thing left to decide the last one.
TIE_FACTORS = (Decimal("0.5"), Decimal("-0.5"), Decimal("1.5"), Decimal("0.25"))
TIE_DIVISORS = (2, -2, 4, 8, -16, Decimal("2.5"))
# Divisors whose quotient does not terminate, so no tie is ever reached.
ENDLESS_DIVISORS = (3, -3, 7, -9, Decimal("1.3"))


def _stream(name: str, asset: Asset) -> random.Random:
    # Seeded per asset and per test, so a case that fails once comes back.
    return random.Random(f"{SEED}:{name}:{asset.symbol}:{asset.decimals}")


def _sampled(stream: random.Random, base_units: list[int]) -> list[int]:
    """The boundary counts every asset has, plus a seeded spread of the rest."""
    return base_units[:8] + stream.sample(base_units[16:], 12)


def _factors(stream: random.Random, asset: Asset) -> list[Decimal]:
    factors = list(TIE_FACTORS)
    for _ in range(6):
        factor = Decimal(stream.randrange(1, 10**6)).scaleb(
            -stream.randrange(1, asset.decimals + 4)
        )
        factors.append(-factor if stream.getrandbits(1) else factor)
    return factors


def _divisors(stream: random.Random) -> list[int | Decimal]:
    divisors: list[int | Decimal] = [*TIE_DIVISORS, *ENDLESS_DIVISORS]
    for _ in range(4):
        divisor = stream.randrange(1, 10_000)
        divisors.append(-divisor if stream.getrandbits(1) else divisor)
    return divisors


def _finer_texts(stream: random.Random, asset: Asset) -> list[str]:
    """Amounts written finer than ``asset`` is divisible into."""
    places = asset.decimals
    texts = [
        f"5E-{places + 1}",
        f"-5E-{places + 1}",
        f"1E-{places + 1}",
        f"-9E-{places + 1}",
        f"15E-{places + 2}",
        f"-25E-{places + 2}",
    ]
    for _ in range(10):
        extra = stream.randrange(1, 4)
        units = stream.randrange(-(10**9), 10**9)
        tail = stream.randrange(10**extra)
        texts.append(f"{units}{tail:0{extra}d}E-{places + extra}")
    return texts


def _shorter_places(stream: random.Random, significant: int) -> list[int]:
    """Decimal places too few to hold an amount needing ``significant`` of them."""
    candidates = [0, significant - 1, significant // 2]
    if significant > 1:
        candidates.append(stream.randrange(significant))
    return sorted({place for place in candidates if 0 <= place < significant})


def _units(value: Decimal, places: int) -> int:
    """The value as an integer count of ``10**-places``."""
    scaled = Fraction(value) * 10**places
    assert scaled.denominator == 1
    return int(scaled)


def _assert_rounded(result: int, exact: Fraction, rounding: str) -> None:
    """``result`` is the neighbour of ``exact`` that ``rounding`` prescribes.

    Both count the unit the result was rounded to, so the modes read as
    integers: below for the floor, above for the ceiling, towards zero and away.
    """
    below = math.floor(exact)
    above = math.ceil(exact)
    towards = int(exact)
    away = towards if exact == towards else towards + (1 if exact > 0 else -1)

    assert below <= result <= above

    if exact == below:
        assert result == below
        return

    if rounding == ROUND_FLOOR:
        assert result == below
    elif rounding == ROUND_CEILING:
        assert result == above
    elif rounding == ROUND_DOWN:
        assert result == towards
    elif rounding == ROUND_UP:
        assert result == away
    elif rounding == ROUND_05UP:
        # Away from zero only where truncating leaves a 0 or a 5 at the end.
        assert result == (away if towards % 5 == 0 else towards)
    else:
        assert rounding in HALF_MODES
        to_below = exact - below
        to_above = above - exact
        if to_below < to_above:
            assert result == below
        elif to_above < to_below:
            assert result == above
        elif rounding == ROUND_HALF_UP:
            assert result == away
        elif rounding == ROUND_HALF_DOWN:
            assert result == towards
        else:
            assert result == (below if below % 2 == 0 else above)


@pytest.mark.parametrize("rounding", ROUNDING_MODES, ids=ROUNDING_IDS)
def test_multiply_rounds_on_the_side_of_its_mode(asset, base_units, rounding):
    stream = _stream("multiply", asset)
    factors = _factors(stream, asset)
    for units in _sampled(stream, base_units):
        money = Money.from_base_units(units, asset)
        for factor in factors:
            product = money.multiply(factor, rounding=rounding)
            assert product.asset == asset
            _assert_rounded(
                product.to_base_units(), units * Fraction(factor), rounding
            )


@pytest.mark.parametrize("rounding", ROUNDING_MODES, ids=ROUNDING_IDS)
def test_divide_rounds_on_the_side_of_its_mode(asset, base_units, rounding):
    stream = _stream("divide", asset)
    divisors = _divisors(stream)
    for units in _sampled(stream, base_units):
        money = Money.from_base_units(units, asset)
        for divisor in divisors:
            quotient = money.divide(divisor, rounding=rounding)
            assert quotient.asset == asset
            _assert_rounded(
                quotient.to_base_units(), units / Fraction(divisor), rounding
            )


@pytest.mark.parametrize("rounding", ROUNDING_MODES, ids=ROUNDING_IDS)
def test_parse_amount_rounds_on_the_side_of_its_mode(asset, rounding):
    stream = _stream("parse", asset)
    scale = 10**asset.decimals
    for text in _finer_texts(stream, asset):
        with pytest.raises(ParseError):
            parse_amount(text, asset)
        money = parse_amount(text, asset, rounding=rounding)
        assert money.asset == asset
        _assert_rounded(
            money.to_base_units(), Fraction(Decimal(text)) * scale, rounding
        )


@pytest.mark.parametrize("rounding", ROUNDING_MODES, ids=ROUNDING_IDS)
def test_format_rounds_on_the_side_of_its_mode(asset, base_units, rounding):
    stream = _stream("format", asset)
    for units in _sampled(stream, base_units):
        money = Money.from_base_units(units, asset)
        exact = Fraction(money.amount)
        for places in _shorter_places(stream, _significant_decimals(money.amount)):
            text = money.format(symbol=False, decimals=places, rounding=rounding)
            assert "e" not in text.lower()
            _assert_rounded(
                _units(Decimal(text), places), exact * 10**places, rounding
            )
