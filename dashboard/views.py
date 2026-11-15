import logging
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
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
from .presentation import correlation_context, dashboard_context, dashboard_labels
from .services import (
    DEFAULT_FIXTURE,
    DashboardUnavailable,
    archive_correlation,
    load_dashboard,
    mock_choices,
    mock_profile_reference,
    workspace_payload,
)

logger = logging.getLogger(__name__)


class PreferenceForm(forms.ModelForm):
    currency = forms.ChoiceField(choices=CURRENCIES)
    monthly_contribution = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)

    class Meta:
        model = DashboardPreferences
        fields = ['currency', 'profile', 'level', 'monthly_contribution']


class DashboardQuery(forms.Form):
    lang = forms.ChoiceField(choices=LANGUAGES, required=False)
    currency = forms.ChoiceField(choices=CURRENCIES, required=False)
    profile = forms.ChoiceField(choices=PROFILES, required=False)
    level = forms.ChoiceField(choices=LEVELS, required=False)

    def __init__(self, data):
        super().__init__(data)
        self.fields['fixture'] = forms.ChoiceField(choices=mock_choices(), required=False)


def read_payload(request, preferences, params, portfolio):
    lang = params.get('lang') or request.LANGUAGE_CODE
    fixture = params.get('fixture')
    if fixture:
        return load_dashboard(request.user, lang, fixture=fixture), None, True
    if portfolio is None:
        raise DashboardUnavailable('Select or create a portfolio.')
    return workspace_payload(portfolio, params.get('currency') or preferences.currency,
                             params.get('profile') or preferences.profile, lang)


def selected_fixture(request, fixture=None):
    choice = fixture or request.session.get('dashboard_fixture')
    if choice in dict(mock_choices()):
        return choice
    return DEFAULT_FIXTURE


@login_required
@never_cache
@require_safe
def dashboard(request):
    stored = request.dashboard_preferences
    preferences = stored or DashboardPreferences()
    query = DashboardQuery(request.GET)
    valid_query = query.is_valid()
    params = query.cleaned_data if valid_query else {}
    portfolio = workspace(request).get('active_portfolio')
    mock = bool(params.get('fixture'))
    has_transactions = bool(portfolio and portfolio.transactions.exists())
    context = {
        'page': 'ai_dashboard',
        'language': params.get('lang') or request.LANGUAGE_CODE,
        'currency': params.get('currency') or preferences.currency,
        'profile': params.get('profile') or preferences.profile,
        'level': params.get('level') or preferences.level,
        'monthly_contribution': preferences.monthly_contribution,
        'mock': mock,
        'onboarding': not mock and not has_transactions,
        'selected_workspace': bool(portfolio and request.session.get('portfolio_id') == portfolio.pk),
        'uses_archive': bool(portfolio and portfolio.archive_prices),
        'demo_workspace': bool(portfolio and portfolio.dataset == 'demo'),
        'fixture': selected_fixture(request, params.get('fixture')),
        'fixtures': mock_choices(),
        'query_error': not valid_query or request.GET.get('invalid') == '1',
    }
    labels = dashboard_labels(context['language'])
    context.update(t=labels, profile_label=labels[context['profile']], level_label=labels[context['level']],
                   profile_help=labels[f"{context['profile']}_help"])
    context['robustness_source'] = labels['robustness_engine']
    if context['mock']:
        fixture = context['fixture']
        fixture_label = labels['fixture_example'] if fixture == 'example' else f"{labels['fixture']} {fixture[-1]}"
        context['robustness_source'] = f"{fixture_label} · {labels['robustness_archive']}"
    context['level_options'] = [(code, labels[code], labels[f'{code}_help']) for code, _ in LEVELS]
    context['profile_options'] = [(code, labels[code], labels[f'{code}_help']) for code, _ in PROFILES]
    if context['language'] != request.LANGUAGE_CODE:
        translation.activate(context['language'])
        request.LANGUAGE_CODE = context['language']
    if not context['onboarding']:
        try:
            payload, snap, full_analysis = read_payload(request, preferences, params, portfolio)
        except (DashboardUnavailable, MissingData) as exc:
            logger.info('Dashboard data unavailable', exc_info=True)
            context.update(data_unavailable=True, data_error=str(exc) if isinstance(exc, MissingData) else '')
        else:
            reference = mock_profile_reference(context['profile']) if mock else None
            context.update(dashboard_context(
                payload, context['language'], context['currency'],
                profile=context['profile'], level=context['level'], reference=reference,
            ))
            context.update(snap=snap, full_analysis=full_analysis)
            if not mock and snap and not snap['holdings']:
                context['first_purchase'] = not portfolio.transactions.filter(kind='buy').exists()
            if context['level'] == 'expert' and full_analysis and not mock:
                result = archive_correlation(payload)
                if result is not None:
                    context['correlation_data'] = correlation_context(result)
    return render(request, 'dashboard/index.html', context)


@login_required
@require_POST
def preferences(request):
    current = request.dashboard_preferences
    form = PreferenceForm(request.POST, instance=current)
    fixture = request.POST.get('fixture')
    query = {'fixture': fixture} if fixture in dict(mock_choices()) else {}
    if form.is_valid():
        DashboardPreferences.objects.update_or_create(
            user=request.user, defaults=form.cleaned_data,
            create_defaults={'language': request.LANGUAGE_CODE, **form.cleaned_data},
        )
        if query:
            request.session['dashboard_fixture'] = fixture
        messages.success(request, dashboard_labels(request.LANGUAGE_CODE)['saved'])
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
    preferences = request.dashboard_preferences
    try:
        portfolio = workspace(request).get('active_portfolio')
        payload, _, _ = read_payload(request, preferences or DashboardPreferences(), query.cleaned_data, portfolio)
    except (DashboardUnavailable, MissingData):
        logger.info('Dashboard data unavailable', exc_info=True)
        return JsonResponse({'error': 'Dashboard data is unavailable.'}, status=503)
    return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
