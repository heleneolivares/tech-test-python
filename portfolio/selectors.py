from __future__ import annotations

from datetime import date
from typing import Iterable

from django.db.models import QuerySet

from portfolio.models import Asset, AssetPrice, Portfolio, PortfolioPosition

def get_portfolio(*, portfolio_id: int) -> Portfolio:
    return Portfolio.objects.get(id=portfolio_id)

def get_portfolio_positions(*, portfolio_id: int) -> QuerySet[PortfolioPosition]:
    return (
        PortfolioPosition.objects.filter(portfolio_id=portfolio_id)
        .select_related("asset")
        .order_by("asset__ticker")
    )

def get_prices_assets(
        *,
        assets: Iterable[Asset],
        start_date:date,
        end_date: date,
 ) -> QuerySet[AssetPrice]:
    return (
        AssetPrice.objects.filter(
            asset__in=list(assets),
            date__range=(start_date, end_date),
        )
        .select_related("asset")
        .order_by("date", "asset__ticker")
    )

def available_price_dates_assets(
    *,
    assets: Iterable[Asset],
    start_date: date,
    end_date: date,
) -> list[date]:
    qs = (
        AssetPrice.objects.filter(
            asset__in=list(assets),
            date__range=(start_date, end_date),
        )
        .values_list("date", flat=True)
        .distinct()
        .order_by("date")
    )

    return list(qs)