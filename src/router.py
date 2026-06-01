"""
FastAPI router for portfolio API endpoints.
"""
import logging
from datetime import datetime, timezone
from typing import Any

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


def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


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
        logging.error(f"Price refresh failed: {e}")
        raise HTTPException(status_code=500, detail="Price refresh failed. Check logs for details.")


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
    return {"status": "ok", "timestamp": get_utc_now()}


# Report endpoints
@router.get("/reports/portfolio")
def get_portfolio_report() -> dict[str, Any]:
    """Get the latest portfolio news report."""
    from .report_state import get_report_state
    state = get_report_state()
    report = state.load_report("portfolio")
    return {
        "report": report or "No portfolio report generated yet.",
        "last_generated": state.last_portfolio_report
    }


@router.get("/reports/opportunities")
def get_opportunity_report() -> dict[str, Any]:
    """Get the latest opportunity report."""
    from .report_state import get_report_state
    state = get_report_state()
    report = state.load_report("opportunity")
    return {
        "report": report or "No opportunity report generated yet.",
        "last_generated": state.last_opportunity_report
    }


@router.post("/reports/portfolio/generate")
def generate_portfolio_report() -> dict[str, Any]:
    """Generate a new portfolio report."""
    from .report_generator import generate_portfolio_report as gen_report
    from .emailer import send_portfolio_report
    
    result = gen_report()
    send_portfolio_report(result['report'])
    return result


@router.post("/reports/opportunities/generate")
def generate_opportunity_report() -> dict[str, Any]:
    """Generate a new opportunity report."""
    from .report_generator import generate_opportunity_report as gen_report
    from .emailer import send_opportunity_report
    
    result = gen_report()
    send_opportunity_report(result['report'])
    return result


@router.get("/news/stock/{symbol}")
def get_stock_news(symbol: str) -> dict[str, Any]:
    """Get news for a specific stock symbol."""
    from .news_fetcher import fetch_stock_news
    
    news = fetch_stock_news([symbol], days=7)
    return {
        "symbol": symbol,
        "news": news,
        "count": len(news)
    }


@router.get("/news/market")
def get_market_news() -> dict[str, Any]:
    """Get general market news."""
    from .news_fetcher import fetch_general_market_news, get_trending_topics
    
    news = fetch_general_market_news(limit=20)
    trending = get_trending_topics()
    return {
        "news": news,
        "trending": trending,
        "news_count": len(news),
        "trending_count": len(trending)
    }