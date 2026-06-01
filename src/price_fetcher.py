"""
Yahoo Finance price fetcher using chart API (no auth required).
"""
from datetime import datetime, timezone
from typing import Optional

import requests

from .models import PriceData, PricesCacheFile
from . import storage


def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def fetch_price(symbol: str) -> Optional[PriceData]:
    """
    Fetch current price for a single symbol from Yahoo Finance chart API.
    
    Uses the non-authenticated chart endpoint. Returns None if fetch fails.
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": "1d",
            "range": "2d",
            "includePrePost": "false"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        result = data.get("chart", {}).get("result", [])
        
        if not result:
            return None
        
        meta = result[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        chart_previous_close = meta.get("chartPreviousClose")
        market_time = meta.get("regularMarketTime")
        
        if current_price is None:
            return None
        
        change = None
        change_percent = None
        if chart_previous_close and chart_previous_close > 0:
            change = current_price - chart_previous_close
            change_percent = (change / chart_previous_close) * 100
        
        # Convert market time to ISO if available
        timestamp = get_utc_now()
        if market_time:
            try:
                ts_dt = datetime.fromtimestamp(market_time, tz=timezone.utc)
                timestamp = ts_dt.isoformat().replace('+00:00', 'Z')
            except Exception:
                pass
        
        return PriceData(
            symbol=symbol,
            price=current_price,
            timestamp=timestamp,
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