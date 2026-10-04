"""Decimal ledger: weighted average cost, TRY cash, full-history validation."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction

from portfolio.models import Portfolio

D = Decimal
ZERO = D('0')


@dataclass
class Position:
    quantity: Decimal = ZERO
    cost: Decimal = ZERO
    realized: Decimal = ZERO


@dataclass
class Ledger:
    cash: Decimal = ZERO
    contributions: Decimal = ZERO
    positions: dict = field(default_factory=lambda: defaultdict(Position))

    def apply(self, row):
        if row.quantity <= 0 or row.price <= 0 or row.fee < 0 or row.fx_to_try <= 0:
            raise ValidationError(
                'Amounts and exchange rates must be positive; fees cannot be negative.'
            )
        value = row.quantity * row.price * row.fx_to_try
        fee = row.fee * row.fx_to_try
        if row.kind in ('deposit', 'withdraw'):
            if row.asset_id or row.quantity != 1 or row.fee != 0:
                raise ValidationError('Cash movements use quantity 1, no asset and no fee.')
            change = value if row.kind == 'deposit' else -value
            self.cash += change
            self.contributions += change
        else:
            if not row.asset_id or row.asset.kind == 'benchmark':
                raise ValidationError('Choose a fund or metal for a trade.')
            p = self.positions[row.asset_id]
            if row.kind == 'buy':
                p.quantity += row.quantity
                p.cost += value + fee
                self.cash -= value + fee
            elif row.kind == 'sell':
                if row.quantity > p.quantity:
                    raise ValidationError(
                        f'Insufficient {row.asset.symbol} on {row.date}. Later transactions must remain valid.'
                    )
                released = p.cost * row.quantity / p.quantity
                p.quantity -= row.quantity
                p.cost -= released
                p.realized += value - fee - released
                self.cash += value - fee
            else:
                raise ValidationError('Unknown transaction type.')
        if self.cash < ZERO:
            raise ValidationError(
                f'Insufficient cash on {row.date}. Add a deposit first or adjust subsequent transactions.'
            )


def replay(rows):
    state = Ledger()
    for row in rows:
        state.apply(row)
    return state


@db_transaction.atomic
def save_transaction(row):
    Portfolio.objects.select_for_update().get(pk=row.portfolio_id)
    row.full_clean()
    row.save()
    replay(row.portfolio.transactions.select_related('asset').all())
    return row


@db_transaction.atomic
def delete_transaction(row):
    Portfolio.objects.select_for_update().get(pk=row.portfolio_id)
    portfolio = row.portfolio
    row.delete()
    replay(portfolio.transactions.select_related('asset').all())
