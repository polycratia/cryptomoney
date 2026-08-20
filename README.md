# cryptomoney

Crypto amounts without float bugs: decimal money, per-asset precision, satoshi
and wei units, parsing and formatting.

## Status

The core value objects (`Asset`, `Money`), the asset registry and base unit
conversion are implemented. Parsing and formatting are not there yet.

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
