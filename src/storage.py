"""
JSON file persistence for transactions and price cache.
"""
import json
from pathlib import Path
from typing import Optional

from .models import TransactionsFile, PricesCacheFile, PriceData


DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
PRICES_CACHE_FILE = DATA_DIR / "prices_cache.json"


def load_transactions() -> TransactionsFile:
    """Load transactions from disk, returning empty list if file doesn't exist."""
    if not TRANSACTIONS_FILE.exists():
        return TransactionsFile()
    
    with open(TRANSACTIONS_FILE, "r") as f:
        data = json.load(f)
    
    return TransactionsFile(**data)


def save_transactions(transactions_file: TransactionsFile) -> None:
    """Save transactions to disk."""
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions_file.model_dump(), f, indent=2, default=str)


def load_prices_cache() -> PricesCacheFile:
    """Load prices cache from disk, returning empty cache if file doesn't exist."""
    if not PRICES_CACHE_FILE.exists():
        return PricesCacheFile()
    
    with open(PRICES_CACHE_FILE, "r") as f:
        data = json.load(f)
    
    return PricesCacheFile(**data)


def save_prices_cache(prices_cache: PricesCacheFile) -> None:
    """Save prices cache to disk."""
    with open(PRICES_CACHE_FILE, "w") as f:
        json.dump(prices_cache.model_dump(), f, indent=2, default=str)


def get_transactions_file_path() -> Path:
    """Return the path to the transactions file."""
    return TRANSACTIONS_FILE


def get_prices_cache_file_path() -> Path:
    """Return the path to the prices cache file."""
    return PRICES_CACHE_FILE