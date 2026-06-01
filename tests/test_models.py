"""
Unit tests for Pydantic data models.
"""
import pytest
from datetime import date
from pydantic import ValidationError

from src.models import (
    Transaction,
    Action,
    PriceData,
    Position,
    PortfolioSummary,
    TransactionsFile,
    PricesCacheFile,
)


class TestTransaction:
    """Tests for Transaction model."""

    def test_valid_buy_transaction(self):
        """Test creating a valid buy transaction."""
        txn = Transaction(
            symbol="BBD",
            quantity=100,
            price=12.50,
            transaction_date=date(2024, 1, 15),
            action=Action.BUY
        )
        assert txn.symbol == "BBD"
        assert txn.quantity == 100
        assert txn.price == 12.50
        assert txn.action == Action.BUY
        assert txn.total_cost == 1250.00

    def test_valid_sell_transaction(self):
        """Test creating a valid sell transaction."""
        txn = Transaction(
            symbol="BBD",
            quantity=50,
            price=14.00,
            transaction_date=date(2024, 6, 1),
            action=Action.SELL
        )
        assert txn.action == Action.SELL
        assert txn.total_cost == 700.00

    def test_transaction_requires_symbol(self):
        """Test that symbol is required."""
        with pytest.raises(ValidationError):
            Transaction(
                quantity=100,
                price=12.50,
                transaction_date=date(2024, 1, 15),
                action=Action.BUY
            )

    def test_transaction_requires_positive_price(self):
        """Test that price must be positive."""
        with pytest.raises(ValidationError):
            Transaction(
                symbol="BBD",
                quantity=100,
                price=0,
                transaction_date=date(2024, 1, 15),
                action=Action.BUY
            )

    def test_transaction_requires_positive_quantity(self):
        """Test that quantity must be positive."""
        with pytest.raises(ValidationError):
            Transaction(
                symbol="BBD",
                quantity=0,
                price=12.50,
                transaction_date=date(2024, 1, 15),
                action=Action.BUY
            )

    def test_transaction_auto_generates_id(self):
        """Test that ID is auto-generated."""
        txn = Transaction(
            symbol="BBD",
            quantity=100,
            price=12.50,
            transaction_date=date(2024, 1, 15),
            action=Action.BUY
        )
        assert txn.id is not None
        assert len(txn.id) > 0


class TestPriceData:
    """Tests for PriceData model."""

    def test_valid_price_data(self):
        """Test creating valid price data."""
        price = PriceData(
            symbol="BBD",
            price=12.50,
            timestamp="2024-06-01T12:00:00Z",
            change=0.25,
            change_percent=2.0
        )
        assert price.symbol == "BBD"
        assert price.price == 12.50

    def test_price_data_optional_fields(self):
        """Test that change fields are optional."""
        price = PriceData(
            symbol="BBD",
            price=12.50,
            timestamp="2024-06-01T12:00:00Z"
        )
        assert price.change is None
        assert price.change_percent is None


class TestTransactionsFile:
    """Tests for TransactionsFile model."""

    def test_empty_transactions_file(self):
        """Test creating empty transactions file."""
        tf = TransactionsFile()
        assert tf.transactions == []

    def test_transactions_file_with_transactions(self):
        """Test creating transactions file with data."""
        txn = Transaction(
            symbol="BBD",
            quantity=100,
            price=12.50,
            transaction_date=date(2024, 1, 15),
            action=Action.BUY
        )
        tf = TransactionsFile(transactions=[txn])
        assert len(tf.transactions) == 1


class TestPricesCacheFile:
    """Tests for PricesCacheFile model."""

    def test_empty_prices_cache(self):
        """Test creating empty prices cache."""
        pc = PricesCacheFile()
        assert pc.prices == {}
        assert pc.last_fetch is None

    def test_prices_cache_with_data(self):
        """Test creating prices cache with data."""
        price = PriceData(
            symbol="BBD",
            price=12.50,
            timestamp="2024-06-01T12:00:00Z"
        )
        pc = PricesCacheFile(
            prices={"BBD": price},
            last_fetch="2024-06-01T12:00:00Z"
        )
        assert "BBD" in pc.prices
        assert pc.last_fetch is not None