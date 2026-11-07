"""Invariants that hold for every registered asset, whatever the amount."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR

import pytest

from cryptomoney import (
    ASSETS,
    ETH,
    USDT,
    Asset,
    AssetRegistry,
    Money,
    UnknownAsset,
    parse_amount,
    parse_money,
)
from cryptomoney.money import _ROUNDING_MODES

# Every mode but the two that lean towards an infinity is defined as towards or
# away from zero, so it treats an amount and its negation alike.
ASYMMETRIC_MODES = frozenset({ROUND_FLOOR, ROUND_CEILING})
SYMMETRIC_MODES = tuple(sorted(_ROUNDING_MODES - ASYMMETRIC_MODES))
SYMMETRIC_IDS = tuple(mode.removeprefix("ROUND_").lower() for mode in SYMMETRIC_MODES)

# Factors whose product lands below the asset's precision for most amounts, so
# the rounding mode is what decides the last base unit.
FRACTIONAL_FACTORS = ("0.3", "0.125", "2.5", "-1.0625")

# convert quantizes its product at the target asset's precision, so the same
# modes decide its last base unit. A rate is always above zero, so the sign of
# the result comes from the amount alone.
CONVERSION_TARGETS = (Asset("COARSE", 2), USDT, ETH)
CONVERSION_TARGET_RATES = ("0.3", "0.125", "2.5")


def _half_unit_rate(asset: Asset, target: Asset) -> str:
    """The rate that turns one base unit of ``asset`` into half a unit of ``target``."""
    return f"5E{asset.decimals - target.decimals - 1}"


def test_registry_resolves_every_symbol(asset):
    assert ASSETS.get(asset.symbol) is asset
    assert asset in ASSETS
    assert asset.symbol in ASSETS.symbols()


def test_zero_is_the_additive_identity(asset, base_units):
    zero = Money.zero(asset)
    assert zero.is_zero
    assert zero.to_base_units() == 0
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        assert money + zero == money
        assert zero + money == money
        assert money - money == zero


def test_sign_round_trips(asset, base_units):
    for units in base_units:
        money = Money.from_base_units(units, asset)
        assert +money is money
        assert -(-money) == money
        assert (-money).to_base_units() == -units
        assert abs(money).to_base_units() == abs(units)
        assert money.is_negative == (units < 0)
        assert money.is_positive == (units > 0)


@pytest.mark.parametrize("rounding", SYMMETRIC_MODES, ids=SYMMETRIC_IDS)
def test_rounding_is_symmetric_around_zero(asset, base_units, rounding):
    finer = [
        f"5E-{asset.decimals + 1}",
        f"1E-{asset.decimals + 1}",
        f"7E-{asset.decimals + 1}",
        f"15E-{asset.decimals + 2}",
        f"25E-{asset.decimals + 2}",
    ]
    for text in finer:
        positive = parse_amount(text, asset, rounding=rounding)
        negative = parse_amount(f"-{text}", asset, rounding=rounding)
        assert negative.to_base_units() == -positive.to_base_units()
        assert negative == -positive

    money = Money.from_base_units(10**asset.decimals + 1, asset)
    assert (-money).divide(3, rounding=rounding) == -money.divide(3, rounding=rounding)

    for factor in FRACTIONAL_FACTORS:
        for units in base_units[:40]:
            money = Money.from_base_units(units, asset)
            scaled = money.multiply(factor, rounding=rounding)
            negated = (-money).multiply(factor, rounding=rounding)
            assert negated == -scaled
            assert negated.to_base_units() == -scaled.to_base_units()

    for target in CONVERSION_TARGETS:
        one = Money.from_base_units(1, asset)
        half_rate = _half_unit_rate(asset, target)
        converted = one.convert(target, half_rate, rounding=rounding)
        negated = (-one).convert(target, half_rate, rounding=rounding)
        assert negated == -converted
        assert negated.to_base_units() == -converted.to_base_units()

        for rate in CONVERSION_TARGET_RATES:
            for units in base_units[:20]:
                money = Money.from_base_units(units, asset)
                converted = money.convert(target, rate, rounding=rounding)
                negated = (-money).convert(target, rate, rounding=rounding)
                assert converted.asset == target
                assert negated == -converted
                assert negated.to_base_units() == -converted.to_base_units()


@pytest.mark.parametrize("rounding", sorted(ASYMMETRIC_MODES))
def test_floor_and_ceiling_are_the_asymmetric_modes(asset, rounding):
    assert rounding in _ROUNDING_MODES
    assert rounding not in SYMMETRIC_MODES
    half = f"5E-{asset.decimals + 1}"
    positive = parse_amount(half, asset, rounding=rounding)
    negative = parse_amount(f"-{half}", asset, rounding=rounding)
    assert negative.to_base_units() != -positive.to_base_units()

    for target in CONVERSION_TARGETS:
        one = Money.from_base_units(1, asset)
        half_rate = _half_unit_rate(asset, target)
        converted = one.convert(target, half_rate, rounding=rounding)
        negated = (-one).convert(target, half_rate, rounding=rounding)
        assert converted.asset == target
        assert negated.to_base_units() != -converted.to_base_units()
        if rounding == ROUND_FLOOR:
            assert converted.to_base_units() == 0
            assert negated.to_base_units() == -1
        else:
            assert converted.to_base_units() == 1
            assert negated.to_base_units() == 0


def test_ordering_follows_base_units(asset, base_units):
    monies = [Money.from_base_units(units, asset) for units in sorted(base_units)]
    assert monies == sorted(monies)
    for smaller, larger in zip(monies, monies[1:]):
        assert smaller < larger
        assert smaller <= larger
        assert larger > smaller
        assert smaller != larger


def test_every_amount_carries_the_asset_precision(asset, amounts):
    for amount in amounts:
        money = Money(amount, asset)
        assert money.amount.as_tuple().exponent == -asset.decimals


def test_equal_amounts_hash_and_print_alike(asset, base_units):
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        trimmed = Money(money.format(symbol=False, trim=True), asset)
        assert trimmed == money
        assert hash(trimmed) == hash(money)
        assert len({money, trimmed}) == 1
        assert str(trimmed) == str(money)
        assert trimmed.amount.as_tuple() == money.amount.as_tuple()


def test_parse_money_uses_the_registry_it_is_given(asset):
    own = AssetRegistry([asset])
    money = Money.from_base_units(1, asset)
    assert parse_money(str(money), assets=own) == money
    with pytest.raises(UnknownAsset):
        parse_money(f"1 NOT{asset.symbol}", assets=own)


def test_shortened_text_truncates_towards_zero(asset, base_units):
    places = asset.decimals - 2
    step = 10 ** (asset.decimals - places)
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        text = money.format(symbol=False, decimals=places, rounding=ROUND_DOWN)
        shortened = parse_amount(text, asset).to_base_units()
        assert abs(shortened - units) < step
        assert abs(shortened) <= abs(units)
