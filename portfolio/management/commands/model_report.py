from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from portfolio.models import ModelRun


class Command(BaseCommand):
    help = 'Export the latest per-asset model evaluation as an English Markdown report.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', choices=['demo', 'live'], default='demo')
        parser.add_argument('--output', default='docs/MODEL_RESULTS.md')

    def handle(self, *args, **options):
        seen, runs = set(), []
        for run in ModelRun.objects.filter(dataset=options['dataset']).select_related('asset'):
            if run.asset_id not in seen:
                seen.add(run.asset_id)
                runs.append(run)
        if not runs:
            raise CommandError('No trained model runs exist for this dataset.')
        runs.sort(key=lambda run: run.asset.symbol)
        lines = [
            '# Model evaluation results',
            '',
            f'Generated {date.today()} · Dataset: {options["dataset"]}',
            '',
            'This report records the latest completed training run for each asset. Errors are measured on fractional next-observation returns, not price levels.',
            '',
        ]
        if options['dataset'] == 'demo':
            lines += [
                '**All prices in these runs are synthetic. These results validate the software pipeline and do not establish performance on real financial markets.**',
                '',
            ]
        lines += [
            '| Asset | Model MAE | Zero-return MAE | RMSE | Direction accuracy | Test observations | Lower MAE than baseline |',
            '| --- | ---: | ---: | ---: | ---: | ---: | --- |',
        ]
        for run in runs:
            m = run.metrics
            better = 'Yes' if m['mae'] < m['baseline_mae'] else 'No'
            lines.append(
                f'| {run.asset.symbol} | {m["mae"]:.6f} | {m["baseline_mae"]:.6f} | {m["rmse"]:.6f} | {m["direction_accuracy"]:.1f}% | {m["test_rows"]} | {better} |'
            )
        lines += ['', '## Chronology and repeatability', '']
        for run in runs:
            m = run.metrics
            folds = ', '.join(f'{v:.6f}' for v in m['cv_mae'])
            lines += [
                f'### {run.asset.symbol}',
                '',
                f'Estimator: `{run.model_name}`. Data ends {run.data_end}. Training: {m["train_start"]}–{m["train_end"]} ({m["train_rows"]} observations). Holdout feature dates: {m["test_start"]}–{m["test_end"]} ({m["test_rows"]} observations). Each holdout target is the following close return.',
                '',
                f'Expanding-window MAE: {folds}. A one-observation gap separates training from validation and the final holdout.',
                '',
                f'Illustrative long/cash return: {m["strategy_return_pct"]:.2f}%. Buy-and-hold return: {m["buy_hold_return_pct"]:.2f}%. Cost: {m["cost_bps"]} bps per position change. Forecast after final refit: {run.prediction * 100:+.3f}% for the next observation.',
                '',
                f'Saved artifact: `{run.artifact}`. Its adjacent JSON contains full evaluation metrics and holdout curves.',
                '',
            ]
        count = sum(r.metrics['mae'] < r.metrics['baseline_mae'] for r in runs)
        lines += [
            '## Interpretation and limits',
            '',
            f'{count} of {len(runs)} models achieved lower holdout MAE than the zero-return baseline. Models without improvement are labeled accordingly in the UI. No significance test or real-market predictive advantage is claimed.',
            '',
            'The backtest assumes feature-day close execution, ignores taxes, slippage and settlement constraints, and uses 10 bps per position change. Capacity figures in the UI are independent alternatives before fees, not a jointly optimized trading plan. The resilience score is a separate documented heuristic, not the output of this prediction model.',
            '',
            '## Reproduce',
            '',
            '```powershell',
            f'.\\.venv\\Scripts\\python.exe manage.py train_models --dataset {options["dataset"]}',
            f'.\\.venv\\Scripts\\python.exe manage.py model_report --dataset {options["dataset"]}',
            '```',
            '',
            'Exact real-data reproducibility requires retaining the input observations and locked package versions. The demo generator preserves past observations when extended to a later date; models trained on a longer series naturally have different holdout boundaries and metrics.',
            '',
        ]
        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('\n'.join(lines), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Wrote {output} with {len(runs)} model runs.'))
