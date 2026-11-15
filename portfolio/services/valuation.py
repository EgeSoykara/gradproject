from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd
from django.utils.translation import gettext as _

from portfolio.models import Asset, ExchangeRate, Price

from .archive import archive_close
from .ledger import Ledger, replay

MAX_QUOTE_AGE_DAYS = 7


@dataclass(frozen=True)
class Quote:
    value: Decimal
    date: date
    source: str


@dataclass(frozen=True)
class QuoteCheck:
    symbol: str
    kind: str
    asof: date
    quote: Quote | None
    origin: str

    @property
    def age(self):
        return (self.asof - self.quote.date).days if self.quote else None

    @property
    def status(self):
        if self.quote is None:
            return 'missing'
        return 'stale' if self.age > MAX_QUOTE_AGE_DAYS else 'ready'

    @property
    def message(self):
        if self.status == 'missing':
            return _('No %(label)s on or before %(day)s.') % {
                'label': self.symbol,
                'day': self.asof,
            }
        return _('%(label)s last observed on %(observed)s, %(age)s days before %(day)s.') % {
            'label': self.symbol,
            'observed': self.quote.date,
            'age': self.age,
            'day': self.asof,
        }

    def public(self):
        return {
            'symbol': self.symbol,
            'kind': self.kind,
            'asof': self.asof.isoformat(),
            'origin': self.origin,
            'status': self.status,
            'age_days': self.age,
            'observed': self.quote.date.isoformat() if self.quote else None,
            'source': self.quote.source if self.quote else None,
        }


class MissingData(ValueError):
    def __init__(self, message, checks=()):
        super().__init__(message)
        self.checks = checks


class MarketBook:
    """Load each instrument's series once and look up observations at or before the requested day."""

    uses_archive = False

    def __init__(self, dataset):
        self.dataset = dataset
        self.assets = Asset.objects.in_bulk()
        self._prices = {}
        self._rates = {}

    def price_series(self, asset_id):
        if asset_id not in self._prices:
            rows = Price.objects.filter(dataset=self.dataset, asset_id=asset_id).order_by('date')
            self._prices[asset_id] = self.indexed(rows.values_list('close', 'date', 'source'))
        return self._prices[asset_id]

    def rate_series(self, currency):
        if currency not in self._rates:
            rows = ExchangeRate.objects.filter(dataset=self.dataset, currency=currency).order_by(
                'date'
            )
            self._rates[currency] = self.indexed(rows.values_list('try_per_unit', 'date', 'source'))
        return self._rates[currency]

    @staticmethod
    def indexed(rows):
        quotes = [Quote(value, day, source) for value, day, source in rows]
        return quotes, [quote.date for quote in quotes]

    @staticmethod
    def latest(series, day):
        quotes, dates = series
        index = bisect_right(dates, day) - 1
        return quotes[index] if index >= 0 else None

    def check_price(self, asset_id, day):
        asset = self.assets[asset_id]
        origin = 'archive' if self.uses_archive and asset.kind != 'benchmark' else self.dataset
        return QuoteCheck(
            asset.symbol, 'price', day, self.latest(self.price_series(asset_id), day), origin
        )

    def check_rate(self, currency, day):
        origin = 'archive' if self.uses_archive and currency == 'USD' else self.dataset
        return QuoteCheck(
            currency + '/TRY', 'fx', day, self.latest(self.rate_series(currency), day), origin
        )

    @staticmethod
    def require(check, strict):
        if check.quote is None or (strict and check.status == 'stale'):
            raise MissingData(check.message, (check,))
        return check.quote

    def rate(self, currency, day, strict=True):
        if currency == 'TRY':
            return Decimal(1)
        return self.require(self.check_rate(currency, day), strict).value

    def price(self, asset_id, day, strict=True):
        quote = self.require(self.check_price(asset_id, day), strict)
        return quote.value, quote.date

    def asset_try(self, asset_id, day):
        price, _ = self.price(asset_id, day)
        return price * self.rate(self.assets[asset_id].currency, day)


class ArchiveMarketBook(MarketBook):
    uses_archive = True

    def __init__(self):
        super().__init__('live')
        self._archive = {}

    def archive_series(self, symbol):
        if symbol not in self._archive:
            try:
                prices = archive_close(symbol)
            except (OSError, ImportError, ValueError, TypeError):
                self._archive[symbol] = ([], [])
            else:
                self._archive[symbol] = self.indexed(
                    (Decimal(str(value)), day.date(), 'PortfolioAI_Ege')
                    for day, value in prices.items()
                )
        return self._archive[symbol]

    def price_series(self, asset_id):
        asset = self.assets[asset_id]
        if asset.kind == 'benchmark':
            return super().price_series(asset_id)
        return self.archive_series(asset.symbol) if asset.currency == 'TRY' else ([], [])

    def rate_series(self, currency):
        return self.archive_series('USDTRY') if currency == 'USD' else super().rate_series(currency)


def portfolio_book(portfolio):
    if portfolio.dataset == 'live' and portfolio.archive_prices:
        return ArchiveMarketBook()
    return MarketBook(portfolio.dataset)


def portfolio_valuation_date(portfolio, book):
    today = date.today()
    if not book.uses_archive:
        return today
    archive_rate = book.check_rate('USD', today).quote
    if archive_rate is None:
        return today
    transaction_day = (
        portfolio.transactions.filter(date__lte=today)
        .order_by('-date')
        .values_list('date', flat=True)
        .first()
    )
    return max(archive_rate.date, transaction_day or archive_rate.date)


def portfolio_quotes(portfolio, currency='TRY', asof=None, book=None, state=None):
    book = book or portfolio_book(portfolio)
    asof = asof or portfolio_valuation_date(portfolio, book)
    if state is None:
        state = replay(portfolio.transactions.filter(date__lte=asof).select_related('asset'))
    prices = {
        aid: book.check_price(aid, asof)
        for aid, position in state.positions.items()
        if position.quantity
    }
    currencies = {book.assets[aid].currency for aid in prices} | {currency}
    rates = {code: book.check_rate(code, asof) for code in sorted(currencies - {'TRY'})}
    return prices, rates


def snapshot(portfolio, currency='TRY', asof=None, book=None):
    book = book or portfolio_book(portfolio)
    asof = asof or portfolio_valuation_date(portfolio, book)
    state = replay(portfolio.transactions.filter(date__lte=asof).select_related('asset'))
    prices, rates = portfolio_quotes(portfolio, currency, asof, book, state)
    checks = [*prices.values(), *rates.values()]
    issues = [check for check in checks if check.status != 'ready']
    if issues:
        detail = (
            issues[0].message
            if len(issues) == 1
            else _('Some required prices or exchange rates are unavailable.')
        )
        raise MissingData(detail, issues)
    fx = rates[currency].quote.value if currency in rates else Decimal(1)
    holdings = []
    for aid, p in state.positions.items():
        if p.quantity == 0:
            continue
        quote = prices[aid].quote
        asset_currency = book.assets[aid].currency
        asset_rate = rates[asset_currency].quote.value if asset_currency in rates else Decimal(1)
        price = quote.value
        value = p.quantity * price * asset_rate
        holdings.append(
            {
                'asset': book.assets[aid],
                'quantity': p.quantity,
                'price': price,
                'value': value / fx,
                'cost': p.cost / fx,
                'pnl': (value - p.cost) / fx,
                'return_pct': float((value / p.cost - 1) * 100) if p.cost else 0,
                'date': quote.date,
                'source': quote.source,
            }
        )
    total = state.cash / fx + sum(h['value'] for h in holdings)
    for h in holdings:
        h['weight'] = float(h['value'] / total * 100) if total else 0
    realized = sum(p.realized for p in state.positions.values()) / fx
    return {
        'holdings': sorted(holdings, key=lambda h: h['value'], reverse=True),
        'cash': state.cash / fx,
        'total': total,
        'invested': state.contributions / fx,
        'pnl': total - state.contributions / fx,
        'realized': realized,
        'unrealized': sum(h['pnl'] for h in holdings),
        'currency': currency,
        'asof': asof,
        'quotes': checks,
        'oldest_quote': min((check.quote.date for check in checks), default=None),
        'latest_quote': max((check.quote.date for check in checks), default=None),
        'state': state,
    }


def history(portfolio, currency='TRY', start=None, end=None, book=None):
    end = end or date.today()
    rows = list(portfolio.transactions.filter(date__lte=end).select_related('asset'))
    if not rows:
        return pd.DataFrame(columns=['value', 'flow', 'return', 'index'])
    book = book or portfolio_book(portfolio)
    first_day = max(rows[0].date, start) if start else rows[0].date
    if first_day > end:
        return pd.DataFrame(columns=['value', 'flow', 'return', 'index'])
    days = sorted(
        set(pd.bdate_range(first_day, end).date)
        | {r.date for r in rows if r.date >= first_day}
        | {end}
    )
    state, cursor, previous, growth = Ledger(), 0, None, 1.0
    output = []
    for day in days:
        flow = Decimal(0)
        while cursor < len(rows) and rows[cursor].date <= day:
            row = rows[cursor]
            state.apply(row)
            if row.date == day and row.kind in ('deposit', 'withdraw'):
                flow += row.price * row.fx_to_try * (1 if row.kind == 'deposit' else -1)
            cursor += 1
        fx = book.rate(currency, day)
        total = state.cash + sum(
            p.quantity * book.asset_try(aid, day)
            for aid, p in state.positions.items()
            if p.quantity
        )
        value, flow_value = float(total / fx), float(flow / fx)
        # End-of-day external flows; same-day trades are valued at close.
        ret = (value - flow_value) / previous - 1 if previous and previous > 0 else 0.0
        growth *= 1 + ret
        output.append((day, value, flow_value, ret, growth * 100))
        previous = value
    frame = pd.DataFrame(output, columns=['date', 'value', 'flow', 'return', 'index']).set_index(
        'date'
    )
    if start:
        frame = frame.loc[frame.index >= start]
    if not frame.empty and frame['index'].iloc[0] > 0:
        frame['index'] = frame['index'] / frame['index'].iloc[0] * 100
    return frame


def benchmark_history(asset, dataset, dates, currency, book=None):
    book = book or MarketBook(dataset)
    values = [float(book.asset_try(asset.id, d) / book.rate(currency, d)) for d in dates]
    series = pd.Series(values, index=dates)
    return series / series.iloc[0] * 100 if len(series) else series
