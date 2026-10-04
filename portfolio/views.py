import csv
import os
from datetime import date
from decimal import Decimal, InvalidOperation

import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .charts import allocation_chart, chart, line_chart
from .context import workspace
from .forms import NoteForm, PortfolioForm, RangeForm, RegisterForm, TransactionForm
from .models import Asset, ModelRun, NewsItem, Note, Portfolio, Price, SyncLog, Transaction
from .services.analytics import correlation_matrix, risk_metrics, stress_tests
from .services.demo import create_demo_portfolio
from .services.ledger import delete_transaction, save_transaction
from .services.providers import ProviderError, import_market, read_market_csv
from .services.valuation import MarketBook, MissingData, benchmark_history, history, snapshot


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
        return redirect('dashboard')
    return render(request, 'registration/register.html', {'form': form})


def selection(request):
    form = RangeForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
        return (
            form,
            data.get('currency') or 'TRY',
            data.get('start'),
            data.get('end') or date.today(),
        )
    return form, 'TRY', None, date.today()


def valuation_context(request, with_history=True):
    portfolio = active(request)
    if portfolio is None:
        portfolio = Portfolio.objects.create(user=request.user, name='My portfolio')
    form, currency, start, end = selection(request)
    ctx = {'range_form': form, 'currency': currency, 'page': 'dashboard', 'portfolio': portfolio}
    if not form.is_valid():
        ctx['data_error'] = 'Correct the date/currency filters below.'
        return ctx
    try:
        book = MarketBook(portfolio.dataset)
        snap = snapshot(portfolio, currency, end, book)
        ctx.update(snap=snap, book=book)
        if with_history:
            frame = history(portfolio, currency, start, end, book)
            ctx['history'] = frame
            ctx['line_chart'] = line_chart(frame, currency)
            weights = [h['weight'] / 100 for h in snap['holdings']]
            if snap['total']:
                weights.append(float(snap['cash'] / snap['total']))
            ctx['risk'] = risk_metrics(frame['return'].iloc[1:], weights)
            ctx['period_return'] = float(frame['index'].iloc[-1] - 100) if not frame.empty else 0
        ctx['allocation_chart'] = allocation_chart(snap)
    except (MissingData, ValidationError) as exc:
        ctx['data_error'] = str(exc)
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
    form = TransactionForm(request.POST or None, instance=instance, portfolio=p)
    if request.method == 'POST' and form.is_valid():
        row = form.save(commit=False)
        row.portfolio = p
        try:
            row.fx_to_try = MarketBook(p.dataset).rate(row.currency, row.date)
            save_transaction(row)
            messages.success(
                request, 'Transaction saved. Portfolio balances have been recalculated.'
            )
            return redirect('transactions')
        except (ValidationError, MissingData) as exc:
            form.add_error(
                None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            )
    return render(
        request,
        'portfolio/form.html',
        {
            'form': form,
            'title': 'Edit transaction' if pk else 'Record a transaction',
            'subtitle': 'Your ledger is the source of truth. Start with a deposit before buying assets.',
            'page': 'transactions',
            'cancel_url': 'transactions',
        },
    )


@login_required
@require_POST
def transaction_delete(request, pk):
    row = get_object_or_404(Transaction, pk=pk, portfolio__user=request.user)
    try:
        delete_transaction(row)
        messages.success(request, 'Transaction deleted and balances recalculated.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('transactions')


@login_required
def compare(request):
    ctx = valuation_context(request)
    ctx['page'] = 'compare'
    benchmarks = Asset.objects.filter(kind='benchmark')
    ctx['benchmarks'] = benchmarks
    selected = request.GET.getlist('benchmark') or ['SP500', 'NASDAQ100', 'BTC']
    ctx['selected'] = selected
    if 'history' in ctx and not ctx['history'].empty:
        frame, f = ctx['history'], go.Figure()
        dates = [str(d) for d in frame.index]
        f.add_trace(
            go.Scatter(
                x=dates, y=frame['index'].tolist(), name='Your portfolio', line=dict(width=3)
            )
        )
        rows = [{'name': 'Your portfolio', 'return': ctx['period_return']}]
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
def analysis(request):
    ctx = valuation_context(request)
    ctx['page'] = 'analysis'
    if 'snap' in ctx:
        ctx['scenarios'] = stress_tests(ctx['snap'], ctx['book']) if ctx['snap']['total'] else []
        try:
            corr = correlation_matrix(ctx['snap'], ctx['book'])
            if not corr.empty:
                ctx['correlation_chart'] = chart(
                    go.Figure(
                        go.Heatmap(
                            z=corr.values.tolist(),
                            x=list(corr.columns),
                            y=list(corr.index),
                            zmin=-1,
                            zmax=1,
                            colorscale=[[0, '#d89587'], [0.5, '#fafbf9'], [1, '#147d64']],
                        )
                    ),
                    320,
                )
        except MissingData:
            ctx['correlation_error'] = 'Correlation needs aligned historical exchange rates.'
    risk_level = request.GET.get('risk', 'balanced')
    if risk_level not in ('cautious', 'balanced', 'growth'):
        risk_level = 'balanced'
    ctx['risk_level'] = risk_level
    current_cash = Decimal(0)
    try:
        if 'book' in ctx:
            current_cash = snapshot(ctx['portfolio'], ctx['currency'], book=ctx['book'])['cash']
    except MissingData:
        pass
    try:
        budget = Decimal(request.GET.get('budget', str(current_cash)))
        if not budget.is_finite() or budget < 0 or budget > Decimal('1e12'):
            raise ValueError
    except (InvalidOperation, ValueError):
        budget = Decimal(0)
        ctx['budget_error'] = 'Enter a finite budget between 0 and 1 trillion.'
    ctx['budget'] = budget
    candidates, seen = [], set()
    for run in ModelRun.objects.filter(dataset=ctx['portfolio'].dataset).select_related('asset'):
        if run.asset_id in seen:
            continue
        seen.add(run.asset_id)
        penalty = {'cautious': 1.5, 'balanced': 0.75, 'growth': 0.25}[risk_level]
        try:
            if 'book' not in ctx:
                continue
            today = date.today()
            price = ctx['book'].asset_try(run.asset_id, today) / ctx['book'].rate(
                ctx['currency'], today
            )
            stale = (today - run.data_end).days > 7
            available = min(budget, current_cash)
            candidates.append(
                {
                    'run': run,
                    'prediction_pct': run.prediction * 100,
                    'rank': run.prediction - penalty * run.metrics['rmse'],
                    'max_units': available / price if price and not stale else 0,
                    'stale': stale,
                    'beats_baseline': run.metrics['mae'] < run.metrics['baseline_mae'],
                }
            )
        except MissingData:
            continue
    candidates.sort(key=lambda c: c['rank'], reverse=True)
    ctx['candidates'] = candidates
    if candidates:
        run = candidates[0]['run']
        curve = run.metrics.get('test_curve', [])
        f = go.Figure()
        for key, name in [('strategy', 'Model long/cash'), ('baseline', 'Buy and hold')]:
            f.add_trace(
                go.Scatter(x=[r['date'] for r in curve], y=[r[key] for r in curve], name=name)
            )
        ctx['backtest_chart'] = chart(f)
        ctx['featured_model'] = run
    return render(request, 'portfolio/analysis.html', ctx)


@login_required
def news(request):
    p = active(request)
    dataset = p.dataset if p else 'live'
    items = NewsItem.objects.filter(dataset=dataset)
    social = items.filter(kind='social')
    counts = {
        'Positive': social.filter(sentiment__gte=0.05).count(),
        'Neutral': social.filter(sentiment__gt=-0.05, sentiment__lt=0.05).count(),
        'Negative': social.filter(sentiment__lte=-0.05).count(),
    }
    return render(
        request,
        'portfolio/news.html',
        {
            'page': 'news',
            'articles': items.filter(kind='news')[:30],
            'posts': social[:12],
            'sample_count': social.count(),
            'counts': counts,
            'latest_post': social.first(),
            'sentiment_chart': chart(
                go.Figure(
                    go.Bar(
                        x=list(counts),
                        y=list(counts.values()),
                        marker_color=['#147d64', '#97a59d', '#bd6353'],
                    )
                ),
                230,
            ),
        },
    )


@login_required
def notes(request):
    return render(
        request,
        'portfolio/notes.html',
        {'page': 'notes', 'notes': Note.objects.filter(portfolio=active(request))},
    )


@login_required
def note_edit(request, pk=None):
    note = get_object_or_404(Note, pk=pk, portfolio__user=request.user) if pk else None
    form = NoteForm(request.POST or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.portfolio = note.portfolio if note else active(request)
        item.save()
        messages.success(request, 'Note saved.')
        return redirect('notes')
    return render(
        request,
        'portfolio/form.html',
        {
            'page': 'notes',
            'form': form,
            'title': 'Edit note' if pk else 'Create a note',
            'subtitle': 'Keep the reasoning behind your decisions.',
            'cancel_url': 'notes',
        },
    )


@login_required
@require_POST
def note_delete(request, pk):
    get_object_or_404(Note, pk=pk, portfolio__user=request.user).delete()
    messages.success(request, 'Note deleted.')
    return redirect('notes')


@login_required
def settings_view(request):
    return render(
        request,
        'portfolio/settings.html',
        {
            'page': 'settings',
            'logs': SyncLog.objects.all()[:10],
            'price_count': Price.objects.filter(dataset='live').count(),
            'providers': [
                {
                    'name': 'GoldAPI · spot metals',
                    'configured': bool(os.getenv('GOLD_API_TOKEN')),
                    'variable': 'GOLD_API_TOKEN',
                },
                {
                    'name': 'Market API',
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
    if not Price.objects.filter(dataset='demo').exists():
        messages.error(request, 'Run python manage.py seed_demo first, then try again.')
        return redirect('settings')
    p = create_demo_portfolio(request.user)
    request.session['portfolio_id'] = p.id
    messages.success(
        request,
        'Learning portfolio loaded. All market data and headlines in this workspace are synthetic.',
    )
    return redirect('dashboard')


@login_required
@require_POST
def portfolio_switch(request):
    p = get_object_or_404(Portfolio, pk=request.POST.get('portfolio_id'), user=request.user)
    request.session['portfolio_id'] = p.id
    return redirect('dashboard')


@login_required
def portfolio_create(request):
    form = PortfolioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.user, p.dataset = request.user, 'live'
        p.save()
        request.session['portfolio_id'] = p.id
        return redirect('dashboard')
    return render(
        request,
        'portfolio/form.html',
        {
            'form': form,
            'title': 'Create a portfolio',
            'subtitle': 'A new portfolio uses market data. Import prices before recording trades.',
            'page': 'settings',
            'cancel_url': 'settings',
        },
    )


@login_required
@require_POST
def market_import(request):
    # Market quotes are shared across accounts, so only the local administrator can import them.
    if not request.user.is_staff:
        return HttpResponse(
            'Administrator access is required to modify shared market data.', status=403
        )
    upload = request.FILES.get('file')
    try:
        if not upload or upload.size > 5 * 1024 * 1024:
            raise ProviderError('Choose a CSV file smaller than 5 MB.')
        text = upload.read().decode('utf-8-sig')
        count = import_market(read_market_csv(text))
        messages.success(request, f'Imported {count} market observations.')
    except (UnicodeDecodeError, ProviderError) as exc:
        messages.error(request, str(exc))
    return redirect('settings')
