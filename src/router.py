"""
FastAPI router for portfolio API endpoints.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from .models import (
    Transaction,
    TransactionsFile,
    PortfolioSummary,
    PriceData,
)
from . import storage
from . import price_fetcher
from . import portfolio as portfolio_calc


router = APIRouter(prefix="/api")


@router.get("/portfolio", response_model=PortfolioSummary)
def get_portfolio() -> PortfolioSummary:
    """Get the full portfolio with all positions computed."""
    transactions_file = storage.load_transactions()
    transactions = transactions_file.transactions
    
    cache = storage.load_prices_cache()
    
    # Convert cached prices to dict
    prices = {symbol: data for symbol, data in cache.prices.items()}
    
    return portfolio_calc.get_portfolio(transactions, prices)


@router.get("/prices")
def get_prices() -> dict[str, PriceData]:
    """Get current cached prices."""
    cache = storage.load_prices_cache()
    return cache.prices


@router.post("/prices/refresh")
def refresh_prices() -> dict[str, Any]:
    """Force refresh prices from Yahoo Finance."""
    try:
        cache = price_fetcher.refresh_prices()
        return {
            "success": True,
            "prices": cache.prices,
            "last_fetch": cache.last_fetch
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
def get_transactions() -> TransactionsFile:
    """List all transactions."""
    return storage.load_transactions()


@router.post("/transactions")
def add_transaction(transaction: Transaction) -> Transaction:
    """Add a new transaction."""
    transactions_file = storage.load_transactions()
    transactions_file.transactions.append(transaction)
    storage.save_transactions(transactions_file)
    return transaction


@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str) -> dict[str, str]:
    """Delete a transaction by ID."""
    transactions_file = storage.load_transactions()
    
    original_count = len(transactions_file.transactions)
    transactions_file.transactions = [
        t for t in transactions_file.transactions if t.id != transaction_id
    ]
    
    if len(transactions_file.transactions) == original_count:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    storage.save_transactions(transactions_file)
    return {"message": "Transaction deleted"}


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}