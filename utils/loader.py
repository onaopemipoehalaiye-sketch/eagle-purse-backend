import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

FOOD_CATALOG_PATH = DATA_DIR / "campus_food.csv"


def load_food_catalog() -> pd.DataFrame:
    df = pd.read_csv(FOOD_CATALOG_PATH)
    df["price"] = df["price"].astype(float)
    return df


def get_feeding_spent(transactions: list[dict]) -> float:
    feeding_categories = {"lunch", "breakfast", "snack", "drink", "feeding", "Feeding"}
    return float(
        sum(tx["amount"] for tx in transactions if tx.get("category") in feeding_categories)
    )


def get_total_spent(transactions: list[dict]) -> float:
    return float(sum(tx["amount"] for tx in transactions))


def _parse_tx_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return datetime.fromisoformat(str(value)).date()


def get_days_elapsed(transactions: list[dict]) -> int:
    if not transactions:
        return 0
    dates = [_parse_tx_date(tx["date"]) for tx in transactions]
    first = min(dates)
    last = max(dates)
    return max(1, (last - first).days + 1)
