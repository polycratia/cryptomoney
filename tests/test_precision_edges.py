"""Behaviour at the edges of an asset's decimal precision."""

from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)

import pytest

from cryptomoney import (
    BTC,
    ETH,
    USDT,
    Asset,
    Money,
    ParseError,
    from_satoshi,
    from_wei,
    parse_amount,
)

FINEST = Asset("FINE", 36)
COARSE = Asset("POINTS", 0)


def test_asset_precision_has_an_upper_bound():
    assert Asset("FINE", 36).decimals == 36
    with pytest.raises(ValueError):
        Asset("TOOFINE", 37)


def test_smallest_unit_of_every_asset(asset):
    smallest = Money.from_base_units(1, asset)
    assert smallest.to_base_units() == 1
    assert smallest.amount == Decimal(1).scaleb(-asset.decimals)
    assert smallest.format(symbol=False) == f"0.{'0' * (asset.decimals - 1)}1"


def test_maximum_precision_asset():
    text = f"0.{'0' * 35}1"
    money = Money(text, FINEST)
    assert money.to_base_units() == 1
    assert money.amount == Money.from_base_units(1, FINEST).amount
    assert money.format(symbol=False) == text
    with pytest.raises(ValueError):
        Money(f"0.{'0' * 36}1", FINEST)


def test_asset_without_decimals():
    money = Money("5", COARSE)
    assert money.to_base_units() == 5
    assert money.format() == "5 POINTS"
    assert Money.from_base_units(-3, COARSE).amount == Decimal(-3)
    with pytest.raises(ValueError):
        Money("0.5", COARSE)
    with pytest.raises(ValueError):
        money.format(decimals=1)


def test_amount_finer_than_its_asset_is_refused(asset):
    with pytest.raises(ValueError, match="divisible"):
        Money(Decimal(1).scaleb(-(asset.decimals + 1)), asset)


def test_parse_refuses_extra_precision_without_a_rounding_mode(asset):
    text = f"1E-{asset.decimals + 1}"
    with pytest.raises(ParseError):
        parse_amount(text, asset)
    assert parse_amount(text, asset, rounding=ROUND_DOWN).to_base_units() == 0
    assert parse_amount(text, asset, rounding=ROUND_UP).to_base_units() == 1


def test_rounding_modes_at_half_of_the_smallest_unit(asset):
    half = f"5E-{asset.decimals + 1}"
    expected = {
        ROUND_DOWN: 0,
        ROUND_UP: 1,
        ROUND_FLOOR: 0,
        ROUND_CEILING: 1,
        ROUND_HALF_DOWN: 0,
        ROUND_HALF_EVEN: 0,
        ROUND_HALF_UP: 1,
    }
    for mode, units in expected.items():
        assert parse_amount(half, asset, rounding=mode).to_base_units() == units

    negative = f"-5E-{asset.decimals + 1}"
    assert parse_amount(negative, asset, rounding=ROUND_FLOOR).to_base_units() == -1
    assert parse_amount(negative, asset, rounding=ROUND_CEILING).to_base_units() == 0
    assert parse_amount(negative, asset, rounding=ROUND_HALF_UP).to_base_units() == -1


def test_division_rounds_at_the_last_unit():
    assert Money("1", BTC).divide(3, rounding=ROUND_DOWN).to_base_units() == 33_333_333
    assert Money("1", BTC).divide(3, rounding=ROUND_UP).to_base_units() == 33_333_334
    assert (
        Money("1", BTC).divide(3, rounding=ROUND_HALF_UP).to_base_units() == 33_333_333
    )
    with pytest.raises(ZeroDivisionError):
        Money("1", BTC).divide(0, rounding=ROUND_DOWN)


def test_large_amounts_keep_every_digit():
    money = Money.from_base_units(10**38, ETH)
    quotient = money.divide(3, rounding=ROUND_DOWN)
    assert quotient.to_base_units() == 10**38 // 3
    third = 10**38 // 3
    assert quotient.multiply(3, rounding=ROUND_DOWN).to_base_units() == third * 3


def test_exact_arithmetic_survives_the_padded_precision():
    big = Money.from_base_units(10**38, ETH)
    assert (big + from_wei(1)).to_base_units() == 10**38 + 1
    assert (big - from_wei(1)).to_base_units() == 10**38 - 1
    assert (big * 1000).to_base_units() == 10**41
    assert (-big).to_base_units() == -(10**38)
    assert abs(-big).to_base_units() == 10**38


def test_whole_factors_stay_exact(asset):
    money = Money.from_base_units(123_456_789, asset)
    assert (money * 1000).to_base_units() == 123_456_789_000
    assert money.multiply(1000, rounding=ROUND_DOWN).to_base_units() == 123_456_789_000


def test_format_never_uses_scientific_notation():
    assert str(from_wei(1)) == "0.000000000000000001 ETH"
    assert (
        Money(Decimal("1E+30"), ETH).format(symbol=False)
        == "1" + "0" * 30 + "." + "0" * 18
    )
    assert (
        Money(Decimal("1E+30"), ETH).format(symbol=False, trim=True) == "1" + "0" * 30
    )
    assert (
        Money.from_base_units(10**36, ETH).format(symbol=False)
        == "1" + "0" * 18 + "." + "0" * 18
    )


def test_shortening_and_padding_the_fraction():
    fee = Money("0.00012500", BTC)
    assert fee.format() == "0.00012500 BTC"
    assert fee.format(trim=True) == "0.000125 BTC"
    assert fee.format(decimals=4, rounding=ROUND_DOWN) == "0.0001 BTC"
    assert fee.format(decimals=6) == "0.000125 BTC"
    assert Money("0.5", BTC).format(decimals=8) == "0.50000000 BTC"
    assert Money("0.5", BTC).format(decimals=2) == "0.50 BTC"
    assert Money("1234567.5", USDT).format(group=True) == "1,234,567.500000 USDT"
    assert (
        Money("1234567.5", USDT).format(group=True, trim=True) == "1,234,567.5 USDT"
    )
    assert Money.from_base_units(0, BTC).format(trim=True, symbol=False) == "0"
    with pytest.raises(ValueError):
        fee.format(decimals=4)
    with pytest.raises(ValueError):
        fee.format(decimals=9)


def test_split_hands_the_remainder_to_the_first_shares():
    shares = Money("0.00000010", BTC).split(3)
    assert [share.to_base_units() for share in shares] == [4, 3, 3]
    negative = Money("-0.00000010", BTC).split(3)
    assert [share.to_base_units() for share in negative] == [-4, -3, -3]
    thin = Money.from_base_units(2, BTC).split(5)
    assert [share.to_base_units() for share in thin] == [1, 1, 0, 0, 0]
    assert Money("1.5", BTC).split(1) == [Money("1.5", BTC)]
    with pytest.raises(ValueError):
        Money("1", BTC).split(0)


def test_equal_amounts_share_one_text():
    plain = Money(Decimal("0.5"), BTC)
    padded = Money(Decimal("0.50000000"), BTC)
    satoshi = from_satoshi(50_000_000)
    assert plain == padded == satoshi
    assert hash(plain) == hash(padded) == hash(satoshi)
    assert plain.to_base_units() == padded.to_base_units() == 50_000_000
    assert str(plain) == str(padded) == str(satoshi) == "0.50000000 BTC"
    assert plain.amount.as_tuple() == satoshi.amount.as_tuple()
    assert plain.format(trim=True) == "0.5 BTC"


def test_negative_zero_is_zero():
    money = Money(Decimal("-0.00000000"), BTC)
    assert money.is_zero
    assert money.to_base_units() == 0
    assert money.format(symbol=False) == "0.00000000"
    assert money.amount.as_tuple() == Money.zero(BTC).amount.as_tuple()


@pytest.mark.parametrize("amount", ["1E+2", "1E-8", "12.5E+3", "0E-8"])
def test_exponent_amounts_round_trip(amount):
    money = Money(Decimal(amount), BTC)
    assert Money.from_base_units(money.to_base_units(), BTC) == money
    assert money.amount.as_tuple().exponent == -BTC.decimals


def test_parse_refuses_hostile_input():
    with pytest.raises(ParseError):
        parse_amount("1E65", BTC)
    with pytest.raises(ParseError):
        parse_amount("1E-65", BTC, rounding=ROUND_DOWN)
    with pytest.raises(ParseError):
        parse_amount("1" * 257, BTC)
    with pytest.raises(ParseError):
        parse_amount("NaN", BTC)
    with pytest.raises(ParseError):
        parse_amount("Infinity", BTC)
    assert parse_amount("1E64", BTC).to_base_units() == 10**72


def test_floats_are_refused_everywhere():
    with pytest.raises(TypeError):
        Money(0.1, BTC)
    with pytest.raises(TypeError):
        Money.from_base_units(1.0, BTC)
    with pytest.raises(TypeError):
        parse_amount(0.5, BTC)
    with pytest.raises(TypeError):
        Money("1", BTC).multiply(0.5, rounding=ROUND_DOWN)
