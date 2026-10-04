from bisect import bisect_right
from datetime import date
from decimal import Decimal

import pandas as pd

from portfolio.models import Asset, ExchangeRate, Price

from .ledger import Ledger, replay


class MissingData(ValueError):
    pass


class MarketBook:
    """One dataset per book. Only observations on or before the requested day."""

    def __init__(self, dataset):
        self.prices = {}
        self.fx = {}
        self.assets = {a.id: a for a in Asset.objects.all()}
        for aid, day, close in (
            Price.objects.filter(dataset=dataset)
            .values_list('asset_id', 'date', 'close')
            .order_by('date')
        ):
            self.prices.setdefault(aid, []).append((day, close))
        for currency, day, rate in (
            ExchangeRate.objects.filter(dataset=dataset)
            .values_list('currency', 'date', 'try_per_unit')
            .order_by('date')
        ):
            self.fx.setdefault(currency, []).append((day, rate))
        self.price_days = {key: [v[0] for v in rows] for key, rows in self.prices.items()}
        self.fx_days = {key: [v[0] for v in rows] for key, rows in self.fx.items()}

    @staticmethod
    def lookup(rows, days, day, label, strict=True):
        i = bisect_right(days, day) - 1
        if i < 0:
            raise MissingData(f'No {label} on or before {day}. Import historical data first.')
        observed, value = rows[i]
        if strict and (day - observed).days > 7:
            raise MissingData(f'{label} is older than 7 days at {day}; valuation is unavailable.')
        return value, observed

    def rate(self, currency, day, strict=True):
        if currency == 'TRY':
            return Decimal(1)
        return self.lookup(
            self.fx.get(currency, []),
            self.fx_days.get(currency, []),
            day,
            currency + '/TRY',
            strict,
        )[0]

    def price(self, asset_id, day, strict=True):
        return self.lookup(
            self.prices.get(asset_id, []),
            self.price_days.get(asset_id, []),
            day,
            self.assets[asset_id].symbol,
            strict,
        )

    def asset_try(self, asset_id, day):
        price, _ = self.price(asset_id, day)
        return price * self.rate(self.assets[asset_id].currency, day)


def snapshot(portfolio, currency='TRY', asof=None, book=None):
    asof = asof or date.today()
    book = book or MarketBook(portfolio.dataset)
    state = replay(portfolio.transactions.filter(date__lte=asof).select_related('asset'))
    fx = book.rate(currency, asof)
    holdings = []
    for aid, p in state.positions.items():
        if p.quantity == 0:
            continue
        price, observed = book.price(aid, asof)
        value = p.quantity * price * book.rate(book.assets[aid].currency, asof)
        holdings.append(
            {
                'asset': book.assets[aid],
                'quantity': p.quantity,
                'price': price,
                'value': value / fx,
                'cost': p.cost / fx,
                'pnl': (value - p.cost) / fx,
                'return_pct': float((value / p.cost - 1) * 100) if p.cost else 0,
                'date': observed,
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
        'state': state,
    }


def history(portfolio, currency='TRY', start=None, end=None, book=None):
    end = end or date.today()
    rows = list(portfolio.transactions.filter(date__lte=end).select_related('asset'))
    if not rows:
        return pd.DataFrame(columns=['value', 'flow', 'return', 'index'])
    book = book or MarketBook(portfolio.dataset)
    days = sorted(set(pd.bdate_range(rows[0].date, end).date) | {r.date for r in rows} | {end})
    state, cursor, previous, growth = Ledger(), 0, None, 1.0
    output = []
    for day in days:
        flow = Decimal(0)
        while cursor < len(rows) and rows[cursor].date <= day:
            row = rows[cursor]
            state.apply(row)
            if row.kind in ('deposit', 'withdraw'):
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
