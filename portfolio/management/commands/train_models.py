from django.core.management.base import BaseCommand, CommandError

from portfolio.models import Asset
from portfolio.services.ml import train_asset


class Command(BaseCommand):
    help = 'Train and evaluate the configured lightweight model. No network calls.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', choices=['demo', 'live'], default='demo')
        parser.add_argument('--symbol')

    def handle(self, *args, **options):
        assets = (
            Asset.objects.filter(price__dataset=options['dataset'])
            .exclude(kind='benchmark')
            .distinct()
        )
        if options['symbol']:
            assets = assets.filter(symbol=options['symbol'])
        if not assets.exists():
            raise CommandError('No eligible asset observations found in the selected dataset.')
        failures = []
        for asset in assets:
            try:
                run = train_asset(asset, options['dataset'])
                self.stdout.write(
                    f'{asset.symbol}: MAE {run.metrics["mae"]:.6f}; baseline {run.metrics["baseline_mae"]:.6f}; test rows {run.metrics["test_rows"]}'
                )
            except ValueError as exc:
                self.stderr.write(str(exc))
                failures.append(asset.symbol)
        if failures:
            raise CommandError(
                f'Training failed for: {", ".join(failures)}. Successful models were retained.'
            )
