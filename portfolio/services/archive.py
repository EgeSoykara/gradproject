from datetime import date

import pandas as pd
from django.conf import settings

METAL_SYMBOLS = {'XAU': 'GOLD', 'XAG': 'SILVER', 'XPT': 'PLATINUM'}


def archive_available():
    return (settings.PORTFOLIO_AI_HOME / 'service_bridge.py').is_file()


def archive_code(symbol):
    return METAL_SYMBOLS.get(symbol, symbol)


def archive_path(symbol):
    code = archive_code(symbol)
    if not isinstance(code, str) or not code.isascii() or not code.isalnum():
        raise ValueError('Invalid archive symbol.')
    return settings.PORTFOLIO_AI_HOME / 'data' / 'snapshot' / f'{code}.parquet'


def archive_close(symbol):
    frame = pd.read_parquet(archive_path(symbol))
    if 'Close' in frame:
        close = frame['Close']
    elif frame.shape[1] == 1:
        close = frame.iloc[:, 0]
    else:
        raise ValueError('Archive price column is unavailable.')
    close = pd.to_numeric(close, errors='coerce')
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    close = close.loc[~close.index.duplicated(keep='last')].sort_index()
    close = close.loc[:pd.Timestamp(date.today())]
    return close[(close > 0) & (close < float('inf'))]
