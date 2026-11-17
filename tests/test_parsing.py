"""Untrusted text read into amounts: the edges and the refusals."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal

import pytest

from cryptomoney import (
    BTC,
    USDT,
    Asset,
    AssetRegistry,
    Money,
    ParseError,
    UnknownAsset,
    parse_amount,
    parse_money,
)
from cryptomoney.parsing import _MAX_EXPONENT, _MAX_LENGTH

COARSE = Asset("POINTS", 0)

# Every separator the integer part accepts between its groups of three digits.
GROUPED = (
    "1 234.5",
    "1_234.5",
    "1,234.5",
    "1'234.5",
    "1\u00a0234.5",
    "1\u202f234.5",
)

# Separators that do not describe groups of three digits, or sit in the fraction.
MIS_GROUPED = (
    "1,23",
    "12,3456",
    "1234,567",
    "1,234,56",
    ",234",
    "1,",
    "1 2",
    "0.123 456",
    "0 .5",
)

NO_DIGITS = ("", "   ", "+", "-", ".", "-.", "e5", "E-3", "+-1", "--1", "1-", "1.2.3")

MALFORMED_EXPONENTS = ("1e", "1e+", "1E1.5", "1e 5", "1ee5", "1e--5")

NOT_ONE_AMOUNT_AND_SYMBOL = (
    "",
    "   ",
    "0.5",
    "BTC",
    "-BTC",
    "BTC0.5",
    "0.5 BTC BTC",
    "0.5 0.5 BTC",
    "0.5 BTC/USDT",
    "5 BTC 5",
)


def test_parse_error_is_a_value_error():
    assert issubclass(ParseError, ValueError)
    assert issubclass(UnknownAsset, KeyError)


@pytest.mark.parametrize("text", GROUPED)
def test_grouped_integers_drop_their_separators(text):
    assert parse_amount(text, USDT) == Money("1234.5", USDT)
    assert parse_amount(f"-{text}", USDT) == Money("-1234.5", USDT)


@pytest.mark.parametrize("text", MIS_GROUPED)
def test_separators_outside_groups_of_three_are_refused(text):
    with pytest.raises(ParseError):
        parse_amount(text, USDT)


@pytest.mark.parametrize("text", NO_DIGITS)
def test_text_without_digits_is_refused(text):
    with pytest.raises(ParseError):
        parse_amount(text, BTC)


def test_surrounding_whitespace_is_the_only_padding_allowed():
    assert parse_amount("\t 0.5\n", BTC) == Money("0.5", BTC)
    assert parse_amount(" -0.5 ", BTC) == Money("-0.5", BTC)
    # A missing integer part is read as a zero, a missing fraction is not.
    assert parse_amount(".5", BTC) == Money("0.5", BTC)
    assert parse_amount("-.5", BTC) == Money("-0.5", BTC)
    with pytest.raises(ParseError):
        parse_amount("5.", BTC)


def test_exponent_notation_is_read_in_every_accepted_shape():
    assert parse_amount("1.25e3", USDT) == Money("1250", USDT)
    assert parse_amount("1.25E+3", USDT) == Money("1250", USDT)
    assert parse_amount("125e-2", USDT) == Money("1.25", USDT)
    assert parse_amount("+1,234.5e2", USDT) == Money("123450", USDT)
    assert parse_amount(".5e1", USDT) == Money("5", USDT)


@pytest.mark.parametrize("text", MALFORMED_EXPONENTS)
def test_malformed_exponents_are_refused(text):
    with pytest.raises(ParseError):
        parse_amount(text, USDT)


def test_the_exponent_range_is_read_from_the_value_not_the_text():
    assert parse_amount(f"1E{_MAX_EXPONENT}", BTC).amount == Decimal(1).scaleb(
        _MAX_EXPONENT
    )
    assert parse_amount(f"1E+0{_MAX_EXPONENT}", BTC).amount == Decimal(1).scaleb(
        _MAX_EXPONENT
    )
    with pytest.raises(ParseError, match="exponent"):
        parse_amount(f"1E{_MAX_EXPONENT + 1}", BTC)
    with pytest.raises(ParseError, match="exponent"):
        parse_amount(f"1E+00{_MAX_EXPONENT + 1}", BTC)
    # The exponent is refused before the precision is looked at, so a rounding
    # mode does not buy a way past it.
    with pytest.raises(ParseError, match="exponent"):
        parse_amount(f"1E-{_MAX_EXPONENT + 1}", BTC)
    with pytest.raises(ParseError, match="exponent"):
        parse_amount(f"1E-{_MAX_EXPONENT + 1}", BTC, rounding=ROUND_DOWN)
    with pytest.raises(ParseError, match="exponent"):
        parse_amount("1E" + "9" * 100, BTC)


def test_the_length_limit_counts_the_text_as_it_arrives():
    assert parse_amount("0.5".rjust(_MAX_LENGTH), BTC) == Money("0.5", BTC)
    with pytest.raises(ParseError, match="longer than"):
        parse_amount("0.5".rjust(_MAX_LENGTH + 1), BTC)
    assert parse_money("0.5 BTC".rjust(_MAX_LENGTH)) == Money("0.5", BTC)
    with pytest.raises(ParseError, match="longer than"):
        parse_money("0.5 BTC".rjust(_MAX_LENGTH + 1))


def test_a_long_mantissa_keeps_every_digit_it_is_allowed():
    # 200 ones shifted down by 64 places: 136 of them land above the point and
    # ROUND_DOWN keeps the 8 that BTC is divisible into.
    money = parse_amount(f"{'1' * 200}E-{_MAX_EXPONENT}", BTC, rounding=ROUND_DOWN)
    assert money.to_base_units() == int("1" * 144)


@pytest.mark.parametrize(
    "text", ["0", "-0", "+0", "0.0", "-0.0", "0E-8", "-0E+3", ".0"]
)
def test_zero_in_any_shape_is_plain_zero(text):
    money = parse_amount(text, BTC)
    assert money.is_zero
    assert money.to_base_units() == 0
    assert money.format(symbol=False) == "0.00000000"
    assert money.amount.as_tuple() == Money.zero(BTC).amount.as_tuple()


def test_trailing_zeros_count_as_decimal_places():
    # The places asked for are the ones written, not the ones that carry a digit,
    # so text finer than the asset needs a mode even when nothing is lost.
    with pytest.raises(ParseError, match="needs 11 decimal places"):
        parse_amount("0.50000000000", BTC)
    assert parse_amount("0.50000000000", BTC, rounding=ROUND_DOWN) == Money("0.5", BTC)
    with pytest.raises(ParseError, match="needs 9 decimal places"):
        parse_amount("0." + "0" * 9, BTC)
    assert parse_amount("0." + "0" * 9, BTC, rounding=ROUND_DOWN).is_zero


def test_text_at_the_asset_precision_needs_no_mode(asset):
    finest = f"1E-{asset.decimals}"
    assert parse_amount(finest, asset) == Money.from_base_units(1, asset)
    assert parse_amount(f"-{finest}", asset) == Money.from_base_units(-1, asset)
    with pytest.raises(ParseError, match="rounding"):
        parse_amount(f"1E-{asset.decimals + 1}", asset)


def test_a_mode_is_ignored_when_the_text_already_fits(asset):
    text = Money.from_base_units(7, asset).format(symbol=False)
    assert parse_amount(text, asset, rounding=ROUND_UP) == parse_amount(text, asset)


def test_an_asset_without_decimals_needs_a_mode_for_any_fraction():
    with pytest.raises(ParseError, match="POINTS"):
        parse_amount("0.5", COARSE)
    assert parse_amount("0.5", COARSE, rounding=ROUND_HALF_UP).to_base_units() == 1
    assert parse_amount("0.5", COARSE, rounding=ROUND_DOWN).to_base_units() == 0
    assert parse_amount("2.4", COARSE, rounding=ROUND_UP).to_base_units() == 3
    assert parse_amount("1e2", COARSE) == Money("100", COARSE)


def test_values_that_are_not_text_are_refused():
    for value in (0.5, 1, Decimal("0.5"), True, None, b"0.5", ["0.5"]):
        with pytest.raises(TypeError):
            parse_amount(value, BTC)
        with pytest.raises(TypeError):
            parse_money(value)


def test_the_asset_and_the_registry_are_type_checked():
    with pytest.raises(TypeError):
        parse_amount("1", "BTC")
    with pytest.raises(TypeError):
        parse_amount("1", BTC.decimals)
    with pytest.raises(TypeError):
        parse_money("1 BTC", assets=[BTC])
    with pytest.raises(TypeError):
        parse_money("1 BTC", assets=BTC)


def test_the_rounding_mode_is_checked_before_the_text():
    with pytest.raises(TypeError):
        parse_amount("0.5", BTC, rounding=1)
    with pytest.raises(TypeError):
        parse_money("0.5 BTC", rounding=1)
    for text in ("not an amount", "1" * (_MAX_LENGTH + 1)):
        with pytest.raises(ValueError, match="unknown rounding mode") as excinfo:
            parse_amount(text, BTC, rounding="ROUND_SOMEHOW")
        assert not isinstance(excinfo.value, ParseError)
    with pytest.raises(ValueError, match="unknown rounding mode"):
        parse_money("not an amount", rounding="round_down")


def test_the_symbol_may_lead_trail_or_be_attached(asset):
    money = Money.from_base_units(12_345, asset)
    number = money.format(symbol=False)
    assert parse_money(f"{number} {asset.symbol}") == money
    assert parse_money(f"  {asset.symbol}   {number} ") == money
    assert parse_money(f"{number}{asset.symbol}") == money
    assert parse_money(f"{number}{asset.symbol.lower()}") == money


@pytest.mark.parametrize("text", NOT_ONE_AMOUNT_AND_SYMBOL)
def test_text_that_is_not_one_amount_and_one_symbol_is_refused(text):
    with pytest.raises(ParseError):
        parse_money(text)


def test_the_last_word_is_read_as_the_symbol():
    with pytest.raises(UnknownAsset):
        parse_money("0.5 XMR")
    with pytest.raises(UnknownAsset):
        parse_money("0.5xmr")
    # A trailing word is taken for the symbol rather than ignored, so a sentence
    # fails on the lookup instead of parsing its first amount.
    with pytest.raises(UnknownAsset):
        parse_money("0.5 BTC extra")


def test_the_registry_given_is_the_only_one_consulted():
    own = AssetRegistry([COARSE])
    assert parse_money("5 POINTS", assets=own) == Money("5", COARSE)
    assert parse_money("5 points", assets=own) == Money("5", COARSE)
    with pytest.raises(UnknownAsset):
        parse_money("0.5 BTC", assets=own)

    # A symbol is tried as written and then upper cased, so a mixed case symbol
    # is found by its own spelling only.
    mixed = AssetRegistry([Asset("wBTC", 8)])
    assert parse_money("1 wBTC", assets=mixed).asset.symbol == "wBTC"
    with pytest.raises(UnknownAsset):
        parse_money("1 wbtc", assets=mixed)


def test_parse_money_hands_the_rounding_mode_to_the_amount(asset):
    text = f"1E-{asset.decimals + 1} {asset.symbol}"
    with pytest.raises(ParseError, match="rounding"):
        parse_money(text)
    assert parse_money(text, rounding=ROUND_UP).to_base_units() == 1
    assert parse_money(text, rounding=ROUND_DOWN).is_zero
    assert parse_money(text, rounding=ROUND_UP).asset == asset
