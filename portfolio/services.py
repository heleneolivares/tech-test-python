from pathlib import Path
import pandas as pd
from django.conf import settings

EXCEL_PATH = Path(settings.BASE_DIR) / "data" / "datos.xlsx"

def load_portfolio_data() -> None:
    pass 