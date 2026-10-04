from django.core.management.base import BaseCommand, CommandError

from portfolio.services.providers import ProviderError, sync_provider


class Command(BaseCommand):
    help = 'Fetch configured market/news/social data, preserving the cache on failure.'

    def add_arguments(self, parser):
        parser.add_argument('provider', choices=['market', 'news', 'social', 'metals'])

    def handle(self, *args, **options):
        try:
            count = sync_provider(options['provider'])
            self.stdout.write(self.style.SUCCESS(f'Imported {count} records.'))
        except ProviderError as exc:
            raise CommandError(str(exc))
