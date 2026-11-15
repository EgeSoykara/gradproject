from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portfolio.models import Asset, ExchangeRate, Portfolio, Price, Transaction
from portfolio.services.analytics import portfolio_correlation
from portfolio.services.valuation import ArchiveMarketBook

from .models import DashboardPreferences
from .services import call_bridge


class DashboardPreferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('dashboard-test')

    def setUp(self):
        self.client.force_login(self.user)
        self.dashboard = reverse('ai_dashboard')
        self.preferences = reverse('dashboard_preferences')

    def test_levels_and_profiles_apply_to_the_same_example(self):
        targets = {}
        for profile in ('conservative', 'balanced', 'aggressive'):
            for level in ('beginner', 'expert'):
                with self.subTest(profile=profile, level=level):
                    response = self.client.post(self.preferences, {
                        'profile': profile, 'level': level, 'currency': 'USD',
                        'monthly_contribution': '0', 'fixture': 'example',
                    }, follow=True)
                    self.assertContains(response, f'data-level="{level}" data-profile="{profile}"')
                    self.assertContains(response, 'Dashboard settings saved.')
                    self.assertEqual(response.context['portfolio_data']['total'], 2289.56)
                    score = response.context['robustness_data']['score']
                    self.assertContains(response, f'<dd>{score}%</dd>', html=True)
                    self.assertContains(response, f'<strong class="dashboard-score-value">{score}%</strong>', html=True)
                    target = tuple(row[2] for row in response.context['rebalancing_data']['rows'])
                    self.assertTrue(target)
                    if level == 'expert':
                        self.assertEqual(target, targets[profile])
                        self.assertContains(response, 'dashboard-risk-components')
                        self.assertNotContains(response, f'href="{reverse("model_lab")}"')
                        self.assertContains(response, 'contains no price series')
                        self.assertNotContains(response, 'id="bridge-correlation"')
                    else:
                        targets[profile] = target
                        self.assertNotContains(response, 'dashboard-risk-components')
                        self.assertNotContains(response, f'href="{reverse("model_lab")}"')
        self.assertEqual(len(set(targets.values())), 3)
        response = self.client.get(self.dashboard)
        self.assertEqual(response.context['fixture'], 'example')
        self.assertEqual(response.context['level'], 'expert')
        self.assertEqual(response.context['profile'], 'aggressive')

    def test_engine_subprocess_requires_a_fixture_during_tests(self):
        with self.assertRaisesRegex(AssertionError, 'analysis fixture'):
            call_bridge({})

    def test_invalid_preferences_preserve_last_valid_selection(self):
        DashboardPreferences.objects.create(user=self.user, profile='conservative', level='expert')
        response = self.client.post(self.preferences, {
            'profile': 'invalid', 'level': 'beginner', 'currency': 'TRY', 'monthly_contribution': '0',
        }, follow=True)
        self.assertContains(response, '<details class="dashboard-preferences" open>')
        self.assertContains(response, 'data-level="expert" data-profile="conservative"')

    def test_ledger_score_percentage_matches_the_api(self):
        today = date.today()
        start = today - timedelta(days=50)
        asset = Asset.objects.create(symbol='LOCAL', name='Local fund', kind='fund')
        portfolio = Portfolio.objects.create(user=self.user, name='Market', dataset='live')
        Transaction.objects.create(portfolio=portfolio, kind='deposit', price=500, date=start)
        Transaction.objects.create(
            portfolio=portfolio, kind='buy', price=10, quantity=5, asset=asset, date=start,
        )
        Price.objects.bulk_create([
            Price(asset=asset, date=start + timedelta(days=i), close=10 + i / 10, dataset='live', source='test')
            for i in range(51)
        ])
        query = {'lang': 'en', 'currency': 'TRY'}
        page = self.client.get(self.dashboard, query)
        api = self.client.get(reverse('dashboard_api'), query).json()
        score = api['historical_risk']['score']
        self.assertEqual(page.context['ledger_score'], score)
        self.assertContains(page, f'<dd>{score}%</dd>', html=True)
        self.assertNotContains(page, 'id="dashboard-historical-risk"')
        expert = self.client.get(self.dashboard, {**query, 'level': 'expert'})
        self.assertContains(expert, f'<dd>{score}%</dd>', html=True)
        self.assertContains(expert, f'<strong class="dashboard-score-value">{score}%</strong>', html=True)
        self.assertContains(expert, 'id="dashboard-historical-risk"')
        turkish = self.client.get(self.dashboard, {**query, 'lang': 'tr'})
        self.assertContains(turkish, f'<strong class="dashboard-score-value">%{score}</strong>', html=True)

    @patch('portfolio.services.valuation.archive_close')
    @patch('dashboard.services.call_bridge', return_value={})
    def test_engine_receives_saved_profile_currency_and_monthly_amount(self, call_bridge, archive_close):
        archive_close.return_value = pd.Series([12], index=pd.DatetimeIndex([date.today()]))
        portfolio = Portfolio.objects.create(
            user=self.user, name='Market portfolio', dataset='live', archive_prices=True,
        )
        asset = Asset.objects.create(symbol='AAL', name='Test fund', kind='fund')
        ExchangeRate.objects.create(currency='EUR', date=date.today(), try_per_unit=50, dataset='live')
        Transaction.objects.create(
            portfolio=portfolio, date=date(2025, 1, 1), kind='deposit',
            price=1000, quantity=1, currency='TRY', fx_to_try=1,
        )
        Transaction.objects.create(
            portfolio=portfolio, asset=asset, date=date(2025, 1, 2), kind='buy',
            price=10, quantity=1, currency='TRY', fx_to_try=1,
        )
        response = self.client.post(self.preferences, {
            'profile': 'aggressive', 'level': 'expert', 'currency': 'EUR', 'monthly_contribution': '2500.50',
        }, follow=True)
        self.assertContains(response, 'data-level="expert" data-profile="aggressive"')
        inputs = call_bridge.call_args.args[0]
        self.assertEqual(inputs['profile'], 'aggressive')
        self.assertEqual(inputs['base_currency'], 'EUR')
        self.assertEqual(inputs['monthly_contribution'], 2500.50)
        self.assertEqual(inputs['holdings'][0]['price'], 12)
        self.assertEqual(self.user.dashboardpreferences.monthly_contribution, Decimal('2500.50'))

    def test_personal_onboarding_through_first_purchase(self):
        placeholder = Portfolio.objects.create(user=self.user, name='My portfolio')
        first = self.client.get(self.dashboard)
        self.assertContains(first, 'Create my portfolio')
        self.assertContains(first, 'Explore the demo')
        self.assertNotContains(first, 'dashboard-payload')

        transaction_url = reverse('transaction_new')
        self.assertRedirects(
            self.client.post(f"{reverse('portfolio_create')}?onboarding=1", {'name': 'My savings'}),
            f'{transaction_url}?kind=deposit&onboarding=1',
        )
        placeholder.refresh_from_db()
        self.assertEqual(placeholder.name, 'My savings')
        self.assertEqual(self.user.portfolio_set.count(), 1)

        base = {'currency': 'TRY', 'date': date.today().isoformat(), 'fee': '0'}
        self.assertRedirects(self.client.post(
            f'{transaction_url}?kind=deposit&onboarding=1',
            {**base, 'kind': 'deposit', 'price': '1000'},
        ), self.dashboard)
        response = self.client.get(self.dashboard)
        self.assertContains(response, 'Record your first purchase')
        self.assertEqual(response.context['snap']['cash'], Decimal(1000))
        self.assertContains(self.client.get(f'{transaction_url}?kind=buy'), 'no assets with price history')

        asset = Asset.objects.create(symbol='TST', name='First test fund', kind='fund')
        Price.objects.create(asset=asset, date=date.today(), close=12, dataset='live')
        self.assertRedirects(self.client.post(
            f'{transaction_url}?kind=buy&onboarding=1',
            {**base, 'kind': 'buy', 'price': '10', 'quantity': '20', 'asset': asset.pk},
        ), self.dashboard)
        response = self.client.get(self.dashboard)
        self.assertContains(response, 'First test fund')
        self.assertEqual(response.context['portfolio_data']['total'], 1040)
        self.assertEqual(self.client.get(reverse('holdings')).context['snap']['total'], Decimal(1040))
        self.assertEqual(self.client.get(reverse('dashboard_api')).json()['portfolio']['total_value_try'], 1040)

    def test_demo_panel_and_trade_form_use_the_demo_dataset(self):
        portfolio = Portfolio.objects.create(user=self.user, name='Demo', dataset='demo')
        Transaction.objects.create(portfolio=portfolio, date=date.today(), kind='deposit', price=1000)
        day = date.today()
        demo_asset = Asset.objects.create(symbol='DEMO-TEST', name='Demo fund', kind='fund')
        live_asset = Asset.objects.create(symbol='LIVE', name='Real fund', kind='fund')
        Price.objects.create(asset=demo_asset, date=day, close=12, dataset='demo')
        Price.objects.create(asset=live_asset, date=day, close=7, dataset='live')
        response = self.client.get(self.dashboard, {'level': 'expert'})
        self.assertNotContains(response, f'href="{reverse("model_lab")}"')
        self.assertEqual(response.context['portfolio_data']['total'], 1000)
        self.assertFalse(response.context['mock'])
        form = self.client.get(reverse('transaction_new')).context['form']
        self.assertEqual(list(form.fields['asset'].queryset), [demo_asset])
        response = self.client.post(reverse('transaction_new'), {
            'kind': 'buy', 'date': day.isoformat(), 'asset': live_asset.pk,
            'quantity': '1', 'price': '7', 'currency': 'TRY', 'fee': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('asset', response.context['form'].errors)
        self.assertFalse(portfolio.transactions.filter(kind='buy').exists())

    @patch('portfolio.services.valuation.archive_close')
    def test_archive_uses_its_date_and_exposes_an_unpriced_later_transaction(self, archive_close):
        cutoff = date.today() - timedelta(days=30)
        archive_close.return_value = pd.Series([12], index=pd.DatetimeIndex([cutoff]))
        portfolio = Portfolio.objects.create(
            user=self.user, name='Archive', dataset='live', archive_prices=True,
        )
        asset = Asset.objects.create(symbol='AAL', name='Fund', kind='fund')
        Transaction.objects.create(portfolio=portfolio, kind='deposit', price=500, date=cutoff)
        Transaction.objects.create(portfolio=portfolio, kind='buy', price=12, asset=asset, date=cutoff)
        url = reverse('dashboard_api')
        with patch('dashboard.services.call_bridge', return_value={}):
            result = self.client.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['portfolio']['valuation_date'], cutoff.isoformat())
        Transaction.objects.create(portfolio=portfolio, kind='deposit', price=50, date=date.today())
        result = self.client.get(url)
        self.assertEqual(result.status_code, 503)
        issues = result.json()['quote_issues']
        self.assertEqual([(row['symbol'], row['origin'], row['status']) for row in issues], [
            ('AAL', 'archive', 'stale'),
        ])
        historical = self.client.get(reverse('holdings'), {'end': cutoff.isoformat()})
        self.assertEqual(historical.context['snap']['total'], 500)

    @patch('portfolio.services.valuation.archive_close')
    def test_correlation_aligns_only_held_symbols_through_snapshot_date(self, archive_close):
        dates = pd.date_range('2026-01-01', periods=45)
        prices = [100 + i + i % 3 for i in range(len(dates))]
        archive_close.side_effect = {
            'AAL': pd.Series(prices, index=dates),
            'XAU': pd.Series([value * 2 for value in prices[3:]], index=dates[3:]),
        }.__getitem__
        fund = Asset.objects.create(symbol='AAL', name='AAL', kind='fund', currency='TRY', unit='unit')
        metal = Asset.objects.create(symbol='XAU', name='Gold', kind='metal', currency='TRY', unit='gram')
        snap = {'asof': date(2026, 2, 7), 'currency': 'TRY', 'holdings': [{'asset': fund}, {'asset': metal}]}
        matrix, observations, start, end = portfolio_correlation(snap, ArchiveMarketBook())
        self.assertEqual(matrix.columns.tolist(), ['AAL', 'XAU'])
        self.assertAlmostEqual(matrix.loc['AAL', 'XAU'], 1)
        self.assertEqual(observations, 34)
        self.assertEqual((start, end), (date(2026, 1, 4), date(2026, 2, 7)))
        self.assertEqual([call.args[0] for call in archive_close.call_args_list], ['AAL', 'XAU'])
