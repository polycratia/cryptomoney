"""Deterministic fixtures shared by the cryptomoney tests."""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from cryptomoney import ASSETS, Asset, Money

SEED = 20260916

REGISTERED_ASSETS = tuple(sorted(ASSETS, key=lambda asset: asset.symbol))
ASSET_IDS = tuple(asset.symbol for asset in REGISTERED_ASSETS)


def _stream(asset: Asset) -> random.Random:
    # Seeded per asset, so a case that fails once comes back on the next run.
    return random.Random(f"{SEED}:{asset.symbol}:{asset.decimals}")


def base_unit_cases(asset: Asset, count: int = 120) -> list[int]:
    """Base unit counts around the interesting boundaries, plus a seeded spread."""
    scale = 10**asset.decimals
    cases = [
        0,
        1,
        -1,
        2,
        -2,
        9,
        10,
        scale - 1,
        scale,
        scale + 1,
        -scale - 1,
        -scale,
        -scale + 1,
        10 * scale,
        10 * scale - 1,
        21_000_000 * scale,
    ]
    stream = _stream(asset)
    bound = scale * 10**6
    for _ in range(count):
        cases.append(stream.randrange(-bound, bound + 1))
    for _ in range(count // 4):
        cases.append(stream.randrange(-999, 1000))
    return list(dict.fromkeys(cases))


def amount_cases(asset: Asset) -> list[Decimal]:
    """Decimals an amount of ``asset`` can legitimately hold."""
    amounts = [
        Money.from_base_units(units, asset).amount
        for units in base_unit_cases(asset, count=40)
    ]
    amounts += [Decimal(0), Decimal(1), Decimal(-1), Decimal("1E+5"), Decimal("-1E+3")]
    if asset.decimals >= 2:
        amounts += [Decimal("123.45"), Decimal("-0.05")]
    if asset.decimals >= 6:
        amounts.append(Decimal("0.000001"))
    return amounts


@pytest.fixture(params=REGISTERED_ASSETS, ids=ASSET_IDS)
def asset(request: pytest.FixtureRequest) -> Asset:
    return request.param


@pytest.fixture
def base_units(asset: Asset) -> list[int]:
    return base_unit_cases(asset)


@pytest.fixture
def amounts(asset: Asset) -> list[Decimal]:
    return amount_cases(asset)
