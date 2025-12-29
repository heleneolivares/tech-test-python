from __future__ import annotations

from pathlib import Path
from decimal import Decimal
from datetime import date
from typing import Any

import pandas as pd

from django.db import transaction

from portfolio.models import Portfolio, Asset, PortfolioPosition, AssetPrice
from portfolio import selectors

INITIAL_VALUE = Decimal("1000000000")


def load_portfolio_data(excel_path: Path) -> None:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel no encontrado en: {excel_path}")

    with transaction.atomic():

        # EXTRACT
        weights_df = pd.read_excel(excel_path, sheet_name="weights", engine="openpyxl")
        prices_df = pd.read_excel(excel_path, sheet_name="Precios", engine="openpyxl")

        # Limpieza nombres de columnas
        weights_df.columns = weights_df.columns.map(lambda c: str(c).strip().lower())
        prices_df.columns = prices_df.columns.map(lambda c: str(c).strip().lower())

        weights_df = weights_df.rename(
            columns={
                "activos": "ticker",
                "portafolio 1": "portfolio_1",
                "portafolio 2": "portfolio_2",
            }
        )

        # Validaciones
        _validate_weights_columns(weights_df)
        _validate_prices(prices_df)
        _validate_weights_sum(weights_df)

        # Fecha inicial
        t0_ts = pd.to_datetime(weights_df["fecha"].iloc[0], errors="coerce")
        if pd.isna(t0_ts):
            raise ValueError("Fecha inicial inválida en hoja 'weights' (columna 'fecha').")
        t0: date = t0_ts.date()

        # Load portafolios

        portfolio1, _ = Portfolio.objects.get_or_create(
            name="Portfolio 1",
            defaults={"initial_value": INITIAL_VALUE},
        )
        portfolio2, _ = Portfolio.objects.get_or_create(
            name="Portfolio 2",
            defaults={"initial_value": INITIAL_VALUE},
        )

        # load acciones y precios

        assets_map = _process_assets_prices(prices_df)

        # load posiciones
        _process_weights_positions(
            weights_df=weights_df,
            assets_map=assets_map,
            portfolio1=portfolio1,
            portfolio2=portfolio2,
            t0=t0,
        )


def _validate_weights_columns(weights_df: pd.DataFrame) -> None:
    required_columns = {"fecha", "ticker", "portfolio_1", "portfolio_2"}

    if not required_columns.issubset(set(weights_df.columns)):
        raise ValueError(
            f"Hoja 'weights' debe tener columnas {required_columns}. "
            f"Columnas econtradas: {set(weights_df.columns)}"
        )


def _validate_prices(prices_df: pd.DataFrame) -> None:
    if prices_df.shape[1] < 2:
        raise ValueError(
            "Hoja 'Precios' debe tener fecha y minimo una columna de activos"
        )
    
def _validate_weights_sum(
        weights_df: pd.DataFrame, *, tolerance: Decimal = Decimal("0.000001")
) -> None:
    p1_sum = Decimal("0")
    p2_sum =  Decimal("0")

    for _, row in weights_df.iterrows():
        if pd.notna(row["portfolio_1"]):
            p1_sum += Decimal(str(row["portfolio_1"]))
        if pd.notna(row["portfolio_2"]):
            p2_sum += Decimal(str(row["portfolio_2"]))

    if abs(p1_sum - Decimal ("1")) > tolerance:
        raise ValueError(
            f"Los weights de portafolio 1 no suman 1."
            f"{p1_sum}"
        )
    if abs(p2_sum - Decimal("1")) > tolerance:
        raise ValueError(
            f"Los weights de portafolio 2 no suman 1."
            f"{p2_sum}"
        )

def _process_assets_prices(prices_df: pd.DataFrame) -> dict[str, Asset]:
    assets_map: dict[str, Asset] = {}

    date_column = prices_df.columns[0]
    ticker_columns = [str(c).strip() for c in prices_df.columns[1:]]

    for ticker in ticker_columns:
        asset, _ = Asset.objects.get_or_create(ticker=ticker)
        assets_map[ticker] = asset

    for _, row in prices_df.iterrows():
        current_ts = pd.to_datetime(row[date_column], errors="coerce")
        if pd.isna(current_ts):
            continue
        current_date: date = current_ts.date()

        for ticker in ticker_columns:
            price_value = row[ticker]
            if pd.isna(price_value):
                continue

            AssetPrice.objects.update_or_create(
                asset=assets_map[ticker],
                date=current_date,
                defaults={"price": Decimal(str(price_value))},
            )

    return assets_map


def _process_weights_positions(
    *,
    weights_df: pd.DataFrame,
    assets_map: dict[str, Asset],
    portfolio1: Portfolio,
    portfolio2: Portfolio,
    t0: date,
) -> None:

    initial_prices: dict[str, Decimal] = {}

    for ticker, asset in assets_map.items():
        try:
            asset_price = AssetPrice.objects.get(asset=asset, date=t0)
            initial_prices[ticker] = asset_price.price
        except AssetPrice.DoesNotExist:
            continue

    for _, row in weights_df.iterrows():
        ticker = str(row["ticker"]).strip()

        if ticker not in assets_map:
            raise ValueError(
                f"Ticker '{ticker}' aparece en weights pero no existe en hoja precios"
            )

        initial_price = initial_prices.get(ticker)
        if initial_price is None:
            raise ValueError(f"Falta precio inicial para '{ticker}' en {t0}")
        if initial_price == 0:
            raise ValueError(f"Precio inicial 0 para '{ticker}' en {t0}")

        asset = assets_map[ticker]

        weight_p1 = row["portfolio_1"]
        weight_p2 = row["portfolio_2"]

        # Portfolio 1

        if pd.notna(weight_p1):
            w1 = Decimal(str(weight_p1))
            quantity = (w1 * INITIAL_VALUE) / initial_price
            PortfolioPosition.objects.update_or_create(
                portfolio=portfolio1,
                asset=asset,
                defaults={"quantity": quantity},
            )

        # Portfolio 2

        if pd.notna(weight_p2):
            w2 = Decimal(str(weight_p2))
            quantity = (w2 * INITIAL_VALUE) / initial_price
            PortfolioPosition.objects.update_or_create(
                portfolio=portfolio2,
                asset=asset,
                defaults={"quantity": quantity},
            )


# Calculations


def calculate_portfolio_evolution(
    *,
    portfolio_id: int,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    if start_date > end_date:
        raise ValueError("start_date no puede ser mayor que end_date")

    positions_qs = selectors.get_portfolio_positions(portfolio_id=portfolio_id)
    if not positions_qs.exists():
        raise ValueError(f"Portfolio {portfolio_id} no tiene posiciones")

    assets = [p.asset for p in positions_qs]

    dates = selectors.available_price_dates_assets(
        assets=assets,
        start_date=start_date,
        end_date=end_date,
    )
    if not dates:
        return []

    prices_qs = selectors.get_prices_assets(
        assets=assets,
        start_date=start_date,
        end_date=end_date,
    )


    qty_by_ticker = _build_ticker_quantity(positions_qs)
    prices_by_date_ticker = _build_prices_by_date_ticker(prices_qs)

    result: list[dict[str, Any]] = []

    for d in dates:
        ticker_price_map = prices_by_date_ticker.get(d, {})
        asset_values: dict[str, Decimal] = {}
        total_value = Decimal("0")

        for ticker, qty in qty_by_ticker.items():
            price = ticker_price_map.get(ticker)
            if price is None:
                continue

            v = qty * price
            asset_values[ticker] = v
            total_value += v

        if total_value == 0:
            weights = {ticker: Decimal("0") for ticker in asset_values.keys()}
        else:
            weights = {
                ticker: (value / total_value) for ticker, value in asset_values.items()
            }

        result.append(
            {
                "date": d,
                "total_value": total_value,
                "weights": weights,
            }
        )
    return result

def _build_ticker_quantity(positions_qs) -> dict[str,Decimal]:
    qty_by_ticker: dict[str,Decimal] = {}
    for p in positions_qs:
        qty_by_ticker[p.asset.ticker] = p.quantity
    return qty_by_ticker

def _build_prices_by_date_ticker(prices_qs) -> dict[date,dict[str,Decimal]]:
    prices_by: dict[date, dict[str, Decimal]] = {}
    for ap in prices_qs:
        prices_by.setdefault(ap.date, {})[ap.asset.ticker] = ap.price
    return prices_by
