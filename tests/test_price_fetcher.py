"""
Unit tests for price fetcher module.

Tests price fetching logic with mocked yfinance responses.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.models import PriceData
from src.price_fetcher import fetch_price, fetch_prices, refresh_prices


class TestFetchPrice:
    """Tests for single price fetching."""

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_price_success(self, mock_ticker_class):
        """Test successful price fetch."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "currentPrice": 12.50,
            "previousClose": 12.00,
        }
        mock_ticker_class.return_value = mock_ticker
        
        result = fetch_price("BBD")
        
        assert result is not None
        assert result.symbol == "BBD"
        assert result.price == 12.50
        assert result.change == 0.50
        assert result.change_percent == pytest.approx(4.1667, rel=0.01)

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_price_uses_regular_market_price(self, mock_ticker_class):
        """Test fallback to regularMarketPrice."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 12.50,
            "previousClose": 12.00,
        }
        mock_ticker_class.return_value = mock_ticker
        
        result = fetch_price("BBD")
        
        assert result.price == 12.50

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_price_no_price(self, mock_ticker_class):
        """Test when no price is available."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker_class.return_value = mock_ticker
        
        result = fetch_price("BBD")
        
        assert result is None

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_price_exception(self, mock_ticker_class):
        """Test handling of exceptions."""
        mock_ticker_class.side_effect = Exception("Network error")
        
        result = fetch_price("BBD")
        
        assert result is None


class TestFetchPrices:
    """Tests for multiple price fetching."""

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_prices_multiple_symbols(self, mock_ticker_class):
        """Test fetching multiple symbols."""
        def create_mock_ticker(symbol):
            mock = MagicMock()
            mock.info = {
                "currentPrice": 12.50 if symbol == "BBD" else 40.00,
                "previousClose": 12.00 if symbol == "BBD" else 39.00,
            }
            return mock
        
        mock_ticker_class.side_effect = create_mock_ticker
        
        results = fetch_prices(["BBD", "VZ"])
        
        assert len(results) == 2
        assert "BBD" in results
        assert "VZ" in results

    @patch('src.price_fetcher.yf.Ticker')
    def test_fetch_prices_skips_failures(self, mock_ticker_class):
        """Test that failed fetches are skipped."""
        def create_mock_ticker(symbol):
            mock = MagicMock()
            if symbol == "BBD":
                mock.info = {"currentPrice": 12.50, "previousClose": 12.00}
            else:
                mock.info = {}  # No price
            return mock
        
        mock_ticker_class.side_effect = create_mock_ticker
        
        results = fetch_prices(["BBD", "VZ"])
        
        assert len(results) == 1
        assert "BBD" in results
        assert "VZ" not in results


class TestRefreshPrices:
    """Tests for price refresh with caching."""

    @patch('src.price_fetcher.yf.Ticker')
    def test_refresh_prices_from_transactions(self, mock_ticker_class):
        """Test refreshing prices based on transactions."""
        # Mock transaction loading
        with patch('src.price_fetcher.storage.load_transactions') as mock_load:
            mock_load.return_value = MagicMock(transactions=[
                MagicMock(symbol="BBD"),
                MagicMock(symbol="VZ"),
            ])
            
            def create_mock_ticker(symbol):
                mock = MagicMock()
                mock.info = {
                    "currentPrice": 12.50 if symbol == "BBD" else 40.00,
                    "previousClose": 12.00 if symbol == "BBD" else 39.00,
                }
                return mock
            
            mock_ticker_class.side_effect = create_mock_ticker
            
            with patch('src.price_fetcher.storage.load_prices_cache') as mock_cache_load:
                mock_cache_load.return_value = MagicMock(prices={}, last_fetch=None)
                
                with patch('src.price_fetcher.storage.save_prices_cache') as mock_save:
                    cache = refresh_prices()
                    
                    assert "BBD" in cache.prices
                    assert "VZ" in cache.prices
                    assert cache.last_fetch is not None

    @patch('src.price_fetcher.fetch_prices')
    def test_refresh_prices_with_symbol_list(self, mock_fetch):
        """Test refreshing with explicit symbol list."""
        mock_fetch.return_value = {
            "BBD": PriceData(symbol="BBD", price=12.50, timestamp="2024-06-01T12:00:00Z")
        }
        
        with patch('src.price_fetcher.storage.load_prices_cache') as mock_cache_load:
            mock_cache_load.return_value = MagicMock(prices={}, last_fetch=None)
            
            with patch('src.price_fetcher.storage.save_prices_cache') as mock_save:
                cache = refresh_prices(symbols=["BBD"])
                
                mock_fetch.assert_called_once_with(["BBD"])