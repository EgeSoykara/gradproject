from numbers import Real

import plotly.graph_objects as go

from portfolio.charts import COLORS, chart

TEXT = {
    'title': ('Portföy paneli', 'Portfolio dashboard'),
    'portfolio': ('Portföy', 'Portfolio'),
    'sample': ('Örnek veri', 'Example data'),
    'connected': ('Analiz motoru', 'Analysis engine'),
    'ledger': ('Kayıtlı portföy', 'Recorded portfolio'),
    'demo_workspace': ('Deneme portföyü', 'Learning portfolio'),
    'welcome': ('Portföyüne nasıl başlamak istersin?', 'How would you like to start?'),
    'explore_demo': ('Demoyu keşfet', 'Explore the demo'),
    'explore_demo_help': ('İşlem kaydetmeyi ve paneli örnek fiyatlarla dene.', 'Try the dashboard and record transactions using example prices.'),
    'create_portfolio': ('Kendi portföyümü oluştur', 'Create my portfolio'),
    'create_portfolio_help': ('Portföyüne ad ver, nakit ekle ve ilk alışını kaydet.', 'Name your portfolio, add cash and record your first purchase.'),
    'add_cash': ('Nakit ekle', 'Add cash'),
    'first_buy': ('İlk alışını kaydet', 'Record your first purchase'),
    'first_buy_help': ('Nakit kaydın hazır. Alışını ekleyince varlığın bu panelde görünecek.', 'Your cash is recorded. Your holding will appear here after you save your purchase.'),
    'open_example': ('Hazır analiz örneğini aç', 'Open a prepared analysis example'),
    'return_workspace': ('Kendi portföyüne dön', 'Return to your portfolio'),
    'positions': ('Portföydeki varlıklar', 'Portfolio holdings'),
    'view_positions': ('Varlıklarımı aç', 'Open my holdings'),
    'manage_data': ('Veri ve ayarlara git', 'Go to data and settings'),
    'archive_analysis_unavailable': ('Arşiv analizi şu anda kullanılamıyor.', 'The archive analysis is currently unavailable.'),
    'preferences': ('Panel ayarları', 'Dashboard settings'),
    'overview': ('Portföy özeti', 'Portfolio summary'),
    'portfolio_details': ('Değer ve birikim takibi', 'Value and savings tracker'),
    'highlights': ('Öne çıkan yorumlar', 'Key insights'),
    'all_comments': ('Tüm yorumları gör', 'See all insights'),
    'analysis_sections': ('Portföy analizi', 'Portfolio analysis'),
    'planning_sections': ('Birikim ve planlama', 'Savings and planning'),
    'expert_tools': ('Uzman araçları', 'Expert tools'),
    'correlation': ('Varlıklar birlikte nasıl hareket ediyor?', 'How do your holdings move together?'),
    'correlation_hint': ('Portföy varlıklarının geçmiş fiyat ilişkisi', 'Historical price relationships between holdings'),
    'correlation_sample': ('Bu örnek portföy dosyası fiyat serisi içermiyor. Korelasyon için fiyat geçmişi olan bir portföy aç.', 'This example portfolio file contains no price series. Open a portfolio with price history to see correlation.'),
    'correlation_missing': ('Korelasyon için en az iki varlığın ortak tarihlerde hesaplanmış ve değişkenlik gösteren en az 30 getirisi gerekiyor.', 'Correlation requires at least two holdings with 30 overlapping, varying returns.'),
    'correlation_note': ('+1, getirilerin birlikte hareket ettiğini gösterir. −1 ters yönü, 0 ise zayıf bir doğrusal ilişkiyi gösterir.', '+1 means returns tend to move together. −1 means they tend to move in opposite directions. 0 means a weak linear relationship.'),
    'correlation_period': ('Ortak tarihlerdeki TRY getirileri', 'TRY returns on shared dates'),
    'robustness_hint': ('Kriz senaryoları ve risk puanları', 'Crisis scenarios and risk scores'),
    'comments_hint': ('Portföyündeki güçlü yönler ve riskler', 'Strengths and risks in your portfolio'),
    'news_hint': ('Fonlarını ilgilendiren haberlerin etkisi', 'News sentiment for the funds you hold'),
    'funds_hint': ('Her fon için 1 hafta, 1 ay ve 3 ay görünümü', '1-week, 1-month and 3-month outlooks'),
    'value_hint': ('Diğer para birimleri ve yatırdığın tutar', 'Other currencies and invested amounts'),
    'savings_hint': ('Düzenli katkıların geçmişteki seyri', 'How regular contributions would have performed'),
    'rebalance_hint': ('Portföyün ile model dağılımı arasındaki fark', 'Differences between your portfolio and the model allocation'),
    'saved': ('Panel ayarların kaydedildi.', 'Dashboard settings saved.'),
    'beginner_help': ('Günlük dille kısa açıklamalar.', 'Short explanations in plain language.'),
    'expert_help': ('Ölçümler, karşılaştırmalar ve yöntem ayrıntıları.', 'Metrics, comparisons and methodology.'),
    'conservative_help': ('Daha düşük dalgalanmayı önceler.', 'Prioritizes smaller swings in value.'),
    'balanced_help': ('Dalgalanma ve büyüme arasında denge arar.', 'Balances volatility and growth.'),
    'aggressive_help': ('Büyüme için daha büyük dalgalanmayı kabul eder.', 'Accepts bigger swings in pursuit of growth.'),
    'source_notes': ('Kaynak analizi ve yöntem', 'Source analysis and method'),
    'risk_explain': ('Bu puanı kriz senaryoları, alım gücü, ileriye dönük risk ve çeşitlendirme birlikte belirler.', 'The score combines crisis scenarios, purchasing power, forward-looking risk and diversification.'),
    'weakest_scenario': ('Geçmiş senaryolardaki en düşük değişim', 'Lowest change across historical scenarios'),
    'scenario_explain': ('Bugünkü portföy dağılımı geçmiş krizlere uygulandığında, aşağıdaki senaryo seçili para birimindeki en düşük değişimi gösteriyor.', 'This is the lowest change in the stated currency when today’s portfolio mix is applied to past crises.'),
    'risk_components': ('Puanı oluşturan ölçümler', 'What makes up the score'),
    'risk_estimates': ('Modelin risk tahminleri', 'Model risk estimates'),
    'loss_real_12m': ('12 ayda alım gücü kaybı olasılığı', '12-month probability of purchasing-power loss'),
    'loss_usd_12m': ('12 ayda dolar bazında kayıp olasılığı', '12-month probability of a loss in USD'),
    'volatility_21d': ('21 günlük dalgalanma tahmini', '21-day volatility estimate'),
    'tracker_explain': ('Yatırdığın para ile portföyün bugünkü değeri arasındaki farkı gör. Sonuç, burada belirtilen para biriminde hesaplanır.', 'Compare what you put in with what your portfolio is worth today. The figures use the currency shown here.'),
    'currency_details': ('Diğer para birimleri ve kur etkisi', 'Other currencies and currency exposure'),
    'savings_explain': ('Her ay aynı tutarı yatırsaydın geçmişte ne olurdu? Düz çizgi yatırımlarının değerini, kesikli çizgi ise biriken katkı tutarını gösteriyor.', 'What would have happened if you had invested the same amount every month? The solid line shows the investment value. The dashed line shows your total contributions.'),
    'simulation_result': ('Simülasyon sonunda', 'At the end of the simulation'),
    'news_explain': ('Bu özet, fonlarınla ilgili haberlerin tonunu gösterir. Olumlu haber, fonun fiyatının yükseleceğini göstermez.', 'This shows the tone of news relevant to your funds. Positive coverage does not predict a price increase.'),
    'funds_explain': ('Güçlü ve zayıf ifadeleri, fonun benzer fonlara göre modeldeki konumunu anlatır.', 'Strong and weak describe where a fund ranks among similar funds in the model.'),
    'outperform': ('Benzer fonların ortanca getirisini aşma olasılığı', 'Probability of beating the median return among peers'),
    'tested_ic': ('Testte sıralama korelasyonu (IC)', 'Test rank correlation (IC)'),
    'rebalance_explain': ('Portföyündeki payları seçtiğin örnek sepetle karşılaştır. Çubuklar her varlık grubunun toplam içindeki payını gösterir.', 'Compare your mix with the example basket for your selected profile. The bars show each asset group’s share of the total.'),
    'reference_date': ('Örnek sepetin tarihi', 'Example basket date'),
    'reference_note': ('Örnek portföyün geçmiş değerleri sabit. Seçtiğin profil, karşılaştırma için kullanılan model sepetini değiştirir.', 'The example portfolio’s historical values are fixed. Your profile changes the reference basket used for comparison.'),
    'contribution_explain': ('Mevcut varlıkları koruyarak yeni katkının nasıl dağıtılabileceğini gösteren bir örnek.', 'An example of how a new contribution could be divided while keeping existing holdings.'),
    'all_allocations': ('Tüm varlık gruplarını karşılaştır', 'Compare all asset groups'),
    'fund_allocations': ('Fon bazında ağırlıklar', 'Weights by fund'),
    'tracker_missing': ('Yatırılan tutarı hesaplamak için portföyde katkı kayıtları gerekli.', 'Contribution records are needed to calculate how much you put in.'),
    'savings_missing': ('Bu portföy için gösterilebilecek bir aylık katkı simülasyonu yok.', 'There is no monthly contribution simulation for this portfolio.'),
    'snapshot_date': ('USD kuru tarihi', 'USD rate date'),
    'currency': ('Para birimi', 'Currency'),
    'profile': ('Profil', 'Profile'),
    'level': ('Görünüm', 'View'),
    'conservative': ('Muhafazakâr', 'Conservative'),
    'balanced': ('Dengeli', 'Balanced'),
    'aggressive': ('Agresif', 'Aggressive'),
    'beginner': ('Başlangıç', 'Beginner'),
    'expert': ('Uzman', 'Expert'),
    'monthly': ('Aylık katkı (TL)', 'Monthly contribution (TRY)'),
    'apply': ('Uygula', 'Apply'),
    'fixture': ('Örnek portföy', 'Example portfolio'),
    'fixture_example': ('Temel örnek', 'Basic example'),
    'invalid': ('Panel ayarlarını kontrol edin.', 'Check the dashboard settings.'),
    'unavailable': ('Panel verisi şu anda yüklenemiyor.', 'Dashboard data is currently unavailable.'),
    'missing': ('Veri bulunmuyor.', 'Data unavailable.'),
    'insufficient': ('Yetersiz veri', 'Insufficient data'),
    'total': ('Toplam değer', 'Total value'),
    'cash': ('Nakit', 'Cash'),
    'protected': ('USD korumalı pay', 'USD-protective share'),
    'allocation': ('Varlık dağılımı', 'Asset allocation'),
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
    'robustness': ('Portföy sağlamlık puanı', 'Portfolio robustness score'),
    'robustness_archive': ('Arşiv puanı', 'Archived score'),
    'robustness_engine': ('Yerel analiz motoru', 'Local analysis engine'),
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

ALLOCATION_LABELS = {
    'Borclanma-Doviz': ('Döviz borçlanma araçları', 'Foreign-currency bonds'),
    'Borclanma-TL': ('TL borçlanma araçları', 'TRY bonds'),
    'Cash': ('Nakit', 'Cash'),
    'Değişken': ('Değişken fonlar', 'Flexible funds'),
    'FonSepeti-Yabanci': ('Yabancı fon sepetleri', 'Foreign fund baskets'),
    'Hisse-Yabanci': ('Yabancı hisse senetleri', 'Foreign equities'),
    'Hisse-Yerli': ('Yerli hisse senetleri', 'Turkish equities'),
    'Katilim-Diger': ('Diğer katılım fonları', 'Other participation funds'),
    'Kiymetli-Maden': ('Kıymetli madenler', 'Precious metals'),
    'Nakit': ('Nakit', 'Cash'),
    'Nakit / Cash': ('Nakit', 'Cash'),
    'Para Piyasası': ('Para piyasası', 'Money market'),
}

NEWS_THEME_LABELS = {
    'Interest_Rates_CBRT': ('Faiz ve Merkez Bankası', 'Interest rates and central bank'),
    'Precious_Metals': ('Kıymetli madenler', 'Precious metals'),
    'Currency_FX': ('Döviz kurları', 'Exchange rates'),
    'Inflation': ('Enflasyon', 'Inflation'),
}

COMMENT_EXPLANATIONS = {
    'fx_protection': ('Döviz kuru değiştiğinde bazı varlıklar portföyü dengeleyebilir. Bu etkinin gücü, portföydeki paylarına bağlıdır.',
                      'Some assets can cushion currency changes. The effect depends on how much of the portfolio they make up.'),
    'risk_profile': ('Bu yorum, daha çok dalgalanabilen fonların portföydeki payını, seçtiğin profilin modeliyle karşılaştırır.',
                     'This compares the share held in higher-risk funds with the model for your selected profile.'),
    'concentration': ('Yatırımların büyük bir bölümü aynı yönetim şirketinde. O şirketle ilgili bir gelişme birden çok fonu etkileyebilir.',
                      'Much of the portfolio is with one fund manager. A change at that firm could affect several funds.'),
    'liquidation': ('Portföydeki fonlardan biri tasfiye sürecinde veya kapsam dışında. Fon kartında durumunu görebilirsin.',
                    'One of your funds is in liquidation or outside the analysis coverage. The fund card shows its status.'),
    'macro_sentiment': ('Fonlarınla ilgili haberlerin genel tonunu Haberler bölümünde görebilirsin.',
                        'The news section shows the overall tone of coverage relevant to your funds.'),
    'governance': ('Piyasa değiştikçe portföyündeki varlıkların payı da değişebilir. Varlık dağılımı bu farkı görmene yardımcı olur.',
                   'As markets move, the share held in each asset can change. The allocation chart helps you see that shift.'),
    'model_forecast': ('Model, bu fonu benzer fonlarla karşılaştırdı. Bir hafta, bir ay ve üç ay için sonucu fon kartında görebilirsin.',
                       'The model compared this fund with similar funds. See its one-week, one-month and three-month outlook in the fund card.'),
    'gru_weak': ('Fon, modelin benzer fonlar sıralamasında alt grupta. Fon kartında farklı süreler için görünümü inceleyebilirsin.',
                 'The fund ranks in the lower group of its peers in the model. See the fund card for the outlook over different periods.'),
    'gru_strong': ('Fon, modelin benzer fonlar sıralamasında üst grupta. Fon kartında farklı süreler için görünümü inceleyebilirsin.',
                   'The fund ranks in the upper group of its peers in the model. See the fund card for the outlook over different periods.'),
    'profile_risk_deviation': ('Daha çok dalgalanabilen fonların payı, seçtiğin profil için modelde tanımlanan sınırın üzerinde.',
                               'The share held in higher-risk funds is above the model’s limit for your selected profile.'),
}


def asset_label(name, lang):
    return ALLOCATION_LABELS.get(name, (name, name))[lang == 'en']


def localized(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get('tr') or value.get('en')
    return value


def copy_blocks(section, lang):
    texts = section.get('texts') or section
    version = texts.get(lang) or texts.get('tr') or texts.get('en') or {}
    details = (version.get('details') or section.get(f'details_{lang}')
               or localized(section.get('details'), lang))
    return {
        'summary': (
            version.get('summary') or section.get(f'summary_{lang}')
            or localized(section.get('summary'), lang)
        ),
        'details': [line.strip() for line in details.splitlines() if line.strip()] if isinstance(details, str) else [],
        'disclaimer': localized(texts.get('disclaimer') or section.get('disclaimer'), lang),
    }


def portfolio_context(section, currency, labels, lang):
    selected = section.get(f'total_value_{currency.lower()}')
    cash = section.get('cash_balance')
    cash_currency = section.get('cash_currency') or (
        'TRY' if section.get('usd_rate_date') else section.get('base_currency', 'TRY')
    )
    source_total = section.get(f'total_value_{cash_currency.lower()}')
    if currency != cash_currency and isinstance(cash, Real) and selected is not None and source_total:
        cash, cash_currency = cash * selected / source_total, currency
    allocation = section.get('allocation_by_subcategory') or {}
    allocations = [
        (asset_label(name, lang), value, COLORS[index % len(COLORS)])
        for index, (name, value) in enumerate(allocation.items())
    ]
    pie = None
    if allocation and sum(allocation.values()) > 0:
        names, values, colors = zip(*allocations)
        pie = chart(go.Figure(go.Pie(
            labels=names, values=values, hole=0.68,
            textinfo='none', sort=False, hovertemplate='%{label}<extra></extra>',
            marker={'colors': colors, 'line': {'color': 'white', 'width': 2}},
        )).update_layout(showlegend=False), 204)
    tracker = section.get('savings_tracker') or {}
    tracker_rows = [
        (unit, tracker.get(f'total_invested_{suffix}'), tracker.get(f'current_value_{suffix}'),
         tracker.get(f'gap_{suffix}'), tracker.get(f'gap_{suffix}_pct'))
        for unit, suffix in [('TRY', 'tl'), ('USD', 'usd'), (labels['real_tl'], 'real_tl')]
    ] if tracker else []
    usable_rows = [row for row in tracker_rows if any(value is not None for value in row[1:])]
    primary_row = next((row for row in usable_rows if row[0] == currency), next(iter(usable_rows), None))
    return {
        'total': selected,
        'cash': cash,
        'cash_currency': cash_currency,
        'others': [(c, section.get(f'total_value_{c.lower()}'))
                   for c in ('TRY', 'USD', 'EUR', 'GBP') if c != currency],
        'allocations': allocations,
        'pie_note': bool(pie) and abs(sum(allocation.values()) - 100) > 0.2,
        'pie': pie,
        'protected': section.get('usd_protective_share_pct'),
        'protected_text': section.get('usd_protective_share_text'),
        'as_of': section.get('usd_rate_date'),
        'months': tracker.get('months_count'),
        'tracker_rows': tracker_rows,
        'primary_row': primary_row,
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
        'last_point': trajectory[-1] if trajectory else None,
    }


def robustness_context(section, lang, labels, currency):
    score = section.get('overall_score')
    caps = {'stress_resilience': 35, 'purchasing_power': 25, 'forward_risk': 20, 'diversification': 20}
    subs = section.get('sub_scores') or {}
    parts = [(labels[key], subs[key], maximum) for key, maximum in caps.items() if isinstance(subs.get(key), Real)]
    scenarios = [
        (entry.get(f'name_{lang}') or localized(entry.get('name') or entry.get('scenario'), lang),
         entry.get('portfolio_shock_tl_pct'), entry.get('portfolio_shock_usd_pct'))
        for entry in section.get('scenarios') or []
    ]
    scenario_currency = currency if currency in ('TRY', 'USD') else 'TRY'
    column = 2 if scenario_currency == 'USD' else 1
    weakest = min(
        ((row[0], row[column]) for row in scenarios if isinstance(row[column], Real)),
        key=lambda item: item[1], default=None,
    )
    estimates = []
    for label, field in [
        ('loss_real_12m', 'prob_loss_real_tl_12m'),
        ('loss_usd_12m', 'prob_loss_usd_12m'),
        ('volatility_21d', 'portfolio_forecast_21d_vol'),
    ]:
        value = section.get(field)
        if isinstance(value, Real):
            estimates.append((labels[label], 100 * value))
    return {
        'score': score, 'grade': section.get('grade'), 'parts': parts,
        'scenarios': scenarios, 'weakest': weakest, 'scenario_currency': scenario_currency,
        'estimates': estimates,
    }


def rebalance_context(section, lang, profile, reference, portfolio):
    target = section.get('target_comparison') or {}
    contribution = section.get('contribution_only') or {}
    categories = (
        target.get('by_subcategory') or target.get('subcategory_comparison')
        or section.get('subcategory_comparison') or []
    )
    funds = target.get('comparison') or target.get('fund_comparison') or []
    rows = [
        (asset_label(entry.get('subcategory'), lang), entry.get('current_weight_pct'),
         entry.get('target_weight_pct'), entry.get('difference_pct'))
        for entry in categories
    ]
    if reference:
        actual = {asset_label(key, lang): value for key, value in
                  (portfolio.get('allocation_by_subcategory') or {}).items()}
        target_weights = {asset_label(key, lang): value for key, value in reference['weights'].items()}
        rows = [
            (name, actual.get(name, 0), target_weights.get(name, 0),
             round(target_weights.get(name, 0) - actual.get(name, 0), 2))
            for name in actual.keys() | target_weights.keys()
        ] if actual else []
    rows = sorted(rows, key=lambda row: (-abs(row[3] or 0), row[0] or ''))
    matches_profile = not reference or target.get('profile') == profile
    cash = section.get('cash_allocation') or section.get('cash_example') or []
    if isinstance(cash, dict):
        cash = cash.get('allocations') or []
    return {
        'rows': rows,
        'funds': [(entry.get('symbol'), entry.get('current_weight_pct'),
                   entry.get('target_weight_pct'), entry.get('difference_pct')) for entry in funds] if matches_profile else [],
        'reference_date': reference.get('as_of') if reference else None,
        'matches_profile': matches_profile,
        'contribution': (contribution.get('allocations') or []) if matches_profile else [],
        'cash': [
            {**entry, 'allocated_amount_tl': entry.get('allocated_amount_tl', entry.get('suggested_amount'))}
            for entry in cash if matches_profile
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
        if not data:
            continue
        rank = data.get('percentile', data.get('subcategory_percentile'))
        status = data.get(f'outlook_{lang}') or localized(data.get('status') or data.get('label'), lang)
        color = {'güçlü': 'strong', 'strong': 'strong', 'zayıf': 'weak', 'weak': 'weak'}.get(
            (status or '').lower(), 'neutral'
        )
        if not status and isinstance(rank, Real):
            color = 'strong' if rank >= 67 else 'weak' if rank <= 33 else 'neutral'
            status = labels[color]
        probability = data.get('probability_outperform', data.get('probability'))
        context['chips'].append({
            'label': labels[horizon], 'status': labels[color] if status else '—', 'color': color,
            'rank': rank, 'agreement': data.get(f'seed_agreement_text_{lang}')
            or localized(data.get('seed_agreement_text'), lang),
            'probability': 100 * probability if isinstance(probability, Real) else None,
            'tested_ic': data.get('tested_ic'),
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
        name = localized(theme.get('theme') or theme.get('name'), lang) or ''
        yield {
            'name': NEWS_THEME_LABELS.get(name, (name.replace('_', ' '), name.replace('_', ' ')))[lang == 'en'],
            'status': theme.get(f'status_{lang}') or (labels['insufficient'] if insufficient else status),
            'insufficient': insufficient,
            'counts': [(labels[key], counts.get(key, counts.get(key[:3], theme.get(f'{key}_count'))))
                       for key in ('positive', 'neutral', 'negative')],
            'headline': {'title': headline} if isinstance(headline, str) else headline,
        }


def dashboard_context(payload, lang, currency, *, profile, level, reference=None):
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
    comment_items = [
        {**entry, 'display': entry.get(f'text_{lang}') or entry.get('text_tr') or entry.get('text_en'),
         'title': entry.get(f'title_{lang}') or entry.get('title_tr')}
        for entry in (comment_section.get('items', []) if comment_section else comments)
        if not (reference and entry.get('category') == 'risk_profile')
    ]
    for item in comment_items:
        simple = None
        if level == 'beginner':
            identifier = item.get('id') or ''
            key = '_'.join(identifier.split('_')[:2]) if identifier.startswith('gru_') else identifier
            simple = COMMENT_EXPLANATIONS.get(key) or COMMENT_EXPLANATIONS.get(item.get('category'))
        item['preview'] = simple[lang == 'en'] if simple else item['display']
    highlights = sorted(
        (item for item in comment_items if item['display']),
        key=lambda item: item.get('severity') != 'attention',
    )[:2]
    source_profile = (sections['savings_plan'].get('profile_model_basket') or {}).get('profile')
    return {
        'payload': payload,
        't': labels,
        'portfolio_data': {**copy_blocks(sections['portfolio'], lang),
                           **portfolio_context(sections['portfolio'], currency, labels, lang)},
        'savings_data': {**copy_blocks(sections['savings_plan'], lang),
                         **savings_context(sections['savings_plan'], labels),
                         'source_matches': not reference or source_profile in (None, profile)},
        'robustness_data': {**copy_blocks(sections['robustness'], lang),
                            **robustness_context(sections['robustness'], lang, labels, currency)},
        'rebalancing_data': {**copy_blocks(sections['rebalancing'], lang),
                             **rebalance_context(sections['rebalancing'], lang, profile, reference, sections['portfolio'])},
        'stay': copy_blocks(sections['stay_the_course'], lang) if sections['stay_the_course'] else None,
        'news_data': {
            **copy_blocks(news, lang), 'themes': list(news_context(news, lang, labels)),
            'status': news.get(f'label_{lang}'),
            'counts': [(labels[label], (news.get('counts') or {}).get(key))
                       for label, key in [('positive', 'pos'), ('neutral', 'neu'), ('negative', 'neg')]]
            if news.get('label') != 'insufficient_data' else [],
        },
        'comments_data': {**copy_blocks(comment_section, lang), 'items': comment_items},
        'highlights': highlights,
        'funds': [fund_context(fund, lang, labels) for fund in payload.get('fund_cards') or []],
    }


def correlation_context(result):
    matrix, observations, start, end = result
    values = matrix.to_numpy().round(2).tolist()
    symbols = matrix.columns.tolist()
    figure = go.Figure(go.Heatmap(
        z=values, x=symbols, y=symbols, zmin=-1, zmax=1,
        colorscale=[[0, '#ab574a'], [.5, '#fafbf9'], [1, '#187a60']],
        texttemplate='%{z:.2f}', hovertemplate='%{x} · %{y}<br>%{z:.2f}<extra></extra>',
    ))
    figure.update_yaxes(autorange='reversed', scaleanchor='x')
    figure.update_xaxes(side='top')
    return {
        'chart': chart(figure, min(500, max(260, len(symbols) * 46 + 100))),
        'observations': observations, 'start': start, 'end': end,
    }


def dashboard_labels(lang):
    language_index = 1 if lang == 'en' else 0
    return {key: values[language_index] for key, values in TEXT.items()}
