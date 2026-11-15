from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from portfolio.models import Asset, Portfolio, Transaction

from .models import DashboardPreferences


class DashboardPreferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('dashboard-test')

    def setUp(self):
        self.client.force_login(self.user)
        self.dashboard = reverse('ai_dashboard')
        self.preferences = reverse('dashboard_preferences')

    @override_settings(USE_MOCK_DASHBOARD=True)
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
                    else:
                        targets[profile] = target
                        self.assertNotContains(response, 'dashboard-risk-components')
        self.assertEqual(len(set(targets.values())), 3)
        response = self.client.get(self.dashboard)
        self.assertEqual(response.context['fixture'], 'example')
        self.assertEqual(response.context['level'], 'expert')
        self.assertEqual(response.context['profile'], 'aggressive')

    @override_settings(USE_MOCK_DASHBOARD=True)
    def test_invalid_preferences_preserve_last_valid_selection(self):
        DashboardPreferences.objects.create(user=self.user, profile='conservative', level='expert')
        response = self.client.post(self.preferences, {
            'profile': 'invalid', 'level': 'beginner', 'currency': 'TRY', 'monthly_contribution': '0',
        }, follow=True)
        self.assertContains(response, '<details class="dashboard-preferences" open>')
        self.assertContains(response, 'data-level="expert" data-profile="conservative"')

    @override_settings(USE_MOCK_DASHBOARD=False)
    @patch('dashboard.services.call_bridge', return_value={})
    def test_engine_receives_saved_profile_currency_and_monthly_amount(self, call_bridge):
        portfolio = Portfolio.objects.create(user=self.user, name='Market portfolio', dataset='live')
        asset = Asset.objects.create(symbol='AAL', name='Test fund', kind='fund')
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
        self.assertEqual(self.user.dashboardpreferences.monthly_contribution, Decimal('2500.50'))
