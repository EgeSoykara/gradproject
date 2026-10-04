from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

CURRENCIES = [(c, c) for c in ('TRY', 'USD', 'EUR', 'GBP')]
DATASETS = [('demo', 'Demonstration'), ('live', 'Market data')]
POSITIVE = MinValueValidator(Decimal('0.00000001'))


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    dataset = models.CharField(max_length=4, choices=DATASETS, default='live')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=12,
        choices=[('fund', 'TEFAS fund'), ('metal', 'Precious metal'), ('benchmark', 'Benchmark')],
    )
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='TRY')
    unit = models.CharField(max_length=12, default='units')

    def __str__(self):
        return f'{self.symbol} · {self.name}'


class Price(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    date = models.DateField()
    close = models.DecimalField(max_digits=22, decimal_places=8, validators=[POSITIVE])
    dataset = models.CharField(max_length=4, choices=DATASETS)
    source = models.CharField(max_length=100)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['asset', 'date', 'dataset'], name='unique_asset_price')
        ]
        indexes = [models.Index(fields=['dataset', 'date'])]
        ordering = ['date']


class ExchangeRate(models.Model):
    currency = models.CharField(max_length=3, choices=CURRENCIES)
    date = models.DateField()
    try_per_unit = models.DecimalField(max_digits=20, decimal_places=8, validators=[POSITIVE])
    dataset = models.CharField(max_length=4, choices=DATASETS)
    source = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['currency', 'date', 'dataset'], name='unique_fx_rate')
        ]
        ordering = ['date']


class Transaction(models.Model):
    KINDS = [('deposit', 'Deposit'), ('withdraw', 'Withdrawal'), ('buy', 'Buy'), ('sell', 'Sell')]
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='transactions')
    kind = models.CharField(max_length=8, choices=KINDS)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True)
    date = models.DateField()
    quantity = models.DecimalField(
        max_digits=20, decimal_places=8, default=1, validators=[POSITIVE]
    )
    price = models.DecimalField(max_digits=20, decimal_places=8, validators=[POSITIVE])
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='TRY')
    fee = models.DecimalField(
        max_digits=18, decimal_places=4, default=0, validators=[MinValueValidator(0)]
    )
    fx_to_try = models.DecimalField(
        max_digits=20, decimal_places=8, default=1, validators=[POSITIVE]
    )
    memo = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'id']


class Note(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=10000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class NewsItem(models.Model):
    external_id = models.CharField(max_length=128)
    title = models.CharField(max_length=500)
    url = models.URLField(blank=True, max_length=1000)
    source = models.CharField(max_length=100)
    published_at = models.DateTimeField()
    dataset = models.CharField(max_length=4, choices=DATASETS)
    kind = models.CharField(max_length=8, choices=[('news', 'News'), ('social', 'Social')])
    sentiment = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['external_id', 'dataset', 'kind'], name='unique_news_item'
            )
        ]
        ordering = ['-published_at']


class ModelRun(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    dataset = models.CharField(max_length=4, choices=DATASETS)
    model_name = models.CharField(max_length=120)
    trained_at = models.DateTimeField(auto_now_add=True)
    data_end = models.DateField()
    prediction = models.FloatField()
    metrics = models.JSONField(default=dict)
    artifact = models.CharField(max_length=250)

    class Meta:
        ordering = ['-trained_at']


class SyncLog(models.Model):
    provider = models.CharField(max_length=50)
    status = models.CharField(max_length=12)
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
