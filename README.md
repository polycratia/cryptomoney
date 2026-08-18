# cryptomoney

Crypto amounts without float bugs: decimal money, per-asset precision, satoshi
and wei units, parsing and formatting.

## Status

The core value objects (`Asset`, `Money`) and the asset registry are
implemented. Unit helpers (satoshi, wei), parsing and formatting are not there
yet.

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
