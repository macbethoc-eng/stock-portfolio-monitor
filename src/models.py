"""
Data models for the Stock Portfolio Monitor.
"""
from datetime import date as DateType
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Action(str, Enum):
    """Transaction action type."""
    BUY = "buy"
    SELL = "sell"


class Transaction(BaseModel):
    """A single stock transaction (buy or sell)."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str = Field(min_length=1, max_length=10)
    quantity: int = Field(ge=1)
    price: float = Field(gt=0)
    transaction_date: DateType = Field(alias="date", description="Date of the transaction")
    action: Action = Field(description="Buy or sell")

    model_config = {
        "populate_by_name": True,
    }

    @property
    def total_cost(self) -> float:
        """Total value of this transaction."""
        return self.quantity * self.price


class PriceData(BaseModel):
    """Current price data for a stock."""
    symbol: str
    price: float = Field(gt=0)
    timestamp: str  # ISO format timestamp of when price was fetched
    change: Optional[float] = None  # Price change from previous close
    change_percent: Optional[float] = None  # Percentage change


class Position(BaseModel):
    """A computed position for a single stock."""
    symbol: str
    quantity: int
    avg_cost: float
    cost_basis: float
    current_price: float
    current_value: float
    today_gain: float
    today_gain_percent: float
    total_gain: float
    total_gain_percent: float
    percent_of_account: float


class PortfolioSummary(BaseModel):
    """Complete portfolio summary."""
    total_value: float
    total_cost_basis: float
    total_today_gain: float
    total_today_gain_percent: float
    total_gain: float
    total_gain_percent: float
    positions: list[Position]
    last_updated: str


class TransactionsFile(BaseModel):
    """Root model for transactions.json file."""
    transactions: list[Transaction] = Field(default_factory=list)


class PricesCacheFile(BaseModel):
    """Root model for prices_cache.json file."""
    prices: dict[str, PriceData] = Field(default_factory=dict)
    last_fetch: Optional[str] = None