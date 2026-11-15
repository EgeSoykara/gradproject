import json
import logging
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import salted_hmac

from portfolio.services.analytics import portfolio_risk
from portfolio.services.archive import archive_code
from portfolio.services.ledger import replay
from portfolio.services.valuation import MissingData, history, portfolio_book, snapshot

from .models import DashboardPreferences

logger = logging.getLogger(__name__)
MOCK_DIR = Path(__file__).resolve().parent / 'mock'
DEFAULT_FIXTURE = 'persona_1' if (MOCK_DIR / 'persona_1.json').is_file() else 'example'


class DashboardUnavailable(Exception):
    pass


def mock_choices():
    return [('example', 'example.json')] + [
        (f'persona_{number}', f'persona_{number}.json')
        for number in range(1, 5)
        if (MOCK_DIR / f'persona_{number}.json').is_file()
    ]


def mock_profile_reference(profile):
    with (MOCK_DIR / 'profile_reference.json').open(encoding='utf-8') as source:
        return json.load(source)[profile]


def load_dashboard(user, lang, *, currency=None, profile=None, portfolio=None, fixture=None, snap=None):
    if fixture:
        filename = dict(mock_choices()).get(fixture)
        if filename is None:
            raise DashboardUnavailable('Unknown example file.')
        if fixture == 'persona_2' and lang == 'en' and (MOCK_DIR / 'persona_2_en.json').is_file():
            filename = 'persona_2_en.json'
        try:
            payload = json.loads((MOCK_DIR / filename).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            raise DashboardUnavailable('Example data could not be loaded.') from exc
        if not isinstance(payload, dict):
            raise DashboardUnavailable('Expected a JSON object.')
        return payload

    preferences = DashboardPreferences.objects.filter(user=user).first()
    currency = currency or (preferences.currency if preferences else 'TRY')
    profile = profile or (preferences.profile if preferences else 'balanced')
    portfolios = user.portfolio_set.order_by('id')
    if portfolio is None:
        portfolio = portfolios.first()
    elif portfolio.user_id != user.pk:
        raise DashboardUnavailable('Portfolio unavailable.')

    if not portfolio or portfolio.dataset == 'demo':
        raise DashboardUnavailable('A market portfolio is required.')
    asof = snap['asof'] if snap else date.today()
    rows = list(portfolio.transactions.select_related('asset').filter(date__lte=asof))
    state = snap['state'] if snap else replay(rows)
    assets = {row.asset_id: row.asset for row in rows if row.asset_id}
    market_prices = {holding['asset'].pk: float(holding['price']) for holding in snap['holdings']} if snap else {}
    holdings = []
    for aid, position in state.positions.items():
        if position.quantity > 0:
            holding = {'symbol': archive_code(assets[aid].symbol), 'shares': float(position.quantity)}
            if aid in market_prices:
                holding['price'] = market_prices[aid]
            holdings.append(holding)
    if not holdings:
        raise DashboardUnavailable('At least one open fund or metal position is required.')
    contributions = []
    for row in rows:
        symbol = archive_code(row.asset.symbol) if row.asset else 'CASH'
        item = {
            'date': row.date.isoformat(),
            'symbol': symbol,
            'side': 'buy' if row.kind in ('buy', 'deposit') else 'sell',
            'amount_tl': float(row.quantity * row.price * row.fx_to_try),
            'units': float(row.quantity) if row.asset and row.asset.kind != 'metal' else None,
            'grams': float(row.quantity) if row.asset and row.asset.kind == 'metal' else None,
        }
        contributions.append(item)
    return call_bridge({
        'holdings': holdings, 'cash': float(state.cash), 'contributions': contributions,
        'monthly_contribution': float(preferences.monthly_contribution) if preferences else 0.0,
        'profile': profile, 'base_currency': currency, 'lang': lang,
    })


def workspace_payload(portfolio, currency, profile, lang, book=None, *, include_history=False):
    book = book or portfolio_book(portfolio)
    snap = snapshot(portfolio, currency, book=book)
    total_try = snap['total'] * book.rate(currency, snap['asof'])
    totals = {}
    for code in ('TRY', 'USD', 'EUR', 'GBP'):
        try:
            totals[f'total_value_{code.lower()}'] = float(total_try / book.rate(code, snap['asof']))
        except MissingData:
            totals[f'total_value_{code.lower()}'] = None
    allocation = {holding['asset'].symbol: holding['weight'] for holding in snap['holdings']}
    if snap['cash'] and snap['total']:
        allocation['Cash'] = float(snap['cash'] / snap['total'] * 100)
    portfolio_data = {
        **totals, 'base_currency': currency, 'cash_currency': 'TRY',
        'cash_balance': float(snap['state'].cash), 'allocation_by_subcategory': allocation,
        'valuation_date': snap['asof'].isoformat(), 'dataset': portfolio.dataset,
        'quotes': [check.public() for check in snap['quotes']],
    }
    engine_payload = None
    if portfolio.archive_prices and portfolio.dataset == 'live' and snap['holdings']:
        try:
            engine_payload = load_dashboard(
                portfolio.user, lang, currency=currency, profile=profile, portfolio=portfolio, snap=snap,
            )
        except DashboardUnavailable:
            logger.info('Portfolio analysis engine unavailable')
    payload = dict(engine_payload or {})
    payload['portfolio'] = {**(payload.get('portfolio') or {}), **portfolio_data}
    payload['source'] = 'archive' if portfolio.archive_prices else 'ledger'
    if snap['holdings'] and (include_history or not portfolio.archive_prices):
        history_start = snap['asof'] - timedelta(days=365)
        try:
            frame = history(portfolio, currency, history_start, snap['asof'], book)
        except MissingData as exc:
            payload['historical_risk_error'] = str(exc)
        else:
            risk = portfolio_risk(frame, snap)
            if risk:
                if portfolio.archive_prices:
                    for key in ('score', 'components', 'method'):
                        del risk[key]
                payload['historical_risk'] = {
                    **risk, 'start': frame.index[0], 'end': frame.index[-1],
                }
    return payload, snap, bool(engine_payload)


def call_bridge(inputs):
    if os.getenv('PORTFOLIO_AI_TEST_OFFLINE') == '1':
        raise AssertionError('Use an analysis fixture instead of starting the engine in tests.')
    backend = settings.PORTFOLIO_AI_HOME
    if not (backend / 'service_bridge.py').is_file():
        raise DashboardUnavailable('The analysis package was not found.')
    request = json.dumps(inputs, allow_nan=False)
    # Include the packaged data revisions in the cache key.
    revisions = [(backend / name).stat().st_mtime_ns for name in
                 ('data/snapshot/USDTRY.parquet', 'data/universe_scores.json', 'data/news_cache.sqlite')
                 if (backend / name).is_file()]
    cache_key = salted_hmac('dashboard-bridge', f'{backend}:{revisions}:{request}').hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    env = {**os.environ, 'PORTFOLIO_AI_HOME': str(backend), 'PYTHON_DOTENV_DISABLED': '1',
           'X_BEARER_TOKEN': '', 'TWITTER_BEARER_TOKEN': '', 'EVDS_API_KEY': '',
           'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    try:
        process = subprocess.run(
            [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('bridge_worker.py'))],
            cwd=backend, input=request, capture_output=True, encoding='utf-8', errors='replace',
            timeout=110, env=env, check=True,
        )
        payload = json.loads(process.stdout)
    except subprocess.CalledProcessError as exc:
        logger.warning('Dashboard bridge exited with status %s', exc.returncode)
        raise DashboardUnavailable('The analysis service could not calculate the portfolio.') from None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise DashboardUnavailable('The analysis service is unavailable.') from None
    if not isinstance(payload, dict):
        raise DashboardUnavailable('The analysis service returned an invalid result.')
    cache.set(cache_key, payload, timeout=120)
    return payload
