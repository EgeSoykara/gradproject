from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Min
from django.utils import timezone

from portfolio.models import SyncLog, Transaction
from portfolio.services.providers import ProviderError
from portfolio.services.public_sources import yahoo_history


class Command(BaseCommand):
    help = 'Refresh the SQLite Yahoo Finance cache once per day, outside web requests.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        first = Transaction.objects.filter(portfolio__dataset='live').aggregate(
            first=Min('date')
        )['first']
        if first is None:
            self.stdout.write('No market portfolio transactions yet.')
            return

        end = today - timedelta(days=1)
        if first > end:
            self.stdout.write('No completed market day in the requested period.')
            return
        start = first - timedelta(days=7)
        coverage = f'Benchmark cache: {start} to {end}.'
        if SyncLog.objects.filter(
            provider='benchmark-cache', status='success', message=coverage, created_at__date=today
        ).exists():
            self.stdout.write('Benchmark cache has already been updated today.')
            return

        try:
            count = yahoo_history(start, end)
        except ProviderError as exc:
            raise CommandError(str(exc)) from exc
        SyncLog.objects.create(provider='benchmark-cache', status='success', message=coverage)
        self.stdout.write(self.style.SUCCESS(f'Cached {count} daily price and FX records.'))
