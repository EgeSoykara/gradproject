from django.contrib import admin

from .models import (
    Asset,
    ExchangeRate,
    NewsItem,
    Note,
    Portfolio,
    Price,
    SyncLog,
    Transaction,
)

for model in (
    Asset,
    ExchangeRate,
    NewsItem,
    Note,
    Portfolio,
    Price,
    SyncLog,
    Transaction,
):
    admin.site.register(model)
