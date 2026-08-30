# cryptomoney

Crypto amounts without float bugs: decimal money, per-asset precision, satoshi
and wei units, parsing and formatting.

## Status

The core value objects (`Asset`, `Money`), the asset registry, arithmetic, base
unit conversion, parsing and formatting are implemented.

## Usage

```python
from decimal import Decimal

from cryptomoney import BTC, Money

balance = Money(Decimal("0.5"), BTC)
fee = Money("0.000125", BTC)

print(balance - fee)  # 0.499875 BTC
print(3 * fee)        # 0.000375 BTC
```

`Money` is immutable, hashable and bound to one asset. Floats are refused at
construction, so rounding errors cannot enter a balance:

```python
Money(0.1, BTC)                  # TypeError: float is refused
Money("0.000000001", BTC)        # ValueError: BTC is divisible into 8 decimal places
Money("1", BTC) + Money("1", ETH)  # CurrencyMismatch
```

## Arithmetic

Sums and comparisons stay within one asset: mixing two assets raises
`CurrencyMismatch` instead of producing a number that means nothing. Addition,
subtraction and multiplication by a whole number are exact, so they are plain
operators. Anything that may not fit the asset's precision asks for its
rounding mode and has no default:

```python
from decimal import ROUND_DOWN, ROUND_HALF_UP

from cryptomoney import BTC, Money

Money("0.5", BTC) / 3                                      # TypeError: / is refused
Money("0.5", BTC).divide(3, rounding=ROUND_DOWN)           # 0.16666666 BTC
Money("1", BTC).multiply("0.015", rounding=ROUND_HALF_UP)  # 0.01500000 BTC
```

The result is quantized to the asset's precision with the mode you passed, so
nothing is ever trimmed behind your back. When the whole amount has to survive
the division, `split` works in base units and hands the remainder to the first
shares:

```python
shares = Money("0.00000010", BTC).split(3)
[str(share) for share in shares]   # ['0.00000004 BTC', '0.00000003 BTC', '0.00000003 BTC']
sum(shares[1:], shares[0])         # 0.00000010 BTC
```

## Assets

An `Asset` is a symbol plus the number of decimal places it is divisible into:
BTC has 8, ETH has 18, USDT has 6. The package ships a registry of common
assets, available both as constants and by symbol:

```python
from cryptomoney import ASSETS, ETH

ASSETS.get("ETH") is ETH   # True
"USDT" in ASSETS           # True
sorted(ASSETS.symbols())   # ['BNB', 'BTC', 'DOGE', 'ETH', 'LTC', 'SOL', 'USDC', 'USDT']
```

The defaults are a convenience, not a source of truth: the same ticker can have
different precision on different chains. Build your own registry when that
matters:

```python
from cryptomoney import ASSETS, Asset, AssetRegistry

assets = ASSETS.copy()
assets.register(Asset("USDT", 18), replace=True)  # USDT on BNB Smart Chain
assets.register(Asset("XMR", 12))

own = AssetRegistry([Asset("POINTS", 0)])         # or start from nothing
```

Looking up a symbol that is not registered raises `UnknownAsset`.

## Base units

Chain APIs speak integers: satoshi, wei, the smallest unit an asset is
divisible into. Conversion goes both ways and is exact:

```python
from cryptomoney import BTC, USDT, Money, from_wei, to_satoshi

to_satoshi(Money("0.5", BTC))            # 50000000
from_wei(1)                              # 0.000000000000000001 ETH

Money("12.5", USDT).to_base_units()      # 12500000
Money.from_base_units(12500000, USDT)    # 12.500000 USDT
```

An amount finer than its asset cannot be constructed in the first place, so a
conversion never has a remainder to round away. `to_base_units()` and
`from_base_units()` work for any asset; `to_satoshi`, `from_satoshi`, `to_wei`
and `from_wei` are the named shorthands for BTC and ETH.

## Parsing

`parse_amount` reads one amount of an asset you already know, `parse_money`
also reads the symbol. Both take untrusted text: surrounding whitespace, a
leading sign, thousands separators and exponent notation are accepted, and the
symbol may come before, after or attached to the number:

```python
from cryptomoney import BTC, USDT, parse_amount, parse_money

parse_amount("0.5", BTC)          # 0.5 BTC
parse_amount(" 1 234.50 ", USDT)  # 1234.50 USDT
parse_amount("1.25e3", USDT)      # 1250 USDT
parse_money("0.5 BTC")            # 0.5 BTC
parse_money("12.5btc")            # 12.5 BTC
parse_money("BTC 0.5")            # 0.5 BTC
```

Text that does not describe exactly one amount raises `ParseError`, and an
amount finer than its asset is not rounded unless you say how:

```python
from decimal import ROUND_DOWN

parse_amount("1e-9", BTC)                       # ParseError: needs 9 decimal places
parse_amount("1e-9", BTC, rounding=ROUND_DOWN)  # 0.00000000 BTC
parse_amount("NaN", BTC)                        # ParseError
parse_amount(0.5, BTC)                          # TypeError: float is refused
parse_money("0.5 XMR")                          # UnknownAsset
```

`parse_money` looks the symbol up in `ASSETS` by default; pass `assets=` to use
your own registry. Input longer than 256 characters and exponents beyond ±64
are refused before any arithmetic happens, so a hostile string cannot become a
Decimal with millions of digits.

## Formatting

`format()` renders an amount as fixed point text. A wei amount never comes out
as `1E-18` and a large balance never turns into `1.2345E+7`:

```python
from decimal import ROUND_DOWN

from cryptomoney import BTC, USDT, Money, from_wei

fee = Money("0.00012500", BTC)

fee.format()                                 # '0.00012500 BTC'
fee.format(trim=True)                        # '0.000125 BTC'
fee.format(decimals=4, rounding=ROUND_DOWN)  # '0.0001 BTC'
fee.format(symbol=False)                     # '0.00012500'
str(from_wei(1))                             # '0.000000000000000001 ETH'
Money("1234567.5", USDT).format(group=True)  # '1,234,567.5 USDT'
```

Shortening an amount needs a rounding mode: `fee.format(decimals=4)` raises
instead of dropping digits quietly, and `decimals` cannot ask for more places
than the asset has. `trim=True` drops trailing zeros, `group=True` inserts
thousands separators, `plus=True` keeps the sign on positive amounts and
`symbol=False` leaves the ticker out. `str(money)` is `format()` with its
defaults, and everything it produces can be read back by `parse_money`.

## Installation

```bash
pip install cryptomoney
```

## Development

```bash
pip install -e .
```

## License

MIT, see [LICENSE](LICENSE).

Maintained by [polycratia](https://polycratia.com).
