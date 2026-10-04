"""Explicit imports and optional authenticated providers. Never fall back to demo."""

import csv
import hashlib
import json
import os
from datetime import date, datetime
from datetime import timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from urllib.parse import urlparse

import requests
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from portfolio.models import Asset, ExchangeRate, NewsItem, Price, SyncLog


class ProviderError(ValueError):
    pass


def positive(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < Decimal('0.00000001') or number >= Decimal('1e12'):
            raise ValueError
        return number.quantize(Decimal('0.00000001'))
    except (InvalidOperation, ValueError, TypeError):
        raise ProviderError('Prices/rates must be finite numbers from 0.00000001 to below 1e12.')


def valid_day(value):
    try:
        day = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ProviderError('Dates must use YYYY-MM-DD.')
    if day > date.today():
        raise ProviderError('Future observations are not accepted.')
    return day


@transaction.atomic
def import_market(payload, dataset='live', source='CSV import'):
    if dataset not in ('live', 'demo'):
        raise ProviderError('Unknown dataset.')
    if not isinstance(payload, dict):
        raise ProviderError('Expected a JSON object with prices and rates arrays.')
    if not isinstance(payload.get('prices', []), list) or not isinstance(
        payload.get('rates', []), list
    ):
        raise ProviderError('Prices and rates must be JSON arrays.')
    count = 0
    for row in payload.get('prices', []):
        try:
            asset = Asset.objects.get(symbol=row['symbol'])
            if dataset == 'live' and asset.symbol.startswith('DEMO-'):
                raise ProviderError('Fictional demo fund symbols cannot contain live quotes.')
            day = valid_day(row['date'])
            price = positive(row['close'])
        except (KeyError, Asset.DoesNotExist, TypeError):
            raise ProviderError('Every price requires a known symbol, date and close.')
        Price.objects.update_or_create(
            asset=asset,
            date=day,
            dataset=dataset,
            defaults={'close': price, 'source': source[:100]},
        )
        count += 1
    for row in payload.get('rates', []):
        try:
            currency = row['currency']
            day = valid_day(row['date'])
            rate = positive(row['try_per_unit'])
        except (KeyError, TypeError):
            raise ProviderError('Every rate requires currency, date and try_per_unit.')
        if currency not in ('USD', 'EUR', 'GBP'):
            raise ProviderError('Rate currency must be USD, EUR or GBP; TRY is always 1.')
        ExchangeRate.objects.update_or_create(
            currency=currency,
            date=day,
            dataset=dataset,
            defaults={'try_per_unit': rate, 'source': source[:100]},
        )
        count += 1
    if not count:
        raise ProviderError('No price or exchange-rate observations were supplied.')
    return count


def read_market_csv(text):
    reader = csv.DictReader(StringIO(text))
    result = {'prices': [], 'rates': []}
    for row in reader:
        if row.get('type') == 'price':
            result['prices'].append(
                {'symbol': row.get('symbol'), 'date': row.get('date'), 'close': row.get('value')}
            )
        elif row.get('type') == 'fx':
            result['rates'].append(
                {
                    'currency': row.get('symbol'),
                    'date': row.get('date'),
                    'try_per_unit': row.get('value'),
                }
            )
        else:
            raise ProviderError(
                'CSV type must be price or fx. Required columns: type,symbol,date,value.'
            )
    return result


def get_json(url, headers=None, params=None):
    try:
        response = requests.get(url, headers=headers or {}, params=params or {}, timeout=(5, 25))
        if response.status_code != 200:
            raise ProviderError(
                f'Provider returned HTTP {response.status_code}. Check credentials, quota and access tier.'
            )
        return response.json()
    except (requests.RequestException, json.JSONDecodeError):
        # Never record exception URLs: some providers embed secrets in query strings.
        raise ProviderError('Provider connection or JSON decoding failed. No data was replaced.')


def sentiment_score(text):
    return SentimentIntensityAnalyzer().polarity_scores(text)['compound']


@transaction.atomic
def import_articles(rows, dataset='live', kind='news'):
    if (
        not isinstance(rows, list)
        or dataset not in ('demo', 'live')
        or kind not in ('news', 'social')
    ):
        raise ProviderError('Expected an article array, valid dataset and news/social kind.')
    analyzer = SentimentIntensityAnalyzer()
    count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ProviderError('Each article/post must be a JSON object.')
        title = str(row.get('title') or '').strip()
        stamp = parse_datetime(str(row.get('published_at', '')))
        if not title or not stamp:
            raise ProviderError('Every article/post requires title and an ISO timestamp.')
        if timezone.is_naive(stamp):
            stamp = timezone.make_aware(stamp)
        if stamp > timezone.now():
            raise ProviderError('Future article timestamps are not accepted.')
        url = str(row.get('url', ''))
        if url and urlparse(url).scheme not in ('https', 'http'):
            raise ProviderError('Article URLs must be HTTP(S).')
        key = str(row.get('id') or hashlib.sha256((title + str(stamp)).encode()).hexdigest())
        NewsItem.objects.update_or_create(
            external_id=key[:128],
            dataset=dataset,
            kind=kind,
            defaults={
                'title': title[:500],
                'published_at': stamp,
                'source': str(row.get('source', 'Imported dataset'))[:100],
                'url': url[:1000],
                'sentiment': analyzer.polarity_scores(title)['compound'],
            },
        )
        count += 1
    return count


def sync_provider(provider):
    try:
        if provider == 'market':
            url, key = os.getenv('MARKET_API_URL'), os.getenv('MARKET_API_KEY')
            if not url:
                raise ProviderError(
                    'MARKET_API_URL is not configured. Use CSV import or configure a normalized data service.'
                )
            if urlparse(url).scheme != 'https':
                raise ProviderError('MARKET_API_URL must use HTTPS.')
            payload = get_json(url, {'Authorization': f'Bearer {key}'} if key else {})
            count = import_market(payload, source='Configured market API')
        elif provider == 'metals':
            key = os.getenv('GOLD_API_TOKEN')
            if not key:
                raise ProviderError('GOLD_API_TOKEN is not configured.')
            from .valuation import MarketBook, MissingData

            book = MarketBook('live')
            payload = {'prices': []}
            for symbol, name in [('XAU', 'Gold'), ('XAG', 'Silver'), ('XPT', 'Platinum')]:
                data = get_json(f'https://www.goldapi.io/api/{symbol}/USD', {'x-access-token': key})
                if data.get('metal') != symbol or data.get('currency') != 'USD':
                    raise ProviderError('Unexpected metal or currency in the GoldAPI response.')
                try:
                    day = datetime.fromtimestamp(
                        float(data['timestamp']), tz=datetime_timezone.utc
                    ).date()
                    fx = book.rate('USD', day)
                except (KeyError, ValueError, OverflowError, MissingData):
                    raise ProviderError(
                        'GoldAPI needs a valid quote timestamp and historical USD/TRY rate. Import FX first.'
                    )
                per_gram_try = positive(data['price']) / Decimal('31.1034768') * fx
                payload['prices'].append(
                    {'symbol': symbol, 'date': str(day), 'close': str(per_gram_try)}
                )
            with transaction.atomic():
                for symbol, name in [('XAU', 'Gold'), ('XAG', 'Silver'), ('XPT', 'Platinum')]:
                    asset, _ = Asset.objects.get_or_create(
                        symbol=symbol,
                        defaults={
                            'name': name,
                            'kind': 'metal',
                            'currency': 'TRY',
                            'unit': 'grams',
                        },
                    )
                    if asset.currency != 'TRY' or asset.unit != 'grams':
                        raise ProviderError('Metal catalog must use TRY per gram for this adapter.')
                count = import_market(payload, source='GoldAPI spot · USD/oz converted to TRY/g')
        elif provider == 'news':
            key = os.getenv('NEWS_API_KEY')
            if not key:
                raise ProviderError('NEWS_API_KEY is not configured.')
            data = get_json(
                'https://newsapi.org/v2/everything',
                {'X-Api-Key': key},
                {
                    'q': '(economy OR gold OR investment)',
                    'language': 'en',
                    'pageSize': 50,
                    'sortBy': 'publishedAt',
                },
            )
            if data.get('status') != 'ok':
                raise ProviderError('News provider did not return a successful response.')
            count = import_articles(
                [
                    {
                        'title': x.get('title'),
                        'url': x.get('url'),
                        'source': (x.get('source') or {}).get('name'),
                        'published_at': x.get('publishedAt'),
                    }
                    for x in data.get('articles', [])
                ]
            )
        elif provider == 'social':
            key = os.getenv('X_BEARER_TOKEN')
            if not key:
                raise ProviderError('X_BEARER_TOKEN is not configured.')
            data = get_json(
                'https://api.x.com/2/tweets/search/recent',
                {'Authorization': f'Bearer {key}'},
                {
                    'query': os.getenv('X_QUERY', '(gold OR funds OR markets) lang:en -is:retweet'),
                    'max_results': 50,
                    'tweet.fields': 'created_at',
                },
            )
            if data.get('errors'):
                raise ProviderError('X returned a partial/error response; no posts were imported.')
            count = import_articles(
                [
                    {
                        'id': x['id'],
                        'title': x['text'],
                        'url': f'https://x.com/i/web/status/{x["id"]}',
                        'published_at': x['created_at'],
                        'source': 'X',
                    }
                    for x in data.get('data', [])
                ],
                kind='social',
            )
        else:
            raise ProviderError('Unknown provider.')
        SyncLog.objects.create(
            provider=provider, status='success', message=f'Imported {count} records.'
        )
        return count
    except (ProviderError, KeyError, TypeError, AttributeError) as exc:
        message = (
            str(exc)
            if isinstance(exc, ProviderError)
            else 'Unexpected provider response structure.'
        )
        SyncLog.objects.create(provider=provider, status='error', message=message[:500])
        raise ProviderError(message)
