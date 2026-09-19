"""Invariants that hold for every registered asset, whatever the amount."""

from __future__ import annotations

from decimal import ROUND_DOWN

import pytest

from cryptomoney import (
    ASSETS,
    AssetRegistry,
    Money,
    UnknownAsset,
    parse_amount,
    parse_money,
)


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


def test_ordering_follows_base_units(asset, base_units):
    monies = [Money.from_base_units(units, asset) for units in sorted(base_units)]
    assert monies == sorted(monies)
    for smaller, larger in zip(monies, monies[1:]):
        assert smaller < larger
        assert smaller <= larger
        assert larger > smaller
        assert smaller != larger


def test_equal_amounts_hash_alike(asset, base_units):
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        trimmed = Money(money.format(symbol=False, trim=True), asset)
        assert trimmed == money
        assert hash(trimmed) == hash(money)
        assert len({money, trimmed}) == 1


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
