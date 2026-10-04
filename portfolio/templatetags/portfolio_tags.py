from django import template

register = template.Library()


@register.filter
def money(value):
    try:
        return f'{float(value):,.2f}'
    except (ValueError, TypeError):
        return '—'


@register.filter
def units(value):
    try:
        return f'{float(value):,.4f}'.rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return '—'


@register.filter
def pct(value):
    try:
        return f'{float(value):+.2f}%'
    except (ValueError, TypeError):
        return '—'
