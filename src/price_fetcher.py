"""
Yahoo Finance price fetcher with caching.
"""
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

from .models import PriceData, PricesCacheFile
from . import storage


def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def fetch_price(symbol: str) -> Optional[PriceData]:
    """
    Fetch current price for a single symbol from Yahoo Finance.
    
    Returns None if the fetch fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose")
        
        if current_price is None:
            return None
        
        change = None
        change_percent = None
        if previous_close and previous_close > 0:
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100
        
        return PriceData(
            symbol=symbol,
            price=current_price,
            timestamp=get_utc_now(),
            change=change,
            change_percent=change_percent
        )
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def fetch_prices(symbols: list[str]) -> dict[str, PriceData]:
    """
    Fetch prices for multiple symbols.
    
    Returns dict of symbol -> PriceData. Failed fetches are skipped.
    """
    results = {}
    
    for symbol in symbols:
        price_data = fetch_price(symbol)
        if price_data:
            results[symbol] = price_data
    
    return results


def refresh_prices(symbols: Optional[list[str]] = None) -> PricesCacheFile:
    """
    Refresh prices from Yahoo Finance and update the cache.
    
    If symbols is None, fetches all unique symbols from transactions.
    """
    if symbols is None:
        transactions_file = storage.load_transactions()
        symbols = list(set(t.symbol for t in transactions_file.transactions))
    
    if not symbols:
        return storage.load_prices_cache()
    
    new_prices = fetch_prices(symbols)
    
    # Load existing cache and merge
    cache = storage.load_prices_cache()
    for symbol, price_data in new_prices.items():
        cache.prices[symbol] = price_data
    
    cache.last_fetch = get_utc_now()
    storage.save_prices_cache(cache)
    
    return cache


def get_cached_prices() -> PricesCacheFile:
    """Get the current cached prices without refreshing."""
    return storage.load_prices_cache()


def get_price_for_symbol(symbol: str) -> Optional[PriceData]:
    """Get cached price for a single symbol."""
    cache = storage.load_prices_cache()
    return cache.prices.get(symbol)