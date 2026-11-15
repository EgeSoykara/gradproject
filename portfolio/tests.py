from datetime import date, timedelta
from decimal import Decimal as D
from unittest.mock import patch

import pandas as pd
import requests
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Asset, ExchangeRate, NewsItem, Note, Portfolio, Price, SyncLog, Transaction
from .services.analytics import risk_metrics
from .services.ledger import delete_transaction, replay, save_transaction
from .services.providers import (
    ProviderError,
    import_articles,
    import_market,
    read_market_csv,
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
        self.assertEqual(result['oldest_quote'], self.day)
        self.assertEqual(
            [(check.symbol, check.quote.source) for check in result['quotes']],
            [('TEST', 'fixture'), ('USD/TRY', 'fixture')],
        )

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

    def test_all_missing_and_outdated_observations_are_reported(self):
        self.tx()
        self.tx('buy', '10', '2')
        self.client.force_login(self.user)
        query = {'currency': 'EUR'}
        response = self.client.get(reverse('dashboard_api'), query)
        self.assertEqual(response.status_code, 503)
        issues = response.json()['quote_issues']
        self.assertEqual([(c['symbol'], c['status']) for c in issues], [
            ('TEST', 'stale'), ('EUR/TRY', 'missing'),
        ])
        self.assertEqual(issues[0]['observed'], self.day.isoformat())
        self.assertEqual(issues[0]['origin'], 'live')
        page = self.client.get(reverse('holdings'), query)
        self.assertContains(page, 'Outdated')
        self.assertContains(page, 'EUR/TRY')
        self.assertNotContains(page, 'Market value')
        settings = self.client.get(reverse('settings'), query)
        self.assertContains(settings, 'Portfolio data')
        self.assertContains(settings, 'EUR/TRY')

    def test_history_date_range_uses_previous_holdings_without_earlier_prices(self):
        self.tx()
        self.tx('buy', '10', '10')
        start = self.day + timedelta(days=14)
        end = start + timedelta(days=1)
        for day, value in ((start, 18), (end, 20)):
            Price.objects.create(asset=self.asset, date=day, close=value, dataset='live', source='fixture')
        frame = history(self.portfolio, start=start, end=end)
        self.assertEqual(frame['value'].tolist(), [1080, 1100])
        self.assertEqual(frame['flow'].tolist(), [0, 0])
        self.assertAlmostEqual(frame['index'].iloc[-1], 1100 / 1080 * 100)

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
            'notes',
            'news',
            'settings',
            'compare',
            'transaction_new',
            'note_new',
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_language_switch_persists_across_pages_and_sessions(self):
        self.client.force_login(self.user)
        analysis_url = reverse('ai_dashboard')
        response = self.client.post(
            reverse('set_language'),
            {'language': 'tr', 'next': f'{analysis_url}?lang=en&currency=TRY'},
        )
        self.assertRedirects(response, f'{analysis_url}?currency=TRY')
        self.assertContains(self.client.get(analysis_url), 'Portföy paneli')
        self.assertContains(self.client.get(reverse('transactions')), '<h1>İşlemler</h1>', html=True)
        self.assertContains(self.client.get(reverse('transaction_new')), 'İşlem kaydet')
        self.assertContains(self.client.get(reverse('ai_dashboard')), '<html lang="tr">')

        new_session = Client()
        new_session.force_login(self.user)
        self.assertContains(new_session.get(reverse('notes')), '<h1>Notlarım</h1>', html=True)
        response = new_session.post(
            reverse('set_language'), {'language': 'en', 'next': reverse('notes')}
        )
        self.assertRedirects(response, reverse('notes'))
        self.assertContains(self.client.get(reverse('notes')), '<h1>My notes</h1>', html=True)

    def test_retired_model_lab_bookmarks_go_to_the_portfolio_dashboard(self):
        self.client.force_login(self.user)
        for name in ('analysis', 'model_lab'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name), {'currency': 'USD', 'budget': '200'})
                self.assertRedirects(response, f"{reverse('ai_dashboard')}?currency=USD&budget=200")

    def test_news_keeps_headlines_and_links_to_archive_analysis(self):
        self.client.force_login(self.user)
        import_articles([{
            'id': 'headline', 'title': 'A raw financial headline',
            'url': 'https://example.com/report', 'published_at': '2026-01-01T12:00:00Z',
        }])
        item = NewsItem.objects.get(external_id='headline')
        item.sentiment = 0.9
        item.save(update_fields=['sentiment'])
        self.portfolio.archive_prices = True
        self.portfolio.save(update_fields=['archive_prices'])
        response = self.client.get(reverse('news'))
        self.assertContains(response, 'A raw financial headline')
        self.assertContains(response, 'FinTurkBERT')
        self.assertContains(response, f'{reverse("ai_dashboard")}#dashboard-news')
        self.assertNotContains(response, 'VADER')
        self.assertNotContains(response, '0.9')

    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'fixture-must-not-leave-the-process'})
    def test_x_requests_fail_before_network_access(self):
        with self.assertRaisesRegex(AssertionError, 'Network access is disabled'):
            sync_provider('social')
        with self.assertRaisesRegex(AssertionError, 'Network access is disabled'):
            requests.get('https://api.x.com/2/tweets/search/recent')

    def test_benchmark_form_can_clear_all_comparisons(self):
        self.client.force_login(self.user)
        path = reverse('compare')
        self.assertEqual(self.client.get(path).context['selected'], ['SP500', 'NASDAQ100', 'BTC'])
        self.assertEqual(self.client.get(path, {'benchmark_choices': '1'}).context['selected'], [])

    def test_language_switch_works_before_sign_in(self):
        response = self.client.post(
            reverse('set_language'),
            {'language': 'tr', 'next': 'https://example.com/'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('login')), 'Portföyüne giriş yap')
        self.assertContains(self.client.get(reverse('register')), 'Çalışma alanını oluştur')

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

    def test_staff_upload_shows_result_and_keeps_prices_on_failure(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        template = self.client.get(reverse('market_import_template'))
        self.assertEqual(template.content, b'type,symbol,date,value\r\n')
        url = reverse('market_import')
        csv_file = SimpleUploadedFile(
            'prices.csv', b'type,symbol,date,value\nprice,TEST,2026-01-05,25\n'
        )
        response = self.client.post(url, {'file': csv_file}, follow=True)
        self.assertContains(response, 'Imported 1 market observation.')
        self.assertEqual(Price.objects.get().source, 'CSV import')
        upload = SimpleUploadedFile('fx.json', b'{"rates":[{"currency":"EUR","date":"2026-01-05","try_per_unit":"46"}]}')
        self.client.post(url, {'file': upload}, follow=True)
        self.assertEqual(ExchangeRate.objects.get(currency='EUR').source, 'JSON import')
        invalid = SimpleUploadedFile('bad.csv', (
            b'type,symbol,date,value\nprice,TEST,2026-01-05,99\nprice,UNKNOWN,2026-01-05,1\n'
        ))
        response = self.client.post(url, {'file': invalid}, follow=True)
        self.assertContains(response, 'Every price requires a known symbol, date and close.')
        self.assertContains(response, 'Connection history')
        self.assertEqual(Price.objects.get().close, D(25))
        self.assertEqual(
            list(SyncLog.objects.filter(provider='File import').values_list('status', flat=True)),
            ['error', 'success', 'success'],
        )

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

    def test_note_lifecycle_for_account_without_portfolio(self):
        user = User.objects.create_user('notes-only')
        self.client.force_login(user)
        response = self.client.post(reverse('note_new'), {'title': 'First note', 'body': 'Review next week'})
        self.assertRedirects(response, reverse('notes'))
        note = Note.objects.get(portfolio__user=user)
        self.assertEqual(note.title, 'First note')
        response = self.client.post(reverse('note_edit', args=[note.pk]), {
            'title': 'Updated note', 'body': 'Review next month',
        })
        self.assertRedirects(response, reverse('notes'))
        note.refresh_from_db()
        self.assertEqual(note.body, 'Review next month')
        self.assertRedirects(self.client.post(reverse('note_delete', args=[note.pk])), reverse('notes'))
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

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

    def test_drawdown_known_path(self):
        r = pd.Series([0.0] * 30 + [-0.2, 0.125])
        metrics = risk_metrics(r, [0.5, 0.5])
        self.assertAlmostEqual(metrics['drawdown'], -20)
        self.assertGreaterEqual(metrics['score'], 0)
        self.assertLessEqual(metrics['score'], 100)

    def test_insufficient_history(self):
        self.assertIsNone(risk_metrics([0.01] * 10))
