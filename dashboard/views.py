import logging
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe

from portfolio.context import workspace
from portfolio.models import CURRENCIES
from portfolio.services.valuation import MissingData

from .models import LANGUAGES, LEVELS, PROFILES, DashboardPreferences
from .presentation import dashboard_context, dashboard_labels
from .services import DashboardUnavailable, load_dashboard, mock_choices

logger = logging.getLogger(__name__)


class PreferenceForm(forms.ModelForm):
    currency = forms.ChoiceField(choices=CURRENCIES)
    monthly_contribution = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)

    class Meta:
        model = DashboardPreferences
        fields = ['language', 'currency', 'profile', 'level', 'monthly_contribution']


class DashboardQuery(forms.Form):
    lang = forms.ChoiceField(choices=LANGUAGES, required=False)
    currency = forms.ChoiceField(choices=CURRENCIES, required=False)
    profile = forms.ChoiceField(choices=PROFILES, required=False)
    level = forms.ChoiceField(choices=LEVELS, required=False)

    def __init__(self, data):
        super().__init__(data)
        if settings.USE_MOCK_DASHBOARD:
            self.fields['fixture'] = forms.ChoiceField(choices=mock_choices(), required=False)


def read_payload(request, preferences, params):
    return load_dashboard(
        request.user,
        params.get('lang') or preferences.language,
        currency=params.get('currency') or preferences.currency,
        profile=params.get('profile') or preferences.profile,
        portfolio=workspace(request).get('active_portfolio'),
        fixture=params.get('fixture') or 'example',
    )


@login_required
@never_cache
@require_safe
def dashboard(request):
    stored = DashboardPreferences.objects.filter(user=request.user).first()
    preferences = stored or DashboardPreferences()
    query = DashboardQuery(request.GET)
    valid_query = query.is_valid()
    params = query.cleaned_data if valid_query else {}
    context = {
        'page': 'ai_dashboard',
        'first_visit': stored is None,
        'language': params.get('lang') or preferences.language,
        'currency': params.get('currency') or preferences.currency,
        'profile': params.get('profile') or preferences.profile,
        'level': params.get('level') or preferences.level,
        'monthly_contribution': preferences.monthly_contribution,
        'mock': settings.USE_MOCK_DASHBOARD,
        'fixture': params.get('fixture') or 'example',
        'fixtures': mock_choices() if settings.USE_MOCK_DASHBOARD else [],
        'query_error': not valid_query or request.GET.get('invalid') == '1',
    }
    context['t'] = dashboard_labels(context['language'])
    try:
        payload = read_payload(request, preferences, params)
    except (DashboardUnavailable, MissingData):
        logger.info('Dashboard data unavailable', exc_info=True)
        context['data_unavailable'] = True
    else:
        context.update(dashboard_context(payload, context['language'], context['currency']))
    with translation.override(context['language']):
        return render(request, 'dashboard/index.html', context)


@login_required
@require_POST
def preferences(request):
    current = DashboardPreferences.objects.filter(user=request.user).first()
    form = PreferenceForm(request.POST, instance=current)
    fixture = request.POST.get('fixture')
    query = {'fixture': fixture} if settings.USE_MOCK_DASHBOARD and fixture in dict(mock_choices()) else {}
    if form.is_valid():
        DashboardPreferences.objects.update_or_create(user=request.user, defaults=form.cleaned_data)
    else:
        query['invalid'] = '1'
    url = reverse('ai_dashboard')
    return redirect(f'{url}?{urlencode(query)}' if query else url)


@never_cache
@require_safe
def dashboard_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    query = DashboardQuery(request.GET)
    if not query.is_valid():
        return JsonResponse({'errors': query.errors.get_json_data()}, status=400)
    preferences = DashboardPreferences.objects.filter(user=request.user).first()
    try:
        payload = read_payload(request, preferences or DashboardPreferences(), query.cleaned_data)
    except (DashboardUnavailable, MissingData):
        logger.info('Dashboard data unavailable', exc_info=True)
        return JsonResponse({'error': 'Dashboard data is unavailable.'}, status=503)
    return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
