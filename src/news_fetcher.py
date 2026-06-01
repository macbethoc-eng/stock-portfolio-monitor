"""
News fetcher for stock symbols and market news.
Uses RSS feeds from Yahoo Finance, Google News, and financial sources.
"""
import feedparser
import html
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import re

# RSS feed URLs
YAHOO_FINANCE_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
FINANCIAL_NEWS_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^IXIC&region=US&lang=en-US"  # Nasdaq


def sanitize_text(text: str) -> str:
    """Remove HTML tags and clean text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    clean = html.unescape(clean)
    # Normalize whitespace
    clean = ' '.join(clean.split())
    return clean.strip()


def get_article_id(article: dict) -> str:
    """Generate a unique ID for an article based on title and link."""
    content = f"{article.get('title', '')}{article.get('link', '')}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from RSS feeds."""
    if not date_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_rss_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS feed, returning list of article dicts."""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            article = {
                'title': sanitize_text(entry.get('title', '')),
                'link': entry.get('link', ''),
                'summary': sanitize_text(entry.get('summary', entry.get('description', ''))),
                'published': parse_date(entry.get('published', '')),
                'source': feed.feed.get('title', url),
            }
            if article['title']:
                articles.append(article)
    except Exception as e:
        print(f"Error fetching RSS {url}: {e}")
    return articles


def fetch_stock_news(symbols: list[str], days: int = 7) -> list[dict]:
    """
    Fetch recent news articles for given stock symbols.
    
    Args:
        symbols: List of stock ticker symbols (e.g., ['BBD', 'VZ'])
        days: Only return articles from the last N days
    
    Returns:
        List of article dicts with title, link, summary, published, source
    """
    all_articles = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    for symbol in symbols:
        # Try Yahoo Finance RSS
        url = YAHOO_FINANCE_RSS.format(symbol=symbol)
        articles = fetch_rss_feed(url)
        
        # Add symbol to each article
        for article in articles:
            article['symbol'] = symbol
            article['id'] = get_article_id(article)
        
        all_articles.extend(articles)
        
        # Try Google News RSS as backup
        google_url = GOOGLE_NEWS_RSS.format(symbol=symbol)
        google_articles = fetch_rss_feed(google_url)
        for article in google_articles:
            article['symbol'] = symbol
            article['id'] = get_article_id(article)
            # Avoid duplicates
            if not any(a['id'] == article['id'] for a in all_articles):
                all_articles.append(article)
    
    # Filter by date and remove duplicates
    seen_ids = set()
    filtered = []
    for article in all_articles:
        if article['id'] in seen_ids:
            continue
        if article['published'] and article['published'] < cutoff_date:
            continue
        seen_ids.add(article['id'])
        filtered.append(article)
    
    # Sort by date, newest first
    filtered.sort(key=lambda x: x.get('published') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    return filtered


def fetch_general_market_news(limit: int = 20) -> list[dict]:
    """
    Fetch general market and financial news.
    
    Returns:
        List of article dicts with market-relevant news
    """
    articles = []
    
    # Yahoo Finance main feed
    articles.extend(fetch_rss_feed("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US"))
    
    # Market news
    articles.extend(fetch_rss_feed("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^IXIC&region=US&lang=en-US"))
    
    # Economy
    articles.extend(fetch_rss_feed("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI&region=US&lang=en-US"))
    
    # Filter to recent articles (7 days)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
    
    filtered = []
    for article in articles:
        if article.get('published') and article['published'] < cutoff_date:
            continue
        article['id'] = get_article_id(article)
        filtered.append(article)
    
    # Deduplicate and limit
    seen_ids = set()
    result = []
    for article in filtered:
        if article['id'] in seen_ids:
            continue
        seen_ids.add(article['id'])
        result.append(article)
    
    result.sort(key=lambda x: x.get('published') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    return result[:limit]


def get_trending_topics() -> list[str]:
    """
    Identify trending market topics from recent news headlines.
    
    Returns:
        List of common themes/topics found in recent news
    """
    # Fetch recent market news
    articles = fetch_general_market_news(limit=30)
    
    # Extract keywords and phrases
    all_text = " ".join(a['title'] + " " + a.get('summary', '') for a in articles)
    
    # Common financial/market topics
    topic_keywords = [
        'Federal Reserve', 'interest rate', 'inflation', 'recession',
        'earnings', 'IPO', 'merger', 'acquisition', 'bankruptcy',
        'tariff', 'trade war', 'oil', 'crypto', 'bitcoin', 'AI',
        'semiconductor', 'tech', 'banking', 'healthcare', 'energy',
        'retail', 'housing market', 'jobs report', 'GDP',
        'china', 'europe', 'ukraine', 'russia', 'oil price',
        'fed rate', 'treasury', 'yield curve', 'bull market', 'bear market'
    ]
    
    found_topics = []
    for topic in topic_keywords:
        if topic.lower() in all_text.lower():
            found_topics.append(topic)
    
    return found_topics


def get_news_for_symbol(symbol: str, days: int = 7) -> list[dict]:
    """Convenience function to get news for a single symbol."""
    return fetch_stock_news([symbol], days)


if __name__ == "__main__":
    # Test with a sample symbol
    print("Testing news fetcher...")
    news = fetch_stock_news(['BBD', 'VZ'], days=3)
    print(f"Found {len(news)} articles")
    for article in news[:3]:
        print(f"  - [{article.get('symbol')}] {article['title'][:60]}...")