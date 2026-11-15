from datetime import date
from decimal import Decimal

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.models import DashboardPreferences
from portfolio.models import Asset, Portfolio, Transaction
from portfolio.services.ledger import save_transaction


class Command(BaseCommand):
    help = 'Create an example portfolio for the local analysis engine from the delivered price archive.'

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.select_for_update().filter(username='demo').first()
        if user is None:
            raise CommandError('Run seed_demo --create-account first.')
        if user.portfolio_set.filter(name='Arşiv veri örneği', dataset='live').exists():
            self.stdout.write('Existing archive portfolio preserved.')
            return

        start = date(2025, 2, 3)
        snapshot_dir = settings.PORTFOLIO_AI_HOME / 'data/snapshot'
        trades = []
        for code, symbol, amount in [('AAL', 'AAL', 30000), ('GOLD', 'XAU', 5)]:
            try:
                asset = Asset.objects.get(symbol=symbol)
                prices = pd.read_parquet(snapshot_dir / f'{code}.parquet')['Close'].sort_index()
                price = prices.loc[:pd.Timestamp(start)].dropna().iloc[-1]
            except (Asset.DoesNotExist, OSError, KeyError, IndexError, ValueError) as exc:
                raise CommandError(f'Archive data unavailable for {code}.') from exc
            trades.append((asset, amount, Decimal(str(price)).quantize(Decimal('0.00000001'))))

        portfolio = Portfolio.objects.create(user=user, name='Arşiv veri örneği', dataset='live')
        save_transaction(Transaction(portfolio=portfolio, kind='deposit', date=start, price=100000))
        for asset, amount, price in trades:
            save_transaction(
                Transaction(portfolio=portfolio, kind='buy', date=start, asset=asset,
                            quantity=Decimal(amount), price=price)
            )
        DashboardPreferences.objects.get_or_create(
            user=user, defaults={'monthly_contribution': Decimal('5000')}
        )
        self.stdout.write('Archive example created. Select Arşiv veri örneği in the portfolio menu.')
