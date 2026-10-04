"""Opt-in adapters. Errors are visible; neither adapter substitutes demo data."""

from datetime import timedelta

import pandas as pd
from django.db import transaction

from portfolio.models import Asset

from .providers import ProviderError, import_market


def yahoo_history(start, end):
    import yfinance as yf

    mapping = {
        '^GSPC': ('price', 'SP500', 'S&P 500'),
        '^NDX': ('price', 'NASDAQ100', 'NASDAQ 100'),
        'BTC-USD': ('price', 'BTC', 'Bitcoin'),
        'TRY=X': ('fx', 'USD', 'USD/TRY'),
        'EURTRY=X': ('fx', 'EUR', 'EUR/TRY'),
        'GBPTRY=X': ('fx', 'GBP', 'GBP/TRY'),
    }
    payload = {'prices': [], 'rates': []}
    for ticker, (kind, symbol, name) in mapping.items():
        try:
            frame = yf.download(
                ticker,
                start=str(start),
                end=str(end + timedelta(days=1)),
                auto_adjust=False,
                progress=False,
                threads=False,
                multi_level_index=False,
                timeout=20,
            )
            if frame is None or frame.empty or 'Close' not in frame:
                raise ProviderError(f'No history returned for {ticker}. Cache was not changed.')
            close = frame['Close'].dropna()
            for stamp, value in close.items():
                day = pd.Timestamp(stamp).date()
                if start <= day <= end:
                    if kind == 'price':
                        payload['prices'].append(
                            {'symbol': symbol, 'date': str(day), 'close': str(value)}
                        )
                    else:
                        payload['rates'].append(
                            {'currency': symbol, 'date': str(day), 'try_per_unit': str(value)}
                        )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f'Yahoo history failed for {ticker} ({type(exc).__name__}). Cache was not changed.'
            ) from None
    with transaction.atomic():
        for kind, symbol, name in mapping.values():
            if kind == 'price':
                Asset.objects.get_or_create(
                    symbol=symbol,
                    defaults={
                        'name': name,
                        'kind': 'benchmark',
                        'currency': 'USD',
                        'unit': 'index' if symbol != 'BTC' else 'coins',
                    },
                )
        return import_market(payload, source='Yahoo Finance · unadjusted daily close')


def tefas_history(symbol, start, end):
    from pytefas import Crawler

    if not symbol or not symbol.isalnum() or len(symbol) > 10:
        raise ProviderError('Provide a valid fund symbol, for example AAK.')
    try:
        frame = Crawler(timeout=20, max_retry=1).fetch(
            str(start), str(end), kind='YAT', columns='info', fund_code=symbol
        )
        if frame is None or frame.empty:
            raise ProviderError(
                'TEFAS returned no observations. Use a permitted CSV export if the public API is unavailable.'
            )
        if not {'fund_code', 'fund_name', 'date', 'price'}.issubset(frame.columns):
            raise ProviderError(
                'TEFAS schema changed. Update the adapter; cached data was not replaced.'
            )
        frame = frame[frame.fund_code == symbol].dropna(subset=['price'])
        if frame.empty:
            raise ProviderError('No observations matched the requested TEFAS symbol.')
        payload = {
            'prices': [
                {'symbol': symbol, 'date': str(pd.Timestamp(r.date).date()), 'close': str(r.price)}
                for r in frame.itertuples()
                if start <= pd.Timestamp(r.date).date() <= end
            ]
        }
        with transaction.atomic():
            asset, _ = Asset.objects.get_or_create(
                symbol=symbol,
                defaults={
                    'name': str(frame.iloc[0].fund_name)[:120],
                    'kind': 'fund',
                    'currency': 'TRY',
                    'unit': 'units',
                },
            )
            if asset.kind != 'fund' or asset.currency != 'TRY':
                raise ProviderError('The requested TEFAS symbol conflicts with an existing asset.')
            return import_market(payload, source='TEFAS via pytefas')
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(
            f'TEFAS access failed ({type(exc).__name__}). Use CSV import or retry later; cache is unchanged.'
        ) from None
