from django.contrib import admin

from .models import (
    Asset,
    ExchangeRate,
    ModelRun,
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
    ModelRun,
    NewsItem,
    Note,
    Portfolio,
    Price,
    SyncLog,
    Transaction,
):
    admin.site.register(model)
