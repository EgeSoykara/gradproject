from django import template
from django.utils.formats import number_format

register = template.Library()

PRESET_WORKSPACE_NAMES = {
    'tr': {
        ('demo', 'Learning portfolio'): 'Demo portföyü',
        ('live', 'My portfolio'): 'Portföyüm',
    },
    'en': {('live', 'Arşiv veri örneği'): 'Archive portfolio'},
}


@register.filter
def workspace_name(portfolio, language):
    if not portfolio:
        return 'Portföyüm' if language == 'tr' else 'My portfolio'
    labels = PRESET_WORKSPACE_NAMES.get(language, {})
    return labels.get((portfolio.dataset, portfolio.name), portfolio.name)


@register.filter
def money(value):
    try:
        return number_format(f'{float(value):.2f}', decimal_pos=2, force_grouping=True)
    except (ValueError, TypeError):
        return '—'


@register.filter
def units(value):
    try:
        rounded = f'{float(value):.4f}'.rstrip('0').rstrip('.')
        return number_format(rounded, force_grouping=True)
    except (ValueError, TypeError):
        return '—'


@register.filter
def pct(value):
    try:
        number = float(value)
        sign = '-' if number < 0 else '+'
        return f'{sign}{number_format(f"{abs(number):.2f}", decimal_pos=2)}%'
    except (ValueError, TypeError):
        return '—'
