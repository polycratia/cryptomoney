"""Round trips between amounts, base units and text, for every registered asset."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from cryptomoney import (
    BTC,
    ETH,
    CurrencyMismatch,
    Money,
    from_satoshi,
    from_wei,
    parse_amount,
    parse_money,
    to_satoshi,
    to_wei,
)

FORMATS = [
    {},
    {"trim": True},
    {"group": True},
    {"trim": True, "group": True},
    {"plus": True},
]
FORMAT_IDS = ["plain", "trim", "group", "trim-group", "plus"]

SATOSHI_CASES = [0, 1, -1, 12_345_678, 99_999_999, 100_000_000, 2_100_000_000_000_000]
WEI_CASES = [0, 1, -1, 10**18 - 1, 10**18, 123_456_789_012_345_678_901]


def _scaled(amount: Decimal, scale: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 200
        return amount * scale


def test_base_units_round_trip(asset, base_units):
    for units in base_units:
        money = Money.from_base_units(units, asset)
        assert money.asset == asset
        assert money.to_base_units() == units


def test_amount_round_trip(asset, amounts):
    for amount in amounts:
        money = Money(amount, asset)
        restored = Money.from_base_units(money.to_base_units(), asset)
        assert restored == money
        assert restored.amount == amount
        assert restored.to_base_units() == money.to_base_units()


def test_base_units_are_the_amount_times_the_scale(asset, amounts):
    scale = 10**asset.decimals
    for amount in amounts:
        scaled = _scaled(amount, scale)
        assert scaled == scaled.to_integral_value()
        assert Money(amount, asset).to_base_units() == int(scaled)


@pytest.mark.parametrize("options", FORMATS, ids=FORMAT_IDS)
def test_format_then_parse(asset, amounts, options):
    for amount in amounts:
        money = Money(amount, asset)
        number = money.format(symbol=False, **options)
        assert "e" not in number.lower()
        assert parse_amount(number, asset) == money
        assert parse_money(money.format(**options)) == money


def test_str_round_trip(asset, amounts):
    for amount in amounts:
        money = Money(amount, asset)
        assert parse_money(str(money)) == money


def test_exponent_text_round_trip(asset, base_units):
    for units in base_units:
        money = parse_amount(f"{units}E-{asset.decimals}", asset)
        assert money.to_base_units() == units
        assert money == Money.from_base_units(units, asset)


def test_symbol_placement_round_trip(asset):
    money = Money.from_base_units(12_345, asset)
    number = money.format(symbol=False)
    assert parse_money(f"{number} {asset.symbol}") == money
    assert parse_money(f"{asset.symbol} {number}") == money
    assert parse_money(f"{number}{asset.symbol}") == money
    assert parse_money(f"{number}{asset.symbol.lower()}") == money


def test_addition_round_trip(asset, base_units):
    step = Money.from_base_units(7, asset)
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        assert (money + step) - step == money
        assert ((money + step) - step).to_base_units() == units


def test_multiply_then_divide_round_trip(asset, base_units):
    for units in base_units[:40]:
        money = Money.from_base_units(units, asset)
        scaled = money.multiply(7, rounding=ROUND_DOWN)
        assert scaled.to_base_units() == units * 7
        assert scaled.divide(7, rounding=ROUND_DOWN) == money


@pytest.mark.parametrize("parts", [1, 2, 3, 7, 100])
def test_split_conserves_the_total(asset, base_units, parts):
    for units in base_units[:20]:
        money = Money.from_base_units(units, asset)
        shares = money.split(parts)
        assert len(shares) == parts
        sizes = [share.to_base_units() for share in shares]
        assert sum(sizes) == units
        assert max(sizes) - min(sizes) <= 1
        total = shares[0]
        for share in shares[1:]:
            total = total + share
        assert total == money


def test_satoshi_round_trip():
    for units in SATOSHI_CASES:
        money = from_satoshi(units)
        assert money.asset == BTC
        assert to_satoshi(money) == units
        assert from_satoshi(to_satoshi(money)) == money


def test_wei_round_trip():
    for units in WEI_CASES:
        money = from_wei(units)
        assert money.asset == ETH
        assert to_wei(money) == units
        assert from_wei(to_wei(money)) == money


def test_named_units_refuse_other_assets():
    with pytest.raises(CurrencyMismatch):
        to_satoshi(Money("1", ETH))
    with pytest.raises(CurrencyMismatch):
        to_wei(Money("1", BTC))
