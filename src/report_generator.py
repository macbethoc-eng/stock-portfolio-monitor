"""
Report generator - uses AI to analyze news and generate stock recommendations.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional
import httpx

from .news_fetcher import fetch_stock_news, fetch_general_market_news, get_trending_topics
from .report_state import get_report_state, check_hold_rule
from .storage import load_transactions
from .models import TransactionsFile


# OpenAI-compatible API base (we'll use OpenClaw's AI gateway)
AI_API_BASE = os.environ.get("AI_API_BASE", "https://api.minimax.io/v1")
AI_API_KEY = os.environ.get("AI_API_KEY", "")  # Would need actual key

# Use a simple HTTP call to the AI - in practice you'd use the openclaw agent
# For now, we'll construct prompts and use a simple approach


def build_portfolio_prompt(symbol: str, news: list[dict], hold_info: dict, current_price: float, cost_basis: float) -> str:
    """Build the prompt for portfolio stock analysis."""
    
    news_text = ""
    for i, article in enumerate(news[:5]):
        news_text += f"- [{article.get('source', 'Source')}]({article.get('link', '')}): {article.get('title', '')}\n"
        if article.get('summary'):
            news_text += f"  Summary: {article['summary'][:200]}...\n"
    
    hold_status = "CAN SELL" if hold_info['can_sell'] else "MUST HOLD"
    hold_note = f"{hold_info['reason']} ({hold_info['days_held']} days)"
    
    prompt = f"""You are a stock analyst. Analyze this stock's news and provide a recommendation.

## Stock: {symbol}
- Current Price: ${current_price:.2f}
- Cost Basis: ${cost_basis:.2f}
- Gain/Loss: ${current_price - cost_basis:.2f} ({((current_price - cost_basis) / cost_basis * 100):.2f}%)
- Hold Status: {hold_status} - {hold_note}

## Recent News:
{news_text if news_text else "No recent news found."}

## Output Format:
Return a JSON object with:
{{
  "recommendation": "BUY" | "SELL" | "HOLD" | "WATCH",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "signal": "bullish" | "bearish" | "neutral",
  "summary": "2-3 sentence summary of your analysis",
  "key_points": ["point 1", "point 2", "point 3"],
  "price_target": null or estimated price target,
  "time_horizon": "short" | "medium" | "long"
}}

For SELL recommendation: only if hold rule allows AND there's strong bearish signal.
For HOLD: maintain current position.
For WATCH: uncertain but worth monitoring.
"""
    return prompt


def build_opportunity_prompt(trending: list[str], market_news: list[dict]) -> str:
    """Build the prompt for opportunity identification."""
    
    market_text = ""
    for i, article in enumerate(market_news[:10]):
        market_text += f"- [{article.get('source', 'Source')}]({article.get('link', '')}): {article.get('title', '')}\n"
        if article.get('summary'):
            market_text += f"  {article['summary'][:150]}...\n"
    
    topics_text = ", ".join(trending[:10]) if trending else "General market"
    
    prompt = f"""You are an AI stock market analyst. Based on current news and trends, identify investment opportunities.

## Trending Topics: {topics_text}

## Market News:
{market_text if market_text else "No recent market news."}

## Your Task:
1. Identify 3-5 sectors or themes that appear to have momentum
2. For each sector, suggest 1-2 specific stocks or ETFs that could benefit
3. Consider: tech, healthcare, energy, financials, consumer, industrials
4. Do NOT suggest stocks you already own: BBD, DBX, SNAP, T, VZ, WSE

## Output Format:
Return a JSON object:
{{
  "opportunities": [
    {{
      "sector_theme": "AI Infrastructure",
      "rationale": "Why this sector is trending",
      "stocks": [
        {{"symbol": "NVDA", "reason": "Leader in AI chips", "risk": "high"}},
        {{"symbol": "AMD", "reason": "Competing in AI GPU market", "risk": "medium"}}
      ]
    }}
  ],
  "market_sentiment": "bullish" | "bearish" | "neutral",
  "key_themes": ["theme 1", "theme 2"],
  "overall_advice": "Overall market outlook for next 1-2 weeks"
}}
"""
    return prompt


def call_ai(prompt: str, model: str = "gpt-4o-mini") -> Optional[dict]:
    """Call AI API to get analysis. Returns parsed JSON or None."""
    
    # Try using httpx to call OpenClaw's internal AI gateway
    # Since we're running on the same machine, we can use localhost
    try:
        # Use the openclaw agent's AI endpoint if available
        # For now, return None to indicate we couldn't get AI response
        # In production, you'd integrate with your AI provider
        pass
    except Exception as e:
        print(f"AI call failed: {e}")
    
    return None


def analyze_stock_with_rules(symbol: str, news: list[dict], current_price: float, cost_basis: float) -> dict:
    """
    Analyze a stock with hold rules applied.
    
    Returns dict with recommendation, analysis, and metadata.
    """
    # Check hold rule
    transactions = load_transactions().transactions
    hold_info = check_hold_rule(transactions, symbol)
    
    # Build news summary
    news_summary = ""
    for article in news[:3]:
        news_summary += f"- {article.get('title', '')}\n"
    
    # Simple heuristic-based analysis (when AI is unavailable)
    # This is a fallback - ideally we'd use AI
    
    if not news:
        recommendation = "HOLD"
        signal = "neutral"
        confidence = "LOW"
        summary = "No recent news available. Maintaining position."
        key_points = ["No news to analyze", "Hold for now"]
    else:
        # Simple sentiment scoring based on keywords in news
        bullish_keywords = ['beat', 'bullish', 'upgrade', 'buy', 'growth', 'soar', 'surge', 'rally', 'record', 'high']
        bearish_keywords = ['miss', 'bearish', 'downgrade', 'sell', 'drop', 'fall', 'plunge', 'low', 'cut', 'warning']
        
        score = 0
        text = ' '.join(a.get('title', '') + ' ' + a.get('summary', '') for a in news).lower()
        
        for kw in bullish_keywords:
            if kw in text:
                score += 1
        for kw in bearish_keywords:
            if kw in text:
                score -= 1
        
        gain_pct = ((current_price - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0
        
        # Determine recommendation based on score and gain/loss
        if score >= 2 and hold_info['can_sell']:
            recommendation = "BUY"  # Buy more
            signal = "bullish"
            confidence = "MEDIUM"
        elif score <= -2 and hold_info['can_sell']:
            recommendation = "SELL"
            signal = "bearish"
            confidence = "MEDIUM"
        elif not hold_info['can_sell']:
            recommendation = "HOLD"
            signal = "neutral"
            confidence = "HIGH"
            summary = f"{hold_info['reason']}. {abs(gain_pct):.1f}% unrealized gain/loss."
        else:
            recommendation = "WATCH"
            signal = "neutral"
            confidence = "LOW"
        
        if recommendation == "HOLD" and "Too recent" in hold_info.get('reason', ''):
            summary = f"Hold rule active: {hold_info['reason']}. {abs(gain_pct):.1f}% gain/loss."
        else:
            gain_loss = current_price - cost_basis
            summary = f"{recommendation} recommendation based on {len(news)} news articles. {abs(gain_loss):.2f} gain/loss."
        
        key_points = [
            f"{len(news)} news articles analyzed",
            hold_info['reason'],
            f"Price: ${current_price:.2f} vs Cost ${cost_basis:.2f}"
        ]
    
    return {
        'symbol': symbol,
        'recommendation': recommendation,
        'confidence': confidence,
        'signal': signal,
        'summary': summary,
        'key_points': key_points,
        'hold_info': hold_info,
        'news_count': len(news),
        'analyzed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }


def generate_portfolio_report() -> dict:
    """
    Generate the portfolio news report.
    
    Returns dict with report content and metadata.
    """
    state = get_report_state()
    transactions_file = load_transactions()
    transactions = transactions_file.transactions
    
    # Get unique symbols
    symbols = list(set(t.symbol for t in transactions))
    
    # Fetch news for all portfolio stocks
    all_news = fetch_stock_news(symbols, days=7)
    
    # Filter to only NEW news since last report
    new_news = state.get_portfolio_news_since_last_report(all_news)
    
    # Group news by symbol
    news_by_symbol = {}
    for article in new_news:
        sym = article.get('symbol', 'UNKNOWN')
        if sym not in news_by_symbol:
            news_by_symbol[sym] = []
        news_by_symbol[sym].append(article)
    
    # Analyze each stock
    analyses = []
    from .storage import load_prices_cache
    
    cache = load_prices_cache()
    
    for symbol, news in news_by_symbol.items():
        price_data = cache.prices.get(symbol)
        current_price = price_data.price if price_data else 0.0
        
        # Calculate cost basis for this symbol
        symbol_txns = [t for t in transactions if t.symbol == symbol]
        total_cost = sum(t.quantity * t.price for t in symbol_txns if t.action.value == 'buy')
        total_qty = sum(t.quantity for t in symbol_txns if t.action.value == 'buy')
        avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
        
        analysis = analyze_stock_with_rules(symbol, news, current_price, avg_cost)
        analyses.append(analysis)
    
    # Build markdown report
    report_lines = [
        "# Portfolio News Report",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %I:%M %p ET')}",
        "",
    ]
    
    if not new_news:
        report_lines.extend([
            "## No New News",
            "No new news articles since the last report.",
        ])
    else:
        report_lines.append(f"## Summary ({len(new_news)} new articles across {len(analyses)} stocks)")
        report_lines.append("")
        
        for analysis in analyses:
            rec_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "WATCH": "⚪"}.get(analysis['recommendation'], "⚪")
            
            report_lines.extend([
                f"### {analysis['symbol']} {rec_emoji} {analysis['recommendation']}",
                f"**Signal:** {analysis['signal'].upper()} | **Confidence:** {analysis['confidence']}",
                f"",
                f"{analysis['summary']}",
                f"",
                f"**Hold Status:** {analysis['hold_info']['reason']}",
                f"",
            ])
            
            if analysis['key_points']:
                report_lines.append("**Key Points:**")
                for point in analysis['key_points']:
                    report_lines.append(f"- {point}")
                report_lines.append("")
            
            # List news articles
            if news_by_symbol.get(analysis['symbol']):
                report_lines.append("**Recent Articles:**")
                for article in news_by_symbol[analysis['symbol']][:3]:
                    pub_date = article.get('published', '').strftime('%b %d') if article.get('published') else 'Recent'
                    report_lines.append(f"- [{pub_date}] {article.get('title', '')}")
                report_lines.append("")
    
    report_content = "\n".join(report_lines)
    
    # Save report and state
    state.save_report("portfolio", report_content)
    state.mark_portfolio_report_sent([a['id'] for a in new_news if a.get('id')])
    
    return {
        'report': report_content,
        'new_articles': len(new_news),
        'stocks_analyzed': len(analyses),
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }


def generate_opportunity_report() -> dict:
    """
    Generate the stock opportunities report.
    
    Returns dict with report content and metadata.
    """
    state = get_report_state()
    
    # Fetch general market news
    market_news = fetch_general_market_news(limit=25)
    trending = get_trending_topics()
    
    # Build markdown report
    report_lines = [
        "# Stock Opportunities Report",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %I:%M %p ET')}",
        "",
    ]
    
    if not market_news and not trending:
        report_lines.extend([
            "## No Market Data Available",
            "Unable to fetch market news at this time.",
        ])
    else:
        # Sector/theme analysis based on trending topics
        sectors = identify_sectors(trending, market_news)
        
        report_lines.append("## Market Overview")
        report_lines.append(f"**Trending Topics:** {', '.join(trending[:8]) if trending else 'General market activity'}")
        report_lines.append("")
        
        report_lines.append("## Investment Opportunities")
        report_lines.append("")
        
        for i, sector in enumerate(sectors[:5], 1):
            report_lines.extend([
                f"### {i}. {sector['name']}",
                f"**Rationale:** {sector['rationale']}",
                "",
                "**Suggested Stocks:**",
            ])
            for stock in sector.get('stocks', [])[:3]:
                risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(stock.get('risk', 'medium'), "⚪")
                report_lines.append(f"- {risk_emoji} {stock['symbol']}: {stock['reason']}")
            report_lines.append("")
        
        # Macro themes
        report_lines.extend([
            "## Key Themes",
            "",
        ])
        for theme in trending[:5]:
            report_lines.append(f"- **{theme}**")
        report_lines.append("")
        
        # Overall sentiment
        sentiment = determine_sentiment(market_news, trending)
        report_lines.extend([
            "## Market Sentiment",
            f"**Overall:** {sentiment['overall'].upper()}",
            f"",
            f"{sentiment['explanation']}",
        ])
    
    report_content = "\n".join(report_lines)
    
    # Save report and state
    state.save_report("opportunity", report_content)
    state.mark_opportunity_report_sent(trending[:5])
    
    return {
        'report': report_content,
        'trending_topics': trending[:8],
        'sectors_identified': len(sectors),
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }


def identify_sectors(trending: list[str], news: list[dict]) -> list[dict]:
    """Identify promising sectors based on trending topics and news."""
    
    # Map topics to sectors/stocks
    sector_map = {
        'AI': {
            'name': 'Artificial Intelligence & Semiconductors',
            'rationale': 'AI continues to drive tech spending and innovation',
            'stocks': [
                {'symbol': 'NVDA', 'reason': 'Dominant AI chip maker', 'risk': 'high'},
                {'symbol': 'AMD', 'reason': 'Gaining GPU market share', 'risk': 'medium'},
                {'symbol': 'INTC', 'reason': 'Rebuilding AI capability', 'risk': 'high'},
            ]
        },
        'Federal Reserve': {
            'name': 'Interest Rate Sensitive',
            'rationale': 'Fed policy driving market movements',
            'stocks': [
                {'symbol': 'TLT', 'reason': 'Long-term Treasury bond ETF', 'risk': 'medium'},
                {'symbol': 'KRE', 'reason': 'Regional bank exposure', 'risk': 'high'},
            ]
        },
        'inflation': {
            'name': 'Inflation Hedge',
            'rationale': 'Ongoing inflation concerns affecting portfolios',
            'stocks': [
                {'symbol': 'GLD', 'reason': 'Gold ETF for inflation hedge', 'risk': 'low'},
                {'symbol': 'SLV', 'reason': 'Silver for inflation protection', 'risk': 'medium'},
            ]
        },
        'oil': {
            'name': 'Energy/Oil',
            'rationale': 'Oil prices affecting energy sector',
            'stocks': [
                {'symbol': 'XOM', 'reason': 'Major integrated oil company', 'risk': 'medium'},
                {'symbol': 'CVX', 'reason': 'Strong fundamentals', 'risk': 'medium'},
            ]
        },
        'crypto': {
            'name': 'Cryptocurrency/Fintech',
            'rationale': 'Digital asset adoption continues',
            'stocks': [
                {'symbol': 'MSTR', 'reason': 'Bitcoin treasury holdings', 'risk': 'high'},
                {'symbol': 'COIN', 'reason': 'Leading crypto exchange', 'risk': 'high'},
            ]
        },
        'healthcare': {
            'name': 'Healthcare/Biotech',
            'rationale': 'Healthcare sector under pressure',
            'stocks': [
                {'symbol': 'JNJ', 'reason': 'Defensive healthcare giant', 'risk': 'low'},
                {'symbol': 'UNH', 'reason': 'Leading health insurer', 'risk': 'medium'},
            ]
        },
        'tech': {
            'name': 'Technology',
            'rationale': 'Tech sector leading market recovery',
            'stocks': [
                {'symbol': 'AAPL', 'reason': 'Strong product cycle', 'risk': 'low'},
                {'symbol': 'MSFT', 'reason': 'Cloud and AI leader', 'risk': 'low'},
            ]
        },
        'banking': {
            'name': 'Regional Banks',
            'rationale': 'Banking sector recovery',
            'stocks': [
                {'symbol': 'KEY', 'reason': 'Regional bank turnaround', 'risk': 'high'},
                {'symbol': 'USB', 'reason': 'Diversified bank', 'risk': 'medium'},
            ]
        },
        'housing market': {
            'name': 'Housing/Real Estate',
            'rationale': 'Housing market stabilizing',
            'stocks': [
                {'symbol': 'DHI', 'reason': 'Major homebuilder', 'risk': 'medium'},
                {'symbol': 'PHM', 'reason': 'Affordable housing focus', 'risk': 'medium'},
            ]
        },
    }
    
    identified = []
    news_text = ' '.join(n.get('title', '') + ' ' + n.get('summary', '') for n in news).lower()
    
    for topic, sector_info in sector_map.items():
        if topic.lower() in news_text.lower() or any(topic.lower() in t.lower() for t in trending):
            identified.append(sector_info.copy())
    
    # Add default sectors if not enough found
    if len(identified) < 3:
        default_sectors = [
            {'name': 'Technology', 'rationale': 'Tech remains market leader', 'stocks': [
                {'symbol': 'QQQ', 'reason': 'Nasdaq 100 ETF', 'risk': 'low'},
            ]},
            {'name': 'Dividend Growth', 'rationale': 'Focus on income in uncertain times', 'stocks': [
                {'symbol': 'VYM', 'reason': 'High dividend ETF', 'risk': 'low'},
            ]},
        ]
        for ds in default_sectors:
            if ds['name'] not in [s['name'] for s in identified]:
                identified.append(ds)
    
    return identified[:5]


def determine_sentiment(news: list[dict], trending: list[str]) -> dict:
    """Determine overall market sentiment from news and trends."""
    
    bullish_count = 0
    bearish_count = 0
    
    bullish_terms = ['rally', 'surge', 'gain', 'high', 'record', 'bullish', 'beat', 'growth', 'soar']
    bearish_terms = ['fall', 'drop', 'plunge', 'low', 'bearish', 'miss', 'cut', 'warning', 'decline']
    
    text = ' '.join(n.get('title', '') + ' ' + n.get('summary', '') for n in news).lower()
    
    for term in bullish_terms:
        bullish_count += text.count(term)
    for term in bearish_terms:
        bearish_count += text.count(term)
    
    if bullish_count > bearish_count + 5:
        overall = "bullish"
        explanation = "Positive news dominates. Market sentiment favors upside."
    elif bearish_count > bullish_count + 5:
        overall = "bearish"
        explanation = "Negative news dominates. Market sentiment favors downside."
    else:
        overall = "neutral"
        explanation = "Mixed signals. No strong directional bias."
    
    return {'overall': overall, 'explanation': explanation, 'bullish_count': bullish_count, 'bearish_count': bearish_count}


if __name__ == "__main__":
    print("Testing report generation...")
    result = generate_portfolio_report()
    print(f"Portfolio report: {result['stocks_analyzed']} stocks, {result['new_articles']} new articles")
    print()
    result = generate_opportunity_report()
    print(f"Opportunity report: {result['sectors_identified']} sectors, {len(result.get('trending_topics', []))} topics")