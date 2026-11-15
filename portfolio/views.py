import csv
import json
import os
from datetime import date, timedelta

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_POST

from .charts import allocation_chart, chart, line_chart
from .context import workspace
from .forms import NoteForm, PortfolioForm, RangeForm, RegisterForm, TransactionForm
from .models import (
    CURRENCIES,
    Asset,
    ExchangeRate,
    NewsItem,
    Note,
    Portfolio,
    Price,
    SyncLog,
    Transaction,
)
from .services.analytics import portfolio_risk
from .services.demo import create_demo_portfolio, seed_market
from .services.ledger import delete_transaction, save_transaction
from .services.providers import ProviderError, import_market, read_market_csv
from .services.valuation import (
    MAX_QUOTE_AGE_DAYS,
    MissingData,
    benchmark_history,
    history,
    portfolio_book,
    portfolio_quotes,
    portfolio_valuation_date,
    snapshot,
)


def active(request):
    return workspace(request).get('active_portfolio')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Portfolio.objects.create(user=user, name='My portfolio')
        login(request, user)
        return redirect('ai_dashboard')
    return render(request, 'registration/register.html', {'form': form})


def selection(request):
    form = RangeForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
        return (
            form,
            data.get('currency') or 'TRY',
            data.get('start'),
            data.get('end'),
        )
    return form, 'TRY', None, None


def valuation_context(request, with_history=True):
    portfolio = active(request)
    if portfolio is None:
        portfolio = Portfolio.objects.create(user=request.user, name='My portfolio')
    form, currency, start, end = selection(request)
    ctx = {'range_form': form, 'currency': currency, 'page': 'dashboard', 'portfolio': portfolio}
    if not form.is_valid():
        ctx['data_error'] = _('Correct the date/currency filters below.')
        return ctx
    try:
        book = portfolio_book(portfolio)
        snap = snapshot(portfolio, currency, end, book)
    except (MissingData, ValidationError) as exc:
        ctx['data_error'] = str(exc)
        if isinstance(exc, MissingData):
            ctx['quote_issues'] = exc.checks
        return ctx
    ctx.update(snap=snap, book=book, allocation_chart=allocation_chart(snap))
    if with_history:
        try:
            frame = history(portfolio, currency, start, snap['asof'], book)
        except MissingData as exc:
            ctx.update(history_error=str(exc), historical_quote_issues=exc.checks)
        else:
            ctx['history'] = frame
            ctx['line_chart'] = line_chart(frame, currency)
            ctx['risk'] = portfolio_risk(frame, snap)
            ctx['period_return'] = float(frame['index'].iloc[-1] - 100) if not frame.empty else 0
    return ctx


@login_required
def dashboard(request):
    ctx = valuation_context(request)
    ctx['recent'] = (
        ctx['portfolio'].transactions.select_related('asset').order_by('-date', '-id')[:5]
    )
    return render(request, 'portfolio/dashboard.html', ctx)


@login_required
def holdings(request):
    ctx = valuation_context(request, with_history=False)
    ctx['page'] = 'holdings'
    return render(request, 'portfolio/holdings.html', ctx)


@login_required
def transactions(request):
    p = active(request)
    rows = p.transactions.select_related('asset').order_by('-date', '-id') if p else []
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ['date', 'kind', 'symbol', 'quantity', 'price', 'currency', 'fee', 'fx_to_try', 'memo']
        )
        for row in rows:
            # Neutralize spreadsheet formulas from user-entered text.
            memo = row.memo
            if memo.startswith(('=', '+', '-', '@', '\t', '\r')):
                memo = "'" + memo
            writer.writerow(
                [
                    row.date,
                    row.kind,
                    row.asset.symbol if row.asset else '',
                    row.quantity,
                    row.price,
                    row.currency,
                    row.fee,
                    row.fx_to_try,
                    memo,
                ]
            )
        return response
    return render(request, 'portfolio/transactions.html', {'rows': rows, 'page': 'transactions'})


@login_required
def transaction_edit(request, pk=None):
    instance = get_object_or_404(Transaction, pk=pk, portfolio__user=request.user) if pk else None
    p = instance.portfolio if instance else active(request)
    if not p:
        return redirect('dashboard')
    guided = instance is None and request.GET.get('onboarding') == '1'
    kind = request.GET.get('kind')
    initial = {'kind': kind} if instance is None and kind in ('deposit', 'buy') else None
    form = TransactionForm(request.POST or None, initial=initial, instance=instance, portfolio=p)
    if request.method == 'POST' and form.is_valid():
        row = form.save(commit=False)
        row.portfolio = p
        try:
            row.fx_to_try = portfolio_book(p).rate(row.currency, row.date)
            save_transaction(row)
            messages.success(
                request, _('Transaction saved. Portfolio balances have been recalculated.')
            )
            return redirect('ai_dashboard' if guided else 'transactions')
        except (ValidationError, MissingData) as exc:
            form.add_error(
                None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            )
    return render(
        request,
        'portfolio/form.html',
        {
            'form': form,
            'title': _('Edit transaction') if pk else _('Record a transaction'),
            'subtitle': _('Record cash deposits before entering fund or metal transactions.'),
            'page': 'transactions',
            'cancel_url': 'ai_dashboard' if guided else 'transactions',
            'no_priced_assets': not form.fields['asset'].queryset.exists(),
            'asset_options': [
                {'id': asset.pk, 'kind': asset.kind}
                for asset in form.fields['asset'].queryset
            ],
        },
    )


@login_required
@require_POST
def transaction_delete(request, pk):
    row = get_object_or_404(Transaction, pk=pk, portfolio__user=request.user)
    try:
        delete_transaction(row)
        messages.success(request, _('Transaction deleted and balances recalculated.'))
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('transactions')


@login_required
def compare(request):
    ctx = valuation_context(request)
    ctx['page'] = 'compare'
    benchmarks = Asset.objects.filter(kind='benchmark')
    ctx['benchmarks'] = benchmarks
    selected = request.GET.getlist('benchmark')
    if not selected and 'benchmark_choices' not in request.GET:
        selected = ['SP500', 'NASDAQ100', 'BTC']
    ctx['selected'] = selected
    if 'history' in ctx and not ctx['history'].empty:
        frame, f = ctx['history'], go.Figure()
        dates = [str(d) for d in frame.index]
        f.add_trace(
            go.Scatter(
                x=dates, y=frame['index'].tolist(), name=_('Your portfolio'), line=dict(width=3)
            )
        )
        rows = [{'name': _('Your portfolio'), 'return': ctx['period_return']}]
        errors = []
        for asset in benchmarks.filter(symbol__in=selected):
            try:
                series = benchmark_history(
                    asset, ctx['portfolio'].dataset, frame.index, ctx['currency'], ctx['book']
                )
                f.add_trace(
                    go.Scatter(x=dates, y=series.tolist(), name=asset.name, line=dict(width=2))
                )
                rows.append({'name': asset.name, 'return': float(series.iloc[-1] - 100)})
            except MissingData as exc:
                errors.append(str(exc))
        ctx.update(comparison_chart=chart(f, 390), comparison_rows=rows, comparison_errors=errors)
    return render(request, 'portfolio/compare.html', ctx)


@login_required
def news(request):
    portfolio = active(request)
    dataset = portfolio.dataset if portfolio else 'live'
    return render(
        request,
        'portfolio/news.html',
        {
            'page': 'news',
            'articles': NewsItem.objects.filter(dataset=dataset, kind='news')[:30],
            'archive_analysis': bool(portfolio and portfolio.archive_prices),
        },
    )


@login_required
def notes(request):
    return render(
        request,
        'portfolio/notes.html',
        {'page': 'notes', 'notes': Note.objects.filter(portfolio=active(request)).select_related('fund')},
    )


@login_required
def note_edit(request, pk=None):
    note = get_object_or_404(Note, pk=pk, portfolio__user=request.user) if pk else None
    form = NoteForm(request.POST or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        portfolio = note.portfolio if note else active(request)
        with transaction.atomic():
            item.portfolio = portfolio or Portfolio.objects.create(user=request.user, name='My portfolio')
            item.save()
        messages.success(request, _('Note saved.'))
        return redirect('notes')
    return render(
        request,
        'portfolio/form.html',
        {
            'page': 'notes',
            'form': form,
            'title': _('Edit note') if pk else _('Create a note'),
            'subtitle': _('Keep the reasoning behind your decisions.'),
            'cancel_url': 'notes',
        },
    )


@login_required
@require_POST
def note_delete(request, pk):
    get_object_or_404(Note, pk=pk, portfolio__user=request.user).delete()
    messages.success(request, _('Note deleted.'))
    return redirect('notes')


@login_required
def settings_view(request):
    portfolio = active(request)
    preferences = request.dashboard_preferences
    currency = request.GET.get('currency')
    if currency not in dict(CURRENCIES):
        currency = preferences.currency if preferences else 'TRY'
    try:
        asof = parse_date(request.GET.get('asof', ''))
    except ValueError:
        asof = None
    if asof and asof > date.today():
        asof = date.today()
    checks = []
    if portfolio:
        book = portfolio_book(portfolio)
        asof = asof or portfolio_valuation_date(portfolio, book)
        prices, rates = portfolio_quotes(portfolio, currency, asof, book)
        checks = [*prices.values(), *rates.values()]
    else:
        asof = asof or date.today()
    return render(
        request,
        'portfolio/settings.html',
        {
            'page': 'settings',
            'logs': SyncLog.objects.all()[:10] if request.user.is_staff else (),
            'currency': currency,
            'asof': asof,
            'currencies': CURRENCIES,
            'quote_checks': checks,
            'market_prices': Price.objects.filter(dataset='live').aggregate(count=Count('id'), latest=Max('date')),
            'market_rates': ExchangeRate.objects.filter(dataset='live').aggregate(count=Count('id'), latest=Max('date')),
            'providers': [
                {
                    'name': _('GoldAPI · spot metals'),
                    'configured': bool(os.getenv('GOLD_API_TOKEN')),
                    'variable': 'GOLD_API_TOKEN',
                },
                {
                    'name': _('Market API'),
                    'configured': bool(os.getenv('MARKET_API_URL')),
                    'variable': 'MARKET_API_URL / MARKET_API_KEY',
                },
                {
                    'name': 'NewsAPI',
                    'configured': bool(os.getenv('NEWS_API_KEY')),
                    'variable': 'NEWS_API_KEY',
                },
                {
                    'name': 'X / Twitter',
                    'configured': bool(os.getenv('X_BEARER_TOKEN')),
                    'variable': 'X_BEARER_TOKEN',
                },
            ],
        },
    )


@login_required
@require_POST
def demo_load(request):
    oldest_allowed = date.today() - timedelta(days=MAX_QUOTE_AGE_DAYS)
    if not Price.objects.filter(dataset='demo', date__gte=oldest_allowed).exists():
        seed_market()
    p = create_demo_portfolio(request.user)
    request.session['portfolio_id'] = p.id
    messages.success(
        request,
        _('Learning portfolio loaded. All market data and headlines in this workspace are synthetic.'),
    )
    return redirect('ai_dashboard' if request.POST.get('from_dashboard') == '1' else 'dashboard')


@login_required
@require_POST
def portfolio_switch(request):
    p = get_object_or_404(Portfolio, pk=request.POST.get('portfolio_id'), user=request.user)
    request.session['portfolio_id'] = p.id
    page = request.POST.get('return_page')
    if page in {
        'ai_dashboard', 'holdings', 'transactions', 'compare', 'analysis', 'model_lab', 'news', 'notes', 'settings',
    }:
        return redirect(page)
    return redirect('ai_dashboard' if request.POST.get('from_ai_dashboard') == '1' else 'dashboard')


@login_required
@transaction.atomic
def portfolio_create(request):
    guided = request.GET.get('onboarding') == '1'
    placeholder = None
    if guided:
        portfolios = request.user.portfolio_set.select_for_update()
        if portfolios.count() == 1:
            candidate = portfolios.first()
            if candidate.name == 'My portfolio' and not candidate.transactions.exists() and not candidate.note_set.exists():
                placeholder = candidate
    form = PortfolioForm(request.POST or None, instance=placeholder)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.user, p.dataset = request.user, 'live'
        p.save()
        request.session['portfolio_id'] = p.id
        if guided:
            return redirect(f"{reverse('transaction_new')}?kind=deposit&onboarding=1")
        return redirect('dashboard')
    return render(
        request,
        'portfolio/form.html',
        {
            'form': form,
            'title': _('Create a portfolio'),
            'subtitle': _('A new portfolio uses market data. Import prices before recording trades.'),
            'page': 'settings',
            'cancel_url': 'settings',
        },
    )


@login_required
def market_import_template(request):
    if not request.user.is_staff:
        return HttpResponse(_('Administrator access is required to modify shared market data.'), status=403)
    response = HttpResponse('type,symbol,date,value\r\n', content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="market-data-template.csv"'
    return response


@login_required
@require_POST
def market_import(request):
    if not request.user.is_staff:
        return HttpResponse(
            _('Administrator access is required to modify shared market data.'), status=403
        )
    upload = request.FILES.get('file')
    try:
        if not upload or not 0 < upload.size <= 5 * 1024 * 1024:
            raise ProviderError(_('Choose a nonempty CSV or JSON file up to 5 MB.'))
        content = upload.read().decode('utf-8-sig')
        name = upload.name.lower()
        if name.endswith('.csv'):
            rows, source = read_market_csv(content), 'CSV import'
        elif name.endswith('.json'):
            rows, source = json.loads(content), 'JSON import'
        else:
            raise ProviderError(_('Choose a file ending in .csv or .json.'))
        count = import_market(rows, source=source)
        message = ngettext(
            'Imported %(count)s market observation.', 'Imported %(count)s market observations.', count
        ) % {'count': count}
    except UnicodeDecodeError:
        message, status = _('The file must use UTF-8 encoding.'), 'error'
    except (json.JSONDecodeError, RecursionError):
        message, status = _('The file contains invalid or excessively nested JSON.'), 'error'
    except (ProviderError, csv.Error) as exc:
        message, status = str(exc), 'error'
    else:
        status = 'success'
    SyncLog.objects.create(provider='File import', status=status, message=message[:500])
    messages.add_message(request, messages.SUCCESS if status == 'success' else messages.ERROR, message)
    return redirect(reverse('settings') + '#market-import')
