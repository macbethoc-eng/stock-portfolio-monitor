"""
Unit tests for storage module.

Tests JSON file read/write for transactions and prices cache.
"""
import json
import os
import pytest
from pathlib import Path

from src.storage import (
    TransactionsFile,
    PricesCacheFile,
    TRANSACTIONS_FILE,
    PRICES_CACHE_FILE,
    get_transactions_file_path,
    get_prices_cache_file_path,
)


# Use a temp directory for tests
@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    """Patch DATA_DIR to use temp directory for all tests."""
    import src.storage
    monkeypatch.setattr(src.storage, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(src.storage, 'TRANSACTIONS_FILE', tmp_path / "transactions.json")
    monkeypatch.setattr(src.storage, 'PRICES_CACHE_FILE', tmp_path / "prices_cache.json")


class TestTransactionsStorage:
    """Tests for transaction file operations."""

    def test_save_and_load_transactions(self):
        """Test saving and loading transactions."""
        from src.models import Transaction, Action
        from datetime import date
        
        # Create transactions
        txn1 = Transaction(
            id="test-123",
            symbol="BBD",
            quantity=100,
            price=12.50,
            transaction_date=date(2024, 1, 15),
            action=Action.BUY
        )
        
        txf = TransactionsFile(transactions=[txn1])
        
        # Save
        from src.storage import save_transactions, load_transactions
        save_transactions(txf)
        
        # Load
        loaded = load_transactions()
        
        assert len(loaded.transactions) == 1
        assert loaded.transactions[0].symbol == "BBD"
        assert loaded.transactions[0].quantity == 100

    def test_load_empty_transactions(self):
        """Test loading when file doesn't exist."""
        from src.storage import load_transactions
        
        loaded = load_transactions()
        
        assert len(loaded.transactions) == 0

    def test_save_multiple_transactions(self):
        """Test saving multiple transactions."""
        from src.models import Transaction, Action
        from datetime import date
        
        transactions = [
            Transaction(symbol="BBD", quantity=100, price=12.50, transaction_date=date(2024, 1, 15), action=Action.BUY),
            Transaction(symbol="VZ", quantity=50, price=40.00, transaction_date=date(2024, 2, 1), action=Action.BUY),
        ]
        
        txf = TransactionsFile(transactions=transactions)
        
        from src.storage import save_transactions, load_transactions
        save_transactions(txf)
        
        loaded = load_transactions()
        assert len(loaded.transactions) == 2


class TestPricesCacheStorage:
    """Tests for prices cache file operations."""

    def test_save_and_load_prices_cache(self):
        """Test saving and loading prices cache."""
        from src.models import PriceData
        
        prices = {
            "BBD": PriceData(symbol="BBD", price=12.50, timestamp="2024-06-01T12:00:00Z"),
            "VZ": PriceData(symbol="VZ", price=40.00, timestamp="2024-06-01T12:00:00Z"),
        }
        
        cache = PricesCacheFile(prices=prices, last_fetch="2024-06-01T12:00:00Z")
        
        from src.storage import save_prices_cache, load_prices_cache
        save_prices_cache(cache)
        
        loaded = load_prices_cache()
        
        assert "BBD" in loaded.prices
        assert "VZ" in loaded.prices
        assert loaded.prices["BBD"].price == 12.50

    def test_load_empty_prices_cache(self):
        """Test loading when file doesn't exist."""
        from src.storage import load_prices_cache
        
        loaded = load_prices_cache()
        
        assert loaded.prices == {}
        assert loaded.last_fetch is None


class TestFilePaths:
    """Tests for file path utilities."""

    def test_get_transactions_file_path(self):
        """Test transactions file path getter."""
        path = get_transactions_file_path()
        assert isinstance(path, Path)
        assert path.name == "transactions.json"

    def test_get_prices_cache_file_path(self):
        """Test prices cache file path getter."""
        path = get_prices_cache_file_path()
        assert isinstance(path, Path)
        assert path.name == "prices_cache.json"