from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from portfolio.models import Asset, ExchangeRate, Portfolio, Price, Transaction

from .models import DashboardPreferences
from .services import archive_correlation


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

    def test_invalid_preferences_preserve_last_valid_selection(self):
        DashboardPreferences.objects.create(user=self.user, profile='conservative', level='expert')
        response = self.client.post(self.preferences, {
            'profile': 'invalid', 'level': 'beginner', 'currency': 'TRY', 'monthly_contribution': '0',
        }, follow=True)
        self.assertContains(response, '<details class="dashboard-preferences" open>')
        self.assertContains(response, 'data-level="expert" data-profile="conservative"')

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
        self.assertContains(response, f'href="{reverse("model_lab")}"')
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

    @patch('dashboard.services.pd.read_parquet')
    def test_correlation_aligns_only_held_symbols_through_snapshot_date(self, read_parquet):
        dates = pd.date_range('2026-01-01', periods=45)
        prices = [100 + i + i % 3 for i in range(len(dates))]
        frames = {
            'AAL': pd.DataFrame({'Close': prices}, index=dates),
            'GOLD': pd.DataFrame({'Close': [value * 2 for value in prices[3:]]}, index=dates[3:]),
        }
        read_parquet.side_effect = lambda path: frames[path.stem]

        payload = {
            'portfolio': {'usd_rate_date': '2026-02-07'},
            'fund_cards': [{'symbol': 'AAL'}, {'symbol': 'GOLD'}],
        }
        matrix, observations, start, end = archive_correlation(payload)
        self.assertEqual(matrix.columns.tolist(), ['AAL', 'GOLD'])
        self.assertAlmostEqual(matrix.loc['AAL', 'GOLD'], 1)
        self.assertEqual(observations, 34)
        self.assertEqual((start, end), (date(2026, 1, 4), date(2026, 2, 7)))
        self.assertEqual([call.args[0].stem for call in read_parquet.call_args_list], ['AAL', 'GOLD'])
