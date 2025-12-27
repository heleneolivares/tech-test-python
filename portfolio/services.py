from pathlib import Path
from decimal import Decimal

import pandas as pd

from django.db import transaction

from portfolio.models import Portfolio, Asset, PortfolioPosition, AssetPrice

INITIAL_VALUE = Decimal("1000000000")

def load_portfolio_data(excel_path: Path) -> None:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel no encontrado en: {excel_path}")

    with transaction.atomic():

        # EXTRACT
        weights_df = pd.read_excel(excel_path, sheet_name="weights", engine="openpyxl")
        prices_df = pd.read_excel(excel_path, sheet_name="Precios", engine="openpyxl")

        # Limpieza nombres de columnas
        weights_df.columns = weights_df.columns.map(lambda c: str(c).strip())
        prices_df.columns = prices_df.columns.map(lambda c: str(c).strip())

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

        #Fecha inicial 
        t0 = pd.to_datetime(weights_df["Fecha"].iloc[0]).date()

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
    required_columns = {"Fecha", "ticker", "portfolio_1", "portfolio_2"}

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


def _process_assets_prices(prices_df: pd.DataFrame) -> dict[str, Asset]:
    assets_map: dict[str, Asset] = {}

    date_column = prices_df.columns[0]
    ticker_columns = [str(c).strip() for c in prices_df.columns[1:]]

    for ticker in ticker_columns:
        asset, _ = Asset.objects.get_or_create(ticker=ticker)
        assets_map[ticker] = asset

    for _, row in prices_df.iterrows():
        current_date = pd.to_datetime(row[date_column]).date()

        for ticker in ticker_columns:
            price_value = row[ticker]

            if pd.isna(price_value):
                continue

            price_decimal = Decimal(str(price_value))

            AssetPrice.objects.update_or_create(
                asset=assets_map[ticker],
                date=current_date,
                defaults={"price": price_decimal},
            )

    return assets_map


def _process_weights_positions(
    *,
    weights_df: pd.DataFrame,
    assets_map: dict[str, Asset],
    portfolio1: Portfolio,
    portfolio2: Portfolio,
    t0,
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
