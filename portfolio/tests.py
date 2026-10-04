from datetime import date, timedelta
from decimal import Decimal as D
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .models import Asset, ExchangeRate, Note, Portfolio, Price, Transaction
from .services.analytics import risk_metrics
from .services.ledger import delete_transaction, replay, save_transaction
from .services.ml import features
from .services.providers import (
    ProviderError,
    import_articles,
    import_market,
    read_market_csv,
    sentiment_score,
    sync_provider,
)
from .services.valuation import MarketBook, MissingData, history, snapshot


class PortfolioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='Testing-only-9842')
        self.other = User.objects.create_user('bob', password='Testing-only-9842')
        self.portfolio = Portfolio.objects.create(user=self.user, name='Test', dataset='live')
        self.other_portfolio = Portfolio.objects.create(
            user=self.other, name='Private', dataset='live'
        )
        self.asset = Asset.objects.create(symbol='TEST', name='Test fund', kind='fund')
        self.day = date(2026, 1, 5)
        Price.objects.create(
            asset=self.asset, date=self.day, close=10, dataset='live', source='fixture'
        )
        ExchangeRate.objects.create(
            currency='USD', date=self.day, try_per_unit=40, dataset='live', source='fixture'
        )

    def tx(self, kind='deposit', price='1000', quantity='1', fee='0', day=None, **kwargs):
        row = Transaction(
            portfolio=self.portfolio,
            date=day or self.day,
            kind=kind,
            price=D(price),
            quantity=D(quantity),
            fee=D(fee),
            fx_to_try=D(1),
            asset=self.asset if kind in ('buy', 'sell') else None,
            **kwargs,
        )
        return save_transaction(row)

    def test_weighted_average_partial_sale_and_fees(self):
        self.tx()
        self.tx('buy', '10', '10', '2')
        self.tx('buy', '20', '10', '2')
        self.tx('sell', '30', '5', '1')
        state = replay(self.portfolio.transactions.select_related('asset'))
        p = state.positions[self.asset.id]
        self.assertEqual(p.quantity, 15)
        self.assertEqual(p.cost, D('228'))
        self.assertEqual(p.realized, D('73'))
        self.assertEqual(state.cash, D('845'))

    def test_oversell_rolls_back(self):
        self.tx()
        self.tx('buy', '10', '10')
        with self.assertRaises(ValidationError):
            self.tx('sell', '12', '11')
        self.assertEqual(self.portfolio.transactions.count(), 2)

    def test_cash_shortage_rolls_back(self):
        with self.assertRaises(ValidationError):
            self.tx('buy', '100', '1')
        self.assertEqual(self.portfolio.transactions.count(), 0)

    def test_delete_deposit_revalidates_future_trades(self):
        deposit = self.tx()
        self.tx('buy', '10', '10')
        with self.assertRaises(ValidationError):
            delete_transaction(deposit)
        self.assertEqual(self.portfolio.transactions.count(), 2)

    def test_backdated_edit_preserves_original_on_error(self):
        deposit = self.tx()
        self.tx('buy', '10', '10')
        deposit.price = D('50')
        with self.assertRaises(ValidationError):
            save_transaction(deposit)
        deposit.refresh_from_db()
        self.assertEqual(deposit.price, 1000)

    def test_deleting_buy_that_funds_sale_is_rejected(self):
        self.tx()
        buy = self.tx('buy', '10', '10')
        self.tx('sell', '11', '5')
        with self.assertRaises(ValidationError):
            delete_transaction(buy)
        self.assertEqual(self.portfolio.transactions.count(), 3)

    def test_fx_and_snapshot(self):
        self.tx()
        self.tx('buy', '10', '10')
        result = snapshot(self.portfolio, 'USD', self.day)
        self.assertEqual(result['total'], D('25'))
        self.assertEqual(result['holdings'][0]['value'], D('2.5'))

    def test_fx_trade_records_cash_value(self):
        self.tx()
        row = Transaction(
            portfolio=self.portfolio,
            date=self.day,
            kind='buy',
            asset=self.asset,
            quantity=D(2),
            price=D(3),
            fee=D(1),
            currency='USD',
            fx_to_try=D(40),
        )
        save_transaction(row)
        state = replay(self.portfolio.transactions.select_related('asset'))
        self.assertEqual(state.cash, D(720))
        self.assertEqual(state.positions[self.asset.id].cost, D(280))

    def test_no_future_price_or_cross_dataset_fallback(self):
        Price.objects.create(
            asset=self.asset,
            date=self.day - timedelta(days=2),
            close=999,
            dataset='demo',
            source='demo',
        )
        with self.assertRaises(MissingData):
            MarketBook('live').price(self.asset.id, self.day - timedelta(days=1))

    def test_stale_prices_rejected(self):
        with self.assertRaises(MissingData):
            MarketBook('live').price(self.asset.id, self.day + timedelta(days=8))

    def test_cash_deposit_does_not_create_return(self):
        self.tx()
        self.tx(price='1000', day=self.day + timedelta(days=1))
        frame = history(self.portfolio, end=self.day + timedelta(days=1))
        self.assertEqual(frame['index'].iloc[-1], 100)
        self.assertEqual(frame['value'].iloc[-1], 2000)

    def test_cash_withdrawal_does_not_create_loss(self):
        self.tx()
        self.tx('withdraw', '400', day=self.day + timedelta(days=1))
        frame = history(self.portfolio, end=self.day + timedelta(days=1))
        self.assertEqual(frame['index'].iloc[-1], 100)

    def test_price_appreciation_generates_return(self):
        self.tx()
        self.tx('buy', '10', '100')
        Price.objects.create(
            asset=self.asset,
            date=self.day + timedelta(days=1),
            close=11,
            dataset='live',
            source='fixture',
        )
        frame = history(self.portfolio, end=self.day + timedelta(days=1))
        self.assertAlmostEqual(frame['index'].iloc[-1], 110)

    def test_owner_access(self):
        foreign = Transaction.objects.create(
            portfolio=self.other_portfolio, date=self.day, kind='deposit', price=10
        )
        note = Note.objects.create(
            portfolio=self.other_portfolio, title='secret', body='secret body'
        )
        self.client.force_login(self.user)
        for url in [
            reverse('transaction_edit', args=[foreign.id]),
            reverse('note_edit', args=[note.id]),
        ]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(reverse('transaction_delete', args=[foreign.id])).status_code, 404
        )
        self.assertEqual(self.client.post(reverse('note_delete', args=[note.id])).status_code, 404)
        self.assertEqual(
            self.client.post(
                reverse('portfolio_switch'), {'portfolio_id': self.other_portfolio.id}
            ).status_code,
            404,
        )

    def test_anonymous_redirect(self):
        for name in [
            'dashboard',
            'holdings',
            'transactions',
            'analysis',
            'notes',
            'news',
            'settings',
            'compare',
        ]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_empty_pages_render(self):
        self.client.force_login(self.user)
        for name in [
            'dashboard',
            'holdings',
            'transactions',
            'analysis',
            'notes',
            'news',
            'settings',
            'compare',
            'transaction_new',
            'note_new',
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_delete_requires_post_and_csrf(self):
        self.client.force_login(self.user)
        row = self.tx()
        self.assertEqual(
            self.client.get(reverse('transaction_delete', args=[row.id])).status_code, 405
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(
            csrf_client.post(reverse('transaction_delete', args=[row.id])).status_code, 403
        )

    def test_csv_import_atomic_and_idempotent(self):
        payload = {'prices': [{'symbol': 'TEST', 'date': '2026-01-05', 'close': '12'}]}
        import_market(payload)
        import_market(payload)
        self.assertEqual(Price.objects.filter(dataset='live').count(), 1)
        payload['prices'].append({'symbol': 'UNKNOWN', 'date': '2026-01-05', 'close': '1'})
        payload['prices'][0]['close'] = '99'
        with self.assertRaises(ProviderError):
            import_market(payload)
        self.assertEqual(Price.objects.get(asset=self.asset, dataset='live').close, D(12))

    def test_invalid_numeric_imports_rejected(self):
        for value in ['NaN', 'Infinity', '-1', '0']:
            with self.assertRaises(ProviderError):
                import_market(
                    {'prices': [{'symbol': 'TEST', 'date': '2026-01-05', 'close': value}]}
                )

    def test_csv_schema(self):
        payload = read_market_csv(
            'type,symbol,date,value\nprice,TEST,2026-01-05,25\nfx,USD,2026-01-05,40\n'
        )
        self.assertEqual(import_market(payload), 2)

    @patch.dict('os.environ', {'NEWS_API_KEY': ''})
    def test_missing_credentials_fail_explicitly(self):
        with self.assertRaises(ProviderError):
            sync_provider('news')

    @patch.dict('os.environ', {'NEWS_API_KEY': 'fixture-not-a-secret'})
    @patch('portfolio.services.providers.get_json')
    def test_news_adapter_normalizes_response(self, fetch):
        fetch.return_value = {
            'status': 'ok',
            'articles': [
                {
                    'title': 'Strong growth',
                    'url': 'https://example.com/article',
                    'publishedAt': '2026-01-01T10:00:00Z',
                    'source': {'name': 'Fixture'},
                }
            ],
        }
        self.assertEqual(sync_provider('news'), 1)

    def test_article_unsafe_url_rejected(self):
        with self.assertRaises(ProviderError):
            import_articles(
                [
                    {
                        'title': 'Title',
                        'published_at': '2026-01-01T10:00:00Z',
                        'url': 'javascript:alert(1)',
                    }
                ]
            )

    def test_shared_market_import_requires_staff(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('market_import')).status_code, 403)

    def test_invalid_date_range_has_no_server_error(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard'), {'start': 'bad'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Correct the date')

    def test_note_html_escaped(self):
        Note.objects.create(
            portfolio=self.portfolio, title='<script>alert(1)</script>', body='<b>unsafe</b>'
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('notes'))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_registration_and_transaction_form_flow(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'newinvestor',
                'password1': 'Local-test-account!85',
                'password2': 'Local-test-account!85',
            },
        )
        self.assertEqual(response.status_code, 302)
        p = Portfolio.objects.get(user__username='newinvestor')
        self.assertEqual(p.dataset, 'live')
        response = self.client.post(
            reverse('transaction_new'),
            {
                'kind': 'deposit',
                'date': str(self.day),
                'asset': '',
                'quantity': '1',
                'price': '1000',
                'currency': 'TRY',
                'fee': '0',
                'memo': 'Opening',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(p.transactions.get().price, 1000)

    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'fixture'})
    @patch('portfolio.services.providers.get_json')
    def test_social_adapter(self, fetch):
        fetch.return_value = {
            'data': [
                {'id': '123', 'text': 'Excellent growth', 'created_at': '2026-01-05T10:00:00Z'}
            ]
        }
        self.assertEqual(sync_provider('social'), 1)

    @patch.dict('os.environ', {'GOLD_API_TOKEN': 'fixture'})
    @patch('portfolio.services.providers.get_json')
    def test_metals_ounce_to_gram_conversion(self, fetch):
        from datetime import datetime, timezone

        stamp = datetime(2026, 1, 5, 12, tzinfo=timezone.utc).timestamp()
        fetch.side_effect = [
            {'metal': m, 'currency': 'USD', 'timestamp': stamp, 'price': '31.1034768'}
            for m in ['XAU', 'XAG', 'XPT']
        ]
        self.assertEqual(sync_provider('metals'), 3)
        self.assertEqual(Price.objects.get(asset__symbol='XAU', dataset='live').close, D(40))

    @patch('pytefas.Crawler')
    def test_tefas_normalization(self, crawler):
        from .services.public_sources import tefas_history

        crawler.return_value.fetch.return_value = pd.DataFrame(
            [
                {
                    'fund_code': 'AAK',
                    'fund_name': 'Test TEFAS fixture',
                    'date': '2026-01-05',
                    'price': 10.5,
                }
            ]
        )
        self.assertEqual(tefas_history('AAK', self.day, self.day), 1)
        self.assertEqual(Price.objects.get(asset__symbol='AAK', dataset='live').close, D('10.5'))

    @patch('yfinance.download')
    def test_yahoo_normalization(self, download):
        from .services.public_sources import yahoo_history

        download.return_value = pd.DataFrame(
            {'Close': [42.0]}, index=pd.to_datetime(['2026-01-05'])
        )
        self.assertEqual(yahoo_history(self.day, self.day), 6)
        self.assertEqual(Price.objects.get(asset__symbol='SP500', dataset='live').close, D(42))

    def test_future_and_demo_live_import_rejected(self):
        Asset.objects.create(symbol='DEMO-X', name='Fictional', kind='fund')
        with self.assertRaises(ProviderError):
            import_market({'prices': [{'symbol': 'DEMO-X', 'date': str(self.day), 'close': '3'}]})
        with self.assertRaises(ProviderError):
            import_market(
                {
                    'prices': [
                        {
                            'symbol': 'TEST',
                            'date': str(date.today() + timedelta(days=1)),
                            'close': '3',
                        }
                    ]
                }
            )

    @patch.dict('os.environ', {'NEWS_API_KEY': 'fixture'})
    @patch(
        'portfolio.services.providers.get_json',
        side_effect=ProviderError('Provider returned HTTP 429.'),
    )
    def test_provider_failure_preserves_cached_prices(self, fetch):
        with self.assertRaises(ProviderError):
            sync_provider('news')
        self.assertEqual(Price.objects.get(asset=self.asset, dataset='live').close, D(10))


class AnalyticsTests(TestCase):
    def test_demo_extensions_preserve_earlier_observations(self):
        from .services.demo import synthetic_history

        earlier, rates_before = synthetic_history(date(2026, 10, 1))
        later, rates_after = synthetic_history(date(2026, 10, 5))
        for symbol, values in earlier.items():
            self.assertEqual(values, later[symbol][: len(values)])
        for currency, values in rates_before.items():
            self.assertEqual(values, rates_after[currency][: len(values)])

    def test_training_command_fails_without_eligible_data(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command('train_models', dataset='live', symbol='MISSING')

    def test_drawdown_known_path(self):
        r = pd.Series([0.0] * 30 + [-0.2, 0.125])
        metrics = risk_metrics(r, [0.5, 0.5])
        self.assertAlmostEqual(metrics['drawdown'], -20)
        self.assertGreaterEqual(metrics['score'], 0)
        self.assertLessEqual(metrics['score'], 100)

    def test_insufficient_history(self):
        self.assertIsNone(risk_metrics([0.01] * 10))

    def test_features_have_no_future_leakage(self):
        prices = pd.Series(np.linspace(100, 200, 100))
        before = features(prices).iloc[50].copy()
        prices.iloc[51:] = 999
        pd.testing.assert_series_equal(before, features(prices).iloc[50])

    def test_sentiment_labeled_fixture(self):
        fixture = [
            ('Excellent profits and wonderful growth!', 'positive'),
            ('Terrible losses and disastrous failure.', 'negative'),
            ('The report was published on Monday.', 'neutral'),
        ]
        for text, expected in fixture:
            score = sentiment_score(text)
            label = 'positive' if score >= 0.05 else 'negative' if score <= -0.05 else 'neutral'
            self.assertEqual(label, expected)
