"""
Unit tests for portfolio calculations.

Tests the core financial logic: cost basis, FIFO sells, gain/loss calculations.
"""
import pytest
from datetime import date

from src.models import Transaction, Action, PriceData, Position
from src.portfolio import (
    PositionState,
    compute_positions,
    compute_portfolio_summary,
    get_portfolio,
)


def make_tx(symbol, qty, price, year, month, day, action):
    """Helper to create test transactions."""
    return Transaction(
        symbol=symbol,
        quantity=qty,
        price=price,
        transaction_date=date(year, month, day),
        action=action
    )


class TestPositionState:
    """Tests for PositionState - the mutable cost basis tracker."""

    def test_empty_position(self):
        """Test empty position state."""
        state = PositionState()
        assert state.total_shares == 0
        assert state.total_cost == 0.0
        assert state.avg_cost == 0.0
        assert state.lots == []

    def test_add_single_buy(self):
        """Test adding a single buy."""
        state = PositionState()
        state.add_buy(100, 12.50)
        
        assert state.total_shares == 100
        assert state.total_cost == 1250.00
        assert state.avg_cost == 12.50
        assert len(state.lots) == 1

    def test_add_multiple_buys_same_price(self):
        """Test adding multiple buys at same price."""
        state = PositionState()
        state.add_buy(100, 12.50)
        state.add_buy(50, 12.50)
        
        assert state.total_shares == 150
        assert state.total_cost == 1875.00
        assert state.avg_cost == 12.50
        assert len(state.lots) == 2

    def test_add_multiple_buys_different_prices(self):
        """Test adding buys at different prices."""
        state = PositionState()
        state.add_buy(100, 10.00)
        state.add_buy(100, 15.00)
        
        assert state.total_shares == 200
        assert state.total_cost == 2500.00
        assert state.avg_cost == 12.50
        assert len(state.lots) == 2

    def test_fifo_sell_single_lot(self):
        """Test FIFO sell consuming one lot."""
        state = PositionState()
        state.add_buy(100, 10.00)
        state.add_buy(100, 15.00)
        
        proceeds, cost_basis = state.remove_shares(50)
        
        assert proceeds == 500.00  # 50 * 10.00 (first lot)
        assert cost_basis == 500.00
        assert state.total_shares == 150
        assert state.total_cost == 2000.00

    def test_fifo_sell_across_multiple_lots(self):
        """Test FIFO sell across multiple lots."""
        state = PositionState()
        state.add_buy(50, 10.00)
        state.add_buy(50, 20.00)
        
        proceeds, cost_basis = state.remove_shares(75)
        
        # 50 from first lot at 10 + 25 from second lot at 20
        assert proceeds == 50 * 10.00 + 25 * 20.00
        assert cost_basis == proceeds  # Under FIFO, cost basis = proceeds for sells
        assert state.total_shares == 25
        assert len(state.lots) == 1  # Second lot partially consumed

    def test_fifo_sell_all_shares(self):
        """Test selling all shares."""
        state = PositionState()
        state.add_buy(100, 12.50)
        
        proceeds, cost_basis = state.remove_shares(100)
        
        assert proceeds == 1250.00
        assert cost_basis == 1250.00
        assert state.total_shares == 0
        assert state.lots == []

    def test_avg_cost_with_sells(self):
        """Test that avg cost is computed correctly after sells."""
        state = PositionState()
        state.add_buy(100, 10.00)  # $1000
        state.add_buy(100, 20.00)  # $2000 = $3000 total
        
        state.remove_shares(50)  # Remove 50 from first lot at $10
        
        # Remaining: 50 at 10 + 100 at 20 = 150 shares, $2500 cost
        assert state.total_shares == 150
        assert state.total_cost == 2500.00
        assert state.avg_cost == 2500.00 / 150

    def test_sell_exceeding_shares_raises_error(self):
        """Test that selling more shares than available raises ValueError."""
        state = PositionState()
        state.add_buy(100, 10.00)
        
        with pytest.raises(ValueError, match="Cannot sell 150 shares, only 100 available"):
            state.remove_shares(150)

    def test_sell_exactly_all_shares(self):
        """Test selling exactly all available shares."""
        state = PositionState()
        state.add_buy(100, 10.00)
        
        proceeds, cost_basis = state.remove_shares(100)
        
        assert proceeds == 1000.00
        assert cost_basis == 1000.00
        assert state.total_shares == 0
        assert state.lots == []


class TestComputePositions:
    """Tests for compute_positions function."""

    def test_single_buy_position(self):
        """Test computing position from single buy."""
        transactions = [
            make_tx("BBD", 100, 12.50, 2024, 1, 15, Action.BUY)
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=15.00, timestamp="2024-06-01T12:00:00Z",
                           change=0.50, change_percent=3.45)
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 1
        pos = positions[0]
        assert pos.symbol == "BBD"
        assert pos.quantity == 100
        assert pos.avg_cost == 12.50
        assert pos.cost_basis == 1250.00
        assert pos.current_price == 15.00
        assert pos.current_value == 1500.00

    def test_multiple_buys_same_symbol(self):
        """Test position accumulation from multiple buys."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("BBD", 50, 15.00, 2024, 2, 1, Action.BUY),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=12.00, timestamp="2024-06-01T12:00:00Z")
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 1
        pos = positions[0]
        assert pos.quantity == 150
        assert pos.avg_cost == (100 * 10.00 + 50 * 15.00) / 150  # 11.67
        assert pos.cost_basis == 1000.00 + 750.00  # 1750.00

    def test_position_with_sell(self):
        """Test position reduced by sell (FIFO)."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("BBD", 50, 20.00, 2024, 2, 1, Action.BUY),
            make_tx("BBD", 30, 12.00, 2024, 3, 1, Action.SELL),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=15.00, timestamp="2024-06-01T12:00:00Z")
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 1
        pos = positions[0]
        # 100 at 10 + 50 at 20 = 150 shares, $2000 cost
        # Sell 30 at 12: removes 30 from first lot (100 at 10)
        # Remaining: 70 at 10 + 50 at 20 = 120 shares
        # Cost basis: 70*10 + 50*20 = 700 + 1000 = 1700
        assert pos.quantity == 120
        assert pos.cost_basis == 1700.00

    def test_multiple_symbols(self):
        """Test positions for multiple symbols."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("VZ", 50, 40.00, 2024, 1, 1, Action.BUY),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=12.00, timestamp="2024-06-01T12:00:00Z"),
            "VZ": PriceData(symbol="VZ", price=38.00, timestamp="2024-06-01T12:00:00Z"),
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 2
        bbd_pos = next(p for p in positions if p.symbol == "BBD")
        vz_pos = next(p for p in positions if p.symbol == "VZ")
        
        assert bbd_pos.quantity == 100
        assert bbd_pos.current_value == 1200.00
        assert vz_pos.quantity == 50
        assert vz_pos.current_value == 1900.00

    def test_skips_closed_positions(self):
        """Test that positions with zero shares are skipped."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("BBD", 100, 12.00, 2024, 2, 1, Action.SELL),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=15.00, timestamp="2024-06-01T12:00:00Z")
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 0

    def test_skips_symbols_with_no_price(self):
        """Test that symbols without price data are skipped."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("XYZ", 50, 20.00, 2024, 1, 1, Action.BUY),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=12.00, timestamp="2024-06-01T12:00:00Z"),
            # XYZ intentionally missing
        }
        
        positions = compute_positions(transactions, prices)
        
        assert len(positions) == 1
        assert positions[0].symbol == "BBD"


class TestComputePortfolioSummary:
    """Tests for compute_portfolio_summary function."""

    def test_empty_portfolio(self):
        """Test empty portfolio."""
        summary = compute_portfolio_summary([])
        
        assert summary.total_value == 0.0
        assert summary.total_cost_basis == 0.0
        assert summary.positions == []

    def test_single_position_summary(self):
        """Test portfolio summary with one position."""
        positions = [
            Position(
                symbol="BBD",
                quantity=100,
                avg_cost=10.00,
                cost_basis=1000.00,
                current_price=12.00,
                current_value=1200.00,
                today_gain=20.00,
                today_gain_percent=1.67,
                total_gain=200.00,
                total_gain_percent=20.00,
                percent_of_account=0.0  # Will be computed
            )
        ]
        
        summary = compute_portfolio_summary(positions)
        
        assert summary.total_value == 1200.00
        assert summary.total_cost_basis == 1000.00
        assert summary.total_gain == 200.00
        assert summary.total_gain_percent == 20.00

    def test_multiple_positions_with_percentages(self):
        """Test portfolio with multiple positions."""
        positions = [
            Position(
                symbol="BBD",
                quantity=100,
                avg_cost=10.00,
                cost_basis=1000.00,
                current_price=12.00,
                current_value=1200.00,
                today_gain=20.00,
                today_gain_percent=1.67,
                total_gain=200.00,
                total_gain_percent=20.00,
                percent_of_account=0.0
            ),
            Position(
                symbol="VZ",
                quantity=50,
                avg_cost=40.00,
                cost_basis=2000.00,
                current_price=38.00,
                current_value=1900.00,
                today_gain=-15.00,
                today_gain_percent=-0.78,
                total_gain=-100.00,
                total_gain_percent=-5.00,
                percent_of_account=0.0
            )
        ]
        
        summary = compute_portfolio_summary(positions)
        
        assert summary.total_value == 3100.00  # 1200 + 1900
        assert summary.total_cost_basis == 3000.00  # 1000 + 2000
        assert summary.total_today_gain == 5.00  # 20 + (-15)
        assert summary.total_gain == 100.00  # 200 + (-100)
        
        # Check percentages were computed
        bbd_pos = next(p for p in summary.positions if p.symbol == "BBD")
        vz_pos = next(p for p in summary.positions if p.symbol == "VZ")
        
        assert bbd_pos.percent_of_account == pytest.approx(38.71, rel=0.01)  # 1200/3100
        assert vz_pos.percent_of_account == pytest.approx(61.29, rel=0.01)  # 1900/3100


class TestGetPortfolio:
    """Integration tests for get_portfolio."""

    def test_full_portfolio_calculation(self):
        """Test the full pipeline from transactions to portfolio."""
        transactions = [
            make_tx("BBD", 100, 10.00, 2024, 1, 1, Action.BUY),
            make_tx("VZ", 50, 40.00, 2024, 1, 1, Action.BUY),
        ]
        prices = {
            "BBD": PriceData(symbol="BBD", price=12.00, timestamp="2024-06-01T12:00:00Z",
                           change=0.20, change_percent=1.67),
            "VZ": PriceData(symbol="VZ", price=38.00, timestamp="2024-06-01T12:00:00Z",
                          change=-0.30, change_percent=-0.78),
        }
        
        summary = get_portfolio(transactions, prices)
        
        assert len(summary.positions) == 2
        assert summary.total_value == 1200.00 + 1900.00  # 3100
        assert summary.total_cost_basis == 1000.00 + 2000.00  # 3000
        assert summary.total_gain == 100.00  # (1200-1000) + (1900-2000)