# cryptomoney

Crypto amounts without float bugs: decimal money, per-asset precision, satoshi
and wei units, parsing and formatting.

## Status

The core value objects (`Asset`, `Money`) are implemented. Unit helpers
(satoshi, wei), parsing and formatting are not there yet.

## Usage

```python
from decimal import Decimal

from cryptomoney import Asset, Money

BTC = Asset("BTC", 8)

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
Money("1", BTC) + Money("1", Asset("ETH", 18))  # CurrencyMismatch
```

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
