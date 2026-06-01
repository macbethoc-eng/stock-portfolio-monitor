"""
Portfolio calculations: cost basis, PnL, position sizing.

This module contains all the financial calculations for computing
portfolio positions from raw transactions.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .models import (
    Transaction,
    Action,
    PriceData,
    Position,
    PortfolioSummary,
)


def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


@dataclass
class PositionState:
    """
    Mutable state for computing a position.
    
    We track shares owned and cost basis per lot to support FIFO sells.
    """
    total_shares: int = 0
    total_cost: float = 0.0
    lots: list[tuple[int, float]] = None  # (shares, price_per_share) per lot
    
    def __post_init__(self):
        if self.lots is None:
            self.lots = []
    
    @property
    def avg_cost(self) -> float:
        """Average cost per share."""
        if self.total_shares == 0:
            return 0.0
        return self.total_cost / self.total_shares
    
    def add_buy(self, quantity: int, price: float) -> None:
        """Add shares via a buy transaction."""
        self.total_shares += quantity
        self.total_cost += quantity * price
        self.lots.append((quantity, price))
    
    def remove_shares(self, quantity: int) -> tuple[float, float]:
        """
        Remove shares via a sell transaction using FIFO.
        
        Returns (proceeds, cost_basis_removed).
        Raises ValueError if quantity exceeds available shares.
        """
        if quantity > self.total_shares:
            raise ValueError(
                f"Cannot sell {quantity} shares, only {self.total_shares} available"
            )
        
        proceeds = 0.0
        cost_basis_removed = 0.0
        remaining = quantity
        
        while remaining > 0 and self.lots:
            lot_qty, lot_price = self.lots[0]
            
            if lot_qty <= remaining:
                # Fully consume this lot
                cost_basis_removed += lot_qty * lot_price
                proceeds += lot_qty * lot_price
                remaining -= lot_qty
                self.lots.pop(0)
            else:
                # Partially consume this lot
                cost_basis_removed += remaining * lot_price
                proceeds += remaining * lot_price
                self.lots[0] = (lot_qty - remaining, lot_price)
                remaining = 0
        
        self.total_shares -= quantity
        self.total_cost -= cost_basis_removed
        
        return proceeds, cost_basis_removed


def compute_positions(
    transactions: list[Transaction],
    prices: dict[str, PriceData]
) -> list[Position]:
    """
    Compute all positions from a list of transactions and current prices.
    
    Uses FIFO for cost basis. Sells reduce position.
    """
    # Group transactions by symbol
    by_symbol: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        by_symbol[txn.symbol].append(txn)
    
    # Sort each symbol's transactions by date
    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda t: t.transaction_date)
    
    # Compute positions
    positions = []
    for symbol, txns in by_symbol.items():
        pos_state = PositionState()
        
        for txn in txns:
            if txn.action == Action.BUY:
                pos_state.add_buy(txn.quantity, txn.price)
            elif txn.action == Action.SELL:
                pos_state.remove_shares(txn.quantity)
        
        if pos_state.total_shares <= 0:
            continue  # Skip closed positions
        
        price_data = prices.get(symbol)
        if price_data is None:
            continue  # Skip if no price data
        
        current_price = price_data.price
        current_value = pos_state.total_shares * current_price
        cost_basis = pos_state.total_cost
        
        # Today's gain (using change from price data)
        today_gain = 0.0
        today_gain_percent = 0.0
        if price_data.change is not None and price_data.change_percent is not None:
            today_gain = price_data.change * pos_state.total_shares
            today_gain_percent = price_data.change_percent
        else:
            # If no change data, compute from cost basis
            if cost_basis > 0:
                daily_change_percent = price_data.change_percent or 0.0
                today_gain_percent = daily_change_percent
                today_gain = current_value * (daily_change_percent / 100)
        
        # Total gain (from cost basis)
        total_gain = current_value - cost_basis
        total_gain_percent = 0.0
        if cost_basis > 0:
            total_gain_percent = (total_gain / cost_basis) * 100
        
        positions.append(Position(
            symbol=symbol,
            quantity=pos_state.total_shares,
            avg_cost=pos_state.avg_cost,
            cost_basis=cost_basis,
            current_price=current_price,
            current_value=current_value,
            today_gain=today_gain,
            today_gain_percent=today_gain_percent,
            total_gain=total_gain,
            total_gain_percent=total_gain_percent,
            percent_of_account=0.0  # Computed in portfolio summary
        ))
    
    return positions


def compute_portfolio_summary(
    positions: list[Position],
) -> PortfolioSummary:
    """Compute portfolio-level totals and percentages."""
    if not positions:
        return PortfolioSummary(
            total_value=0.0,
            total_cost_basis=0.0,
            total_today_gain=0.0,
            total_today_gain_percent=0.0,
            total_gain=0.0,
            total_gain_percent=0.0,
            positions=[],
            last_updated=""
        )
    
    total_value = sum(p.current_value for p in positions)
    total_cost_basis = sum(p.cost_basis for p in positions)
    total_today_gain = sum(p.today_gain for p in positions)
    total_gain = sum(p.total_gain for p in positions)
    
    # Percent of account for each position
    for pos in positions:
        if total_value > 0:
            pos.percent_of_account = (pos.current_value / total_value) * 100
        else:
            pos.percent_of_account = 0.0
    
    # Portfolio-level percentages
    total_today_gain_percent = 0.0
    if total_value > 0:
        # Use yesterday's value for today's % calc (approx)
        yesterday_value = total_value - total_today_gain
        if yesterday_value > 0:
            total_today_gain_percent = (total_today_gain / yesterday_value) * 100
    
    total_gain_percent = 0.0
    if total_cost_basis > 0:
        total_gain_percent = (total_gain / total_cost_basis) * 100
    
    last_updated = get_utc_now()
    
    return PortfolioSummary(
        total_value=total_value,
        total_cost_basis=total_cost_basis,
        total_today_gain=total_today_gain,
        total_today_gain_percent=total_today_gain_percent,
        total_gain=total_gain,
        total_gain_percent=total_gain_percent,
        positions=positions,
        last_updated=last_updated
    )


def get_portfolio(transactions: list[Transaction], prices: dict[str, PriceData]) -> PortfolioSummary:
    """Main entry point: compute full portfolio from transactions and prices."""
    positions = compute_positions(transactions, prices)
    return compute_portfolio_summary(positions)