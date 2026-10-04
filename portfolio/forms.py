from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Asset, Note, Portfolio, Transaction


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'date', 'asset', 'quantity', 'price', 'currency', 'fee', 'memo']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'memo': forms.TextInput(attrs={'placeholder': 'Optional context for this transaction'}),
        }
        labels = {
            'price': 'Unit price / cash amount',
            'quantity': 'Units / grams',
            'fee': 'Fee (transaction currency)',
        }
        help_texts = {
            'price': 'For deposits and withdrawals, enter the full cash amount.',
            'quantity': 'Cash movements use 1. Metals use grams.',
            'currency': 'Cash is held in TRY; other currencies convert at the recorded historical rate.',
        }

    def __init__(self, *args, portfolio=None, **kwargs):
        super().__init__(*args, **kwargs)
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
            self.add_error('date', 'Future transactions are not supported.')
        if data.get('kind') in ('deposit', 'withdraw'):
            data['asset'], data['quantity'], data['fee'] = None, 1, 0
        elif data.get('kind') in ('buy', 'sell') and not data.get('asset'):
            self.add_error('asset', 'Select a fund or metal.')
        return data


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'body']
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 8,
                    'placeholder': 'Record your reasoning, questions and next review date…',
                }
            )
        }


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name']


class RangeForm(forms.Form):
    currency = forms.ChoiceField(
        choices=[(c, c) for c in ['TRY', 'USD', 'EUR', 'GBP']], required=False
    )
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('end') and data['end'] > date.today():
            self.add_error('end', 'Choose today or an earlier date.')
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError('The start date must be before the end date.')
        return data
