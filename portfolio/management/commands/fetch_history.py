from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from portfolio.models import SyncLog
from portfolio.services.providers import ProviderError, valid_day
from portfolio.services.public_sources import tefas_history, yahoo_history


class Command(BaseCommand):
    help = 'Fetch historical daily data from an opt-in public adapter. No demo fallback.'

    def add_arguments(self, parser):
        parser.add_argument('provider', choices=['yahoo', 'tefas'])
        parser.add_argument('--start', required=True)
        parser.add_argument('--end', default=str(date.today() - timedelta(days=1)))
        parser.add_argument('--symbol', help='Required for TEFAS, e.g. AAK')

    def handle(self, *args, **options):
        provider = options['provider']
        try:
            start, end = valid_day(options['start']), valid_day(options['end'])
            if start > end:
                raise ProviderError('Start must be on or before end.')
            count = (
                yahoo_history(start, end)
                if provider == 'yahoo'
                else tefas_history((options['symbol'] or '').upper(), start, end)
            )
            SyncLog.objects.create(
                provider=provider,
                status='success',
                message=f'Imported {count} historical observations.',
            )
            self.stdout.write(
                self.style.SUCCESS(f'Imported {count} records into the live dataset.')
            )
        except ProviderError as exc:
            SyncLog.objects.create(provider=provider, status='error', message=str(exc)[:500])
            raise CommandError(str(exc))
