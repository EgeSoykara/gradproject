import json
from datetime import date
from pathlib import Path

from django.conf import settings

from portfolio.services.valuation import MarketBook, snapshot

from .models import DashboardPreferences

MOCK_DIR = Path(__file__).resolve().parent / 'mock'
METAL_SYMBOLS = {'XAU': 'GOLD', 'XAG': 'SILVER', 'XPT': 'PLATINUM'}


class DashboardUnavailable(Exception):
    pass


def mock_choices():
    return [('example', 'example.json')] + [
        (f'persona_{number}', f'persona_{number}.json')
        for number in range(1, 5)
        if (MOCK_DIR / f'persona_{number}.json').is_file()
    ]


def load_dashboard(user, lang, *, currency=None, profile=None, portfolio=None, fixture='example'):
    if settings.USE_MOCK_DASHBOARD:
        filename = dict(mock_choices()).get(fixture)
        if filename is None:
            raise DashboardUnavailable('Unknown example file.')
        try:
            payload = json.loads((MOCK_DIR / filename).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise DashboardUnavailable('Example data could not be loaded.') from exc
        if not isinstance(payload, dict):
            raise DashboardUnavailable('Expected a JSON object.')
        return payload

    try:
        from service_bridge import get_dashboard
    except ImportError as exc:
        raise DashboardUnavailable('The analysis service is unavailable.') from exc

    preferences = DashboardPreferences.objects.filter(user=user).first()
    currency = currency or (preferences.currency if preferences else 'TRY')
    profile = profile or (preferences.profile if preferences else 'balanced')
    portfolios = user.portfolio_set.order_by('id')
    if portfolio is None:
        portfolio = portfolios.first()
    elif portfolio.user_id != user.pk:
        raise DashboardUnavailable('Portfolio unavailable.')

    holdings, cash, contributions = [], 0.0, None
    if portfolio and portfolio.transactions.exists():
        book = MarketBook(portfolio.dataset)
        day = date.today()
        state = snapshot(portfolio, 'TRY', day, book)
        holdings = [
            {
                'symbol': METAL_SYMBOLS.get(item['asset'].symbol, item['asset'].symbol),
                'shares': float(item['quantity']),
                'price': float(item['value'] / item['quantity']),
            }
            for item in state['holdings']
        ]
        cash = float(state['cash'] / book.rate(currency, day))
        rows = list(portfolio.transactions.select_related('asset').filter(date__lte=day))
        # The published bridge accepts only the legacy buy/deposit history.
        if all(row.kind == 'deposit' or (row.kind == 'buy' and row.asset.kind == 'fund') for row in rows):
            contributions = [
                {
                    'date': row.date.isoformat(),
                    'symbol': row.asset.symbol if row.asset else 'CASH',
                    'amount_tl': float(row.quantity * row.price * row.fx_to_try),
                }
                for row in rows
            ] or None
    return get_dashboard(
        holdings=holdings,
        cash=cash,
        monthly_contribution=float(preferences.monthly_contribution) if preferences else 0.0,
        profile=profile,
        base_currency=currency,
        lang=lang,
        contributions=contributions,
    )
