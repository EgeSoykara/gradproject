from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.db import transaction
from django.utils import timezone

from portfolio.models import Asset, ExchangeRate, Note, Portfolio, Price, Transaction

from .ledger import replay
from .providers import import_articles

CATALOG = [
    ('DEMO-EQ', 'Equity Growth Fund', 'fund', 'TRY', 'units', 2.4, 0.00055, 0.012),
    ('DEMO-MM', 'Money Market Fund', 'fund', 'TRY', 'units', 1.2, 0.0004, 0.0002),
    ('DEMO-BD', 'Balanced Fund', 'fund', 'TRY', 'units', 1.8, 0.0004, 0.006),
    ('XAU', 'Gold', 'metal', 'TRY', 'grams', 290, 0.0007, 0.01),
    ('XAG', 'Silver', 'metal', 'TRY', 'grams', 3.4, 0.0006, 0.016),
    ('XPT', 'Platinum', 'metal', 'TRY', 'grams', 170, 0.0003, 0.013),
    ('SP500', 'S&P 500', 'benchmark', 'USD', 'index', 3200, 0.00035, 0.011),
    ('NASDAQ100', 'NASDAQ 100', 'benchmark', 'USD', 'index', 8700, 0.0005, 0.015),
    ('BTC', 'Bitcoin', 'benchmark', 'USD', 'coins', 7200, 0.0007, 0.028),
]

# Preserve the first shipped dataset exactly. Extension streams use separate seeds,
# so adding a later day never changes the random draws for an earlier observation.
DEMO_ANCHOR_END = date(2026, 10, 1)


def synthetic_history(end):
    anchor = pd.bdate_range('2019-12-02', DEMO_ANCHOR_END).date
    extra = pd.bdate_range(DEMO_ANCHOR_END + timedelta(days=1), end).date
    days = np.concatenate([anchor, extra])
    rng = np.random.default_rng(42)
    common = np.concatenate(
        [
            rng.normal(0, 1, len(anchor)),
            np.random.default_rng(8000).normal(0, 1, len(extra)),
        ]
    )
    paths = {}
    for index, (symbol, _, kind, _, _, initial, drift, vol) in enumerate(CATALOG):
        independent = np.concatenate(
            [
                rng.normal(0, 1, len(anchor)),
                np.random.default_rng(9000 + index).normal(0, 1, len(extra)),
            ]
        )
        changes = drift + vol * (0.45 * common + 0.89 * independent)
        if symbol != 'DEMO-MM':
            for i, day in enumerate(days):
                if date(2020, 2, 20) <= day <= date(2020, 3, 23):
                    changes[i] -= 0.006 if kind != 'metal' else 0.002
                if date(2022, 1, 3) <= day <= date(2022, 10, 12):
                    changes[i] -= 0.0012 if kind != 'metal' else 0.0003
        values = initial * np.exp(np.cumsum(changes))
        paths[symbol] = [
            (d, Decimal(str(round(float(p), 8)))) for d, p in zip(days, values) if d <= end
        ]
    rates = {}
    for index, (currency, initial) in enumerate([('USD', 5.8), ('EUR', 6.4), ('GBP', 7.6)]):
        changes = np.concatenate(
            [
                rng.normal(0, 0.0018, len(anchor)),
                np.random.default_rng(10000 + index).normal(0, 0.0018, len(extra)),
            ]
        )
        values = initial * np.exp(np.cumsum(0.00085 + changes))
        rates[currency] = [
            (d, Decimal(str(round(float(p), 8)))) for d, p in zip(days, values) if d <= end
        ]
    return paths, rates


@transaction.atomic
def seed_market():
    """Synthetic seeded paths; symbols with DEMO are fictional, never TEFAS quotes."""
    paths, fx_paths = synthetic_history(date.today())
    prices = []
    for symbol, name, kind, currency, unit, initial, drift, vol in CATALOG:
        asset, _ = Asset.objects.get_or_create(
            symbol=symbol, defaults={'name': name, 'kind': kind, 'currency': currency, 'unit': unit}
        )
        prices.extend(
            Price(
                asset=asset,
                date=d,
                close=p,
                dataset='demo',
                source='Synthetic seeded dataset v1',
            )
            for d, p in paths[symbol]
        )
    Price.objects.bulk_create(prices, ignore_conflicts=True, batch_size=500)
    rates = []
    for currency, values in fx_paths.items():
        rates.extend(
            ExchangeRate(
                currency=currency,
                date=d,
                try_per_unit=p,
                dataset='demo',
                source='Synthetic seeded dataset v1',
            )
            for d, p in values
        )
    ExchangeRate.objects.bulk_create(rates, ignore_conflicts=True, batch_size=500)
    now = timezone.now()
    headlines = [
        'Sample briefing: investors weigh growth against inflation uncertainty',
        'Sample briefing: diversification across funds and metals explained',
        'Sample briefing: understanding currency effects on portfolio returns',
        'Sample briefing: why past performance needs a careful benchmark',
    ]
    import_articles(
        [
            {
                'id': f'demo-news-{i}',
                'title': text,
                'source': 'Learning desk · fictional',
                'published_at': (now - timedelta(hours=i * 4)).isoformat(),
            }
            for i, text in enumerate(headlines)
        ],
        dataset='demo',
    )
    posts = [
        'Strong growth and excellent profits are encouraging.',
        'Losses and uncertainty worry investors.',
        'Markets open for trading today.',
        'The outlook is positive and confidence is improving.',
        'Terrible losses create fear and panic.',
        'The quarterly report was published.',
        'A good recovery brings renewed optimism.',
        'Risk is high and performance is disappointing.',
        'The fund holds gold and bonds.',
        'I love the strong, stable results.',
    ]
    import_articles(
        [
            {
                'id': f'demo-social-{i}',
                'title': t,
                'source': 'Synthetic social sample',
                'published_at': (now - timedelta(minutes=i * 15)).isoformat(),
            }
            for i, t in enumerate(posts)
        ],
        dataset='demo',
        kind='social',
    )
    return len(prices), len(rates)


@transaction.atomic
def create_demo_portfolio(user):
    existing = Portfolio.objects.filter(user=user, dataset='demo').first()
    if existing:
        return existing
    p = Portfolio.objects.create(user=user, name='Learning portfolio', dataset='demo')
    first = date.today() - timedelta(days=365)
    while first.weekday() > 4:
        first += timedelta(days=1)
    Transaction.objects.create(
        portfolio=p, date=first, kind='deposit', price=200000, memo='Sample opening deposit'
    )
    for symbol, budget in [
        ('DEMO-EQ', 50000),
        ('DEMO-MM', 35000),
        ('DEMO-BD', 30000),
        ('XAU', 45000),
        ('XAG', 15000),
    ]:
        asset = Asset.objects.get(symbol=symbol)
        close = (
            Price.objects.filter(asset=asset, dataset='demo', date__lte=first).latest('date').close
        )
        quantity = (Decimal(budget) / close).quantize(Decimal('.0001'))
        Transaction.objects.create(
            portfolio=p, asset=asset, date=first, kind='buy', quantity=quantity, price=close, fee=10
        )
    Transaction.objects.create(
        portfolio=p,
        date=first + timedelta(days=170),
        kind='deposit',
        price=25000,
        memo='Sample additional contribution',
    )
    replay(p.transactions.select_related('asset'))
    Note.objects.create(
        portfolio=p,
        title='My quarterly review',
        body='Review the equity and precious-metal allocation. Compare risk-adjusted returns before changing the portfolio. This is a demonstration note.',
    )
    return p
