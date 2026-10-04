from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from portfolio.services.demo import create_demo_portfolio, seed_market


class Command(BaseCommand):
    help = 'Create repeatable synthetic market data. Optionally create a non-admin demo account.'

    def add_arguments(self, parser):
        parser.add_argument('--create-account', action='store_true')

    def handle(self, *args, **options):
        prices, rates = seed_market()
        if options['create_account']:
            user, created = User.objects.get_or_create(username='demo')
            if created:
                user.set_password('PortfolioDemo!2026')
                user.save()
                create_demo_portfolio(user)
                self.stdout.write(
                    'Created local demo account: demo / PortfolioDemo!2026 (non-admin).'
                )
            else:
                self.stdout.write(
                    'Existing demo account preserved; password and portfolios unchanged.'
                )
        self.stdout.write(
            self.style.SUCCESS(
                f'Demo dataset ready: {prices} prices and {rates} rates (idempotent). Register in the browser to load a personal demo.'
            )
        )
