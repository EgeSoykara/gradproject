import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from portfolio.services.providers import (
    ProviderError,
    import_articles,
    import_market,
    read_market_csv,
)


class Command(BaseCommand):
    help = 'Import market CSV/JSON or news/social JSON into the explicit selected dataset.'

    def add_arguments(self, parser):
        parser.add_argument('file')
        parser.add_argument('--kind', choices=['market', 'news', 'social'], default='market')
        parser.add_argument('--dataset', choices=['demo', 'live'], default='live')

    def handle(self, *args, **options):
        path = Path(options['file'])
        try:
            text = path.read_text(encoding='utf-8-sig')
            if options['kind'] == 'market':
                data = read_market_csv(text) if path.suffix.lower() == '.csv' else json.loads(text)
                count = import_market(data, options['dataset'], source=f'Import: {path.name}')
            else:
                count = import_articles(json.loads(text), options['dataset'], kind=options['kind'])
            self.stdout.write(self.style.SUCCESS(f'Imported {count} records.'))
        except (ProviderError, OSError, ValueError) as exc:
            raise CommandError(str(exc))
