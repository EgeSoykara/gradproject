"""Run the separately installed engine with its own working directory."""
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


def main():
    arguments = json.load(sys.stdin)
    with redirect_stdout(sys.stderr):
        from analytics.dca import load_price_series
        from service_bridge import get_dashboard

        symbols = {entry['symbol'] for entry in arguments['holdings'] + arguments['contributions']}
        for symbol in symbols - {'CASH'}:
            if not symbol or not symbol.isascii() or not symbol.isalnum():
                raise ValueError('An asset symbol is invalid.')
            if not (Path('data/snapshot') / f'{symbol}.parquet').is_file():
                raise ValueError('An asset does not have analysis data.')
        for holding in arguments['holdings']:
            prices = load_price_series(holding['symbol']).sort_index()
            holding['price'] = float(prices.iloc[-1])
        payload = get_dashboard(**arguments, ledger_cash_flows=True)
    json.dump(payload, sys.stdout, ensure_ascii=False, allow_nan=False)


if __name__ == '__main__':
    main()
