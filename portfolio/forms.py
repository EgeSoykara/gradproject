from datetime import date
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Asset, Note, Portfolio, Transaction


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class TransactionForm(forms.ModelForm):
    amount_tl = forms.DecimalField(
        required=False, label=_('Total amount (TRY)'), min_value=Decimal('0.01'),
        max_digits=18, decimal_places=2,
        help_text=_('For a fund, enter either units or a TRY amount. A TRY unit price is required with an amount.'),
    )

    class Meta:
        model = Transaction
        fields = ['kind', 'date', 'asset', 'quantity', 'amount_tl', 'price', 'currency', 'fee', 'memo']
        widgets = {
            'date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'memo': forms.TextInput(attrs={'placeholder': _('Optional context for this transaction')}),
        }
        labels = {
            'asset': _('Asset'),
            'date': _('Date'),
            'currency': _('Currency'),
            'memo': _('Memo'),
            'price': _('Unit price / cash amount'),
            'quantity': _('Units / grams'),
            'kind': _('Transaction type'),
            'fee': _('Fee (transaction currency)'),
        }
        help_texts = {
            'price': _('For deposits and withdrawals, enter the full cash amount.'),
            'currency': _('Cash is held in TRY; other currencies convert at the recorded historical rate.'),
        }

    def __init__(self, *args, portfolio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].required = False
        if not self.instance.pk:
            self.initial.setdefault('quantity', None)
        self.fields['asset'].queryset = Asset.objects.exclude(kind='benchmark').order_by(
            'kind', 'symbol'
        )
        if portfolio and portfolio.dataset == 'live':
            self.fields['asset'].queryset = self.fields['asset'].queryset.exclude(
                symbol__startswith='DEMO-'
            )
        self.fields['date'].initial = date.today

    def clean(self):
        data = super().clean()
        if data.get('date') and data['date'] > date.today():
            self.add_error('date', _('Future transactions are not supported.'))
        if data.get('kind') in ('deposit', 'withdraw'):
            data['asset'], data['quantity'], data['fee'] = None, 1, 0
        elif data.get('kind') in ('buy', 'sell'):
            asset, quantity, amount = data.get('asset'), data.get('quantity'), data.get('amount_tl')
            if not asset:
                self.add_error('asset', _('Select a fund or metal.'))
            elif amount is not None:
                if asset.kind != 'fund' or data.get('currency') != 'TRY':
                    self.add_error('amount_tl', _('Enter a TRY amount only for funds priced in TRY.'))
                elif quantity is not None:
                    self.add_error('amount_tl', _('Enter either units or an amount.'))
                elif data.get('price') and data['price'] > 0:
                    model_field = self._meta.model._meta.get_field('quantity')
                    try:
                        units = (amount / data['price']).quantize(
                            Decimal('0.00000001'), rounding=ROUND_DOWN
                        )
                        data['quantity'] = model_field.clean(units, self.instance)
                    except InvalidOperation:
                        self.add_error('amount_tl', _('The resulting number of units is too large.'))
                    except forms.ValidationError as exc:
                        self.add_error('amount_tl', exc)
            elif quantity is None and 'quantity' not in self.errors:
                self.add_error('quantity', _('Enter units, grams or a TRY amount.'))
        return data


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'body', 'fund']
        labels = {'title': _('Title'), 'body': _('Note'), 'fund': _('Fund')}
        help_texts = {'fund': _('Leave blank to link this note to the whole portfolio.')}
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 8,
                    'placeholder': _('Record your reasoning, questions and next review date…'),
                }
            )
        }


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name']
        labels = {'name': _('Name')}


class RangeForm(forms.Form):
    currency = forms.ChoiceField(
        choices=[(c, c) for c in ['TRY', 'USD', 'EUR', 'GBP']], required=False
    )
    start = forms.DateField(required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    end = forms.DateField(required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('end') and data['end'] > date.today():
            self.add_error('end', _('Choose today or an earlier date.'))
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError(_('The start date must be before the end date.'))
        return data
