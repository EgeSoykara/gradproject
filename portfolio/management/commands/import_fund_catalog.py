import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from portfolio.models import Asset


class Command(BaseCommand):
    help = 'Import the fund symbols and names in universe_scores.json into the asset selector.'

    def add_arguments(self, parser):
        parser.add_argument('catalog', type=Path)

    def handle(self, *args, **options):
        try:
            payload = json.loads(options['catalog'].read_text(encoding='utf-8-sig'))
            scores = payload['scores']
            if not isinstance(scores, list):
                raise ValueError('scores must be an array')
            funds = {}
            for item in scores:
                symbol = item['symbol'].strip().upper()
                name = item['name'].strip()
                if not symbol or not name or len(symbol) > 20 or symbol.startswith('DEMO-'):
                    raise ValueError(f'Invalid catalog entry for {symbol!r}')
                funds[symbol] = name
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise CommandError(f'Invalid fund catalog: {exc}') from exc

        reserved = {'CASH', 'GOLD', 'SILVER', 'PLATINUM', 'XAU', 'XAG', 'XPT', 'SP500', 'NASDAQ100', 'BTC'}
        with transaction.atomic():
            existing = set(Asset.objects.filter(symbol__in=funds).values_list('symbol', flat=True))
            new_funds = [
                Asset(symbol=symbol, name=name[:120], kind='fund')
                for symbol, name in funds.items()
                if symbol not in existing and symbol not in reserved
            ]
            Asset.objects.bulk_create(new_funds, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'{len(new_funds)} new fund entries processed.'))
