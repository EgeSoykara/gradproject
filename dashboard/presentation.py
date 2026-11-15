from numbers import Real

import plotly.graph_objects as go

from portfolio.charts import COLORS, chart

TEXT = {
    'title': ('Portföy paneli', 'Portfolio dashboard'),
    'portfolio': ('Portföy', 'Portfolio'),
    'sample': ('Örnek veri', 'Example data'),
    'connected': ('Portföy verisi', 'Portfolio data'),
    'snapshot_date': ('USD kuru tarihi', 'USD rate date'),
    'language': ('Dil', 'Language'),
    'currency': ('Para birimi', 'Currency'),
    'profile': ('Profil', 'Profile'),
    'level': ('Görünüm', 'View'),
    'conservative': ('Muhafazakâr', 'Conservative'),
    'balanced': ('Dengeli', 'Balanced'),
    'aggressive': ('Agresif', 'Aggressive'),
    'beginner': ('Başlangıç', 'Beginner'),
    'expert': ('Uzman', 'Expert'),
    'choose_profile': ('Risk profilini seç', 'Choose your risk profile'),
    'profile_guide': (
        'Muhafazakâr daha düşük dalgalanmaya, dengeli orta düzey dalgalanmaya, agresif daha yüksek dalgalanmaya karşılık gelir.',
        'Conservative corresponds to lower volatility, balanced to moderate volatility and aggressive to higher volatility.',
    ),
    'monthly': ('Aylık katkı (TL)', 'Monthly contribution (TRY)'),
    'apply': ('Uygula', 'Apply'),
    'fixture': ('Örnek dosya', 'Example file'),
    'invalid': ('Panel ayarlarını kontrol edin.', 'Check the dashboard settings.'),
    'unavailable': ('Panel verisi şu anda yüklenemiyor.', 'Dashboard data is currently unavailable.'),
    'missing': ('Veri bulunmuyor.', 'Data unavailable.'),
    'insufficient': ('Yetersiz veri', 'Insufficient data'),
    'static_data': (
        'Örnek dosya sabit bir veri görüntüsüdür. Dil ve profil seçimi dosyadaki analizleri yeniden üretmez.',
        'The example file is a fixed snapshot. Language and profile selections do not regenerate its analysis.',
    ),
    'total': ('Toplam değer', 'Total value'),
    'cash': ('Nakit', 'Cash'),
    'protected': ('USD korumalı pay', 'USD-protective share'),
    'allocation': ('Alt kategori dağılımı', 'Allocation by subcategory'),
    'pie_note': (
        'Dosyadaki paylar %100 etmiyor. Grafik, payları kendi toplamına göre gösterir.',
        'The source weights do not total 100%. The chart shows each share of their sum.',
    ),
    'tracker': ('Birikim takibi', 'Savings tracker'),
    'months': ('Birikim süresi (ay)', 'Months of saving'),
    'invested': ('Yatırılan', 'Invested'),
    'value': ('Güncel değer', 'Current value'),
    'gap': ('Fark', 'Difference'),
    'real_tl': ('Reel TL', 'Real TRY'),
    'stay': ('Yatırım disiplinini koruma', 'Stay the course'),
    'savings': ('Birikim planı', 'Savings plan'),
    'sim_value': ('Portföy değeri (USD)', 'Portfolio value (USD)'),
    'sim_invested': ('Yatırılan tutar (USD)', 'Amount invested (USD)'),
    'robustness': ('Portföy sağlamlığı', 'Portfolio robustness'),
    'grade': ('Derece', 'Grade'),
    'stress_resilience': ('Kriz dayanıklılığı', 'Stress resilience'),
    'purchasing_power': ('Alım gücü', 'Purchasing power'),
    'forward_risk': ('İleriye dönük risk', 'Forward risk'),
    'diversification': ('Çeşitlendirme', 'Diversification'),
    'maximum': ('Azami puan', 'Maximum score'),
    'score': ('Puan', 'Score'),
    'scenarios': ('Kriz senaryoları', 'Crisis scenarios'),
    'scenario': ('Senaryo', 'Scenario'),
    'tl_change': ('TL değişimi', 'TRY change'),
    'usd_change': ('USD değişimi', 'USD change'),
    'comments': ('Yapay zekâ yorumları', 'AI comments'),
    'attention': ('Dikkat', 'Attention'),
    'info': ('Bilgi', 'Information'),
    'news': ('Portföy temalarına göre haberler', 'News by portfolio theme'),
    'positive': ('Pozitif', 'Positive'),
    'neutral': ('Nötr', 'Neutral'),
    'negative': ('Negatif', 'Negative'),
    'rebalance': ('Model sepet ile karşılaştırma', 'Model basket comparison'),
    'subcategory': ('Alt kategori', 'Subcategory'),
    'fund': ('Fon', 'Fund'),
    'current': ('Mevcut', 'Current'),
    'target': ('Model', 'Model'),
    'contribution': ('Bu ayın katkısı', 'This month’s contribution'),
    'cash_example': ('Nakit için örnek dağılım', 'Example cash allocation'),
    'funds': ('Fon kartları', 'Fund cards'),
    'risk': ('Risk seviyesi', 'Risk level'),
    'fund_news': ('Haber durumu', 'News status'),
    'percentile': ('Yüzdelik dilim', 'Percentile'),
    'short': ('1 hafta', '1 week'),
    'medium': ('1 ay', '1 month'),
    'long': ('3 ay', '3 months'),
    'strong': ('Güçlü', 'Strong'),
    'weak': ('Zayıf', 'Weak'),
}


def localized(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get('tr') or value.get('en')
    return value


def copy_blocks(section, lang):
    texts = section.get('texts') or section
    version = texts.get(lang) or texts.get('tr') or texts.get('en') or {}
    return {
        'summary': (
            version.get('summary') or section.get(f'summary_{lang}')
            or localized(section.get('summary'), lang)
        ),
        'details': (
            version.get('details') or section.get(f'details_{lang}')
            or localized(section.get('details'), lang)
        ),
        'disclaimer': localized(texts.get('disclaimer') or section.get('disclaimer'), lang),
    }


def portfolio_context(section, currency, labels):
    selected = section.get(f'total_value_{currency.lower()}')
    cash = section.get('cash_balance')
    cash_currency = section.get('cash_currency') or (
        'TRY' if section.get('usd_rate_date') else section.get('base_currency', 'TRY')
    )
    source_total = section.get(f'total_value_{cash_currency.lower()}')
    if currency != cash_currency and isinstance(cash, Real) and selected is not None and source_total:
        cash, cash_currency = cash * selected / source_total, currency
    allocation = section.get('allocation_by_subcategory') or {}
    pie = None
    if allocation and sum(allocation.values()) > 0:
        pie = chart(go.Figure(go.Pie(
            labels=list(allocation), values=list(allocation.values()), hole=0.68,
            textinfo='none', sort=False, hovertemplate='%{label}<extra></extra>',
            marker={'colors': COLORS, 'line': {'color': 'white', 'width': 2}},
        )).update_layout(showlegend=False), 250)
    tracker = section.get('savings_tracker') or {}
    tracker_rows = [
        (unit, tracker.get(f'total_invested_{suffix}'), tracker.get(f'current_value_{suffix}'),
         tracker.get(f'gap_{suffix}'), tracker.get(f'gap_{suffix}_pct'))
        for unit, suffix in [('TRY', 'tl'), ('USD', 'usd'), (labels['real_tl'], 'real_tl')]
    ] if tracker else []
    return {
        'total': selected,
        'cash': cash,
        'cash_currency': cash_currency,
        'others': [(c, section.get(f'total_value_{c.lower()}'))
                   for c in ('TRY', 'USD', 'EUR', 'GBP') if c != currency],
        'allocations': [(name, value, COLORS[i % len(COLORS)])
                        for i, (name, value) in enumerate(allocation.items())],
        'pie_note': bool(pie) and abs(sum(allocation.values()) - 100) > 0.2,
        'pie': pie,
        'protected': section.get('usd_protective_share_pct'),
        'protected_text': section.get('usd_protective_share_text'),
        'as_of': section.get('usd_rate_date'),
        'months': tracker.get('months_count'),
        'tracker_rows': tracker_rows,
    }


def savings_context(section, labels):
    trajectory = (section.get('user_basket') or {}).get('trajectory') or []
    figure = None
    if section.get('is_active') is not False and trajectory:
        dates = [point['date'] for point in trajectory]
        figure = go.Figure([
            go.Scatter(x=dates, y=[x.get('portfolio_usd') for x in trajectory], mode='lines',
                       name=labels['sim_value'], line={'width': 3}),
            go.Scatter(x=dates, y=[x.get('invested_usd') for x in trajectory], mode='lines',
                       name=labels['sim_invested'], line={'color': COLORS[2], 'dash': 'dot'}),
        ])
        figure.update_yaxes(tickprefix='$', automargin=True)
    return {
        'line': chart(figure, 300) if figure else None,
        'monthly': section.get('monthly_contribution_tl'),
        'window': section.get('simulation_window'),
    }


def robustness_context(section, lang, labels):
    score = section.get('overall_score')
    caps = {'stress_resilience': 35, 'purchasing_power': 25, 'forward_risk': 20, 'diversification': 20}
    subs = section.get('sub_scores') or {}
    parts = [(labels[key], subs[key], maximum) for key, maximum in caps.items() if key in subs]
    bar = None
    if parts:
        names, values, limits = zip(*parts)
        bar = chart(go.Figure([
            go.Bar(y=list(names), x=list(limits), orientation='h', name=labels['maximum'],
                   marker_color='#e6eee8'),
            go.Bar(y=list(names), x=list(values), orientation='h', name=labels['score'],
                   marker_color=COLORS[0], text=[f'{v:g}/{m}' for v, m in zip(values, limits)],
                   textposition='inside'),
        ]).update_layout(barmode='overlay').update_yaxes(autorange='reversed', automargin=True), 250)
    scenarios = [
        (entry.get(f'name_{lang}') or localized(entry.get('name') or entry.get('scenario'), lang),
         entry.get('portfolio_shock_tl_pct'), entry.get('portfolio_shock_usd_pct'))
        for entry in section.get('scenarios') or []
    ]
    return {'score': score, 'grade': section.get('grade'), 'bar': bar, 'scenarios': scenarios}


def rebalance_context(section, lang, labels):
    target = section.get('target_comparison') or {}
    contribution = section.get('contribution_only') or {}
    categories = (
        target.get('by_subcategory') or target.get('subcategory_comparison')
        or section.get('subcategory_comparison') or []
    )
    funds = target.get('comparison') or target.get('fund_comparison') or []
    tables = [
        [(entry.get(field), entry.get('current_weight_pct'), entry.get('target_weight_pct'),
          entry.get('difference_pct')) for entry in table]
        for field, table in [('subcategory', categories), ('symbol', funds)]
    ]
    grouped = None
    if tables[0]:
        names, current, model, _ = zip(*tables[0])
        grouped = chart(go.Figure([
            go.Bar(x=list(names), y=list(current), name=labels['current']),
            go.Bar(x=list(names), y=list(model), name=labels['target'], marker_color=COLORS[2]),
        ]).update_layout(barmode='group').update_xaxes(automargin=True)
          .update_yaxes(ticksuffix='%', automargin=True), 300)
    cash = section.get('cash_allocation') or section.get('cash_example') or []
    if isinstance(cash, dict):
        cash = cash.get('allocations') or []
    return {
        'tables': [(labels['subcategory'], tables[0]), (labels['fund'], tables[1])],
        'grouped': grouped,
        'contribution': contribution.get('allocations') or [],
        'cash': [
            {**entry, 'allocated_amount_tl': entry.get('allocated_amount_tl', entry.get('suggested_amount'))}
            for entry in cash
        ],
        'description': target.get(f'description_{lang}'),
        'contribution_description': contribution.get(f'description_{lang}'),
    }


def fund_context(fund, lang, labels):
    context = {**fund, **copy_blocks(fund, lang), 'chips': []}
    if fund.get('is_eligible') is False or fund.get('is_suspended'):
        context['ineligible'] = True
        context['ineligibility_reason'] = fund.get(f'ineligibility_reason_{lang}') or fund.get('ineligibility_reason')
        return context
    view = fund.get('horizons') or fund.get('gru_view') or {}
    context['agreement'] = localized(fund.get('seed_agreement_text') or view.get('seed_agreement_text'), lang)
    for horizon, modern, legacy in [
        ('short', 'short_5d', 'horizon_5d'),
        ('medium', 'medium_21d', 'horizon_21d'),
        ('long', 'long_63d', 'horizon_63d'),
    ]:
        data = view.get(modern) or view.get(legacy) or {}
        rank = data.get('percentile', data.get('subcategory_percentile'))
        status = data.get(f'outlook_{lang}') or localized(data.get('status') or data.get('label'), lang)
        color = {'güçlü': 'strong', 'strong': 'strong', 'zayıf': 'weak', 'weak': 'weak'}.get(
            (status or '').lower(), 'neutral'
        )
        if not status and isinstance(rank, Real):
            color = 'strong' if rank >= 67 else 'weak' if rank <= 33 else 'neutral'
            status = labels[color]
        context['chips'].append({
            'label': labels[horizon], 'status': status or '—', 'color': color,
            'rank': rank, 'agreement': data.get(f'seed_agreement_text_{lang}')
            or localized(data.get('seed_agreement_text'), lang),
        })
    return context


def news_context(section, lang, labels):
    themes = section.get('themes') or section.get('theme_status') or []
    if not themes:
        headlines = section.get('top_headlines_per_theme') or {}
        themes = [
            {'theme': theme, 'top_headline': headlines.get(theme)}
            for theme in section.get('portfolio_themes') or []
        ]
    if isinstance(themes, dict):
        themes = [dict(entry, theme=key) if isinstance(entry, dict) else {'theme': key, 'status': entry}
                  for key, entry in themes.items()]
    for theme in themes:
        status = localized(theme.get('status'), lang)
        insufficient = (status or '').lower().replace('_', ' ') in {'insufficient data', 'yetersiz veri'}
        insufficient |= status is None and section.get('label') == 'insufficient_data'
        headline = theme.get('top_headline') or next(iter(theme.get('top_headlines') or []), {})
        counts = theme.get('counts') or {}
        yield {
            'name': localized(theme.get('theme') or theme.get('name'), lang),
            'status': theme.get(f'status_{lang}') or (labels['insufficient'] if insufficient else status),
            'insufficient': insufficient,
            'counts': [(labels[key], counts.get(key, counts.get(key[:3], theme.get(f'{key}_count'))))
                       for key in ('positive', 'neutral', 'negative')],
            'headline': {'title': headline} if isinstance(headline, str) else headline,
        }


def dashboard_context(payload, lang, currency):
    labels = dashboard_labels(lang)
    sections = {key: payload.get(key) or {} for key in
                ('portfolio', 'savings_plan', 'robustness', 'rebalancing', 'stay_the_course')}
    news = payload.get('news') or {}
    if isinstance(news, list):
        news = {'themes': news}
    elif not news and payload.get('theme_status'):
        news = {'theme_status': payload['theme_status']}
    comments = payload.get('ai_comments') or []
    comment_section = comments if isinstance(comments, dict) else {}
    return {
        'payload': payload,
        't': labels,
        'portfolio_data': {**copy_blocks(sections['portfolio'], lang),
                           **portfolio_context(sections['portfolio'], currency, labels)},
        'savings_data': {**copy_blocks(sections['savings_plan'], lang),
                         **savings_context(sections['savings_plan'], labels)},
        'robustness_data': {**copy_blocks(sections['robustness'], lang),
                            **robustness_context(sections['robustness'], lang, labels)},
        'rebalancing_data': {**copy_blocks(sections['rebalancing'], lang),
                            **rebalance_context(sections['rebalancing'], lang, labels)},
        'stay': copy_blocks(sections['stay_the_course'], lang) if sections['stay_the_course'] else None,
        'news_data': {
            **copy_blocks(news, lang), 'themes': list(news_context(news, lang, labels)),
            'status': news.get(f'label_{lang}'),
            'counts': [(labels[label], (news.get('counts') or {}).get(key))
                       for label, key in [('positive', 'pos'), ('neutral', 'neu'), ('negative', 'neg')]]
            if news.get('label') != 'insufficient_data' else [],
        },
        'comments_data': {**copy_blocks(comment_section, lang), 'items': [
            {**entry, 'display': entry.get(f'text_{lang}') or entry.get('text_tr') or entry.get('text_en'),
             'title': entry.get(f'title_{lang}')}
            for entry in (comment_section.get('items', []) if comment_section else comments)
        ]},
        'funds': [fund_context(fund, lang, labels) for fund in payload.get('fund_cards') or []],
    }


def dashboard_labels(lang):
    language_index = 1 if lang == 'en' else 0
    return {key: values[language_index] for key, values in TEXT.items()}
