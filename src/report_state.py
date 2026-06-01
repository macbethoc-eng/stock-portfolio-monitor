"""
Report state management - tracks what news has been sent in reports.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TransactionsFile, PriceData


DATA_DIR = Path(__file__).parent.parent / "data"
REPORT_STATE_FILE = DATA_DIR / "report_state.json"


def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class ReportState:
    """Manages report state for tracking which news has been reported."""
    
    def __init__(self):
        self.last_portfolio_report: Optional[str] = None
        self.last_opportunity_report: Optional[str] = None
        self.portfolio_news_sent: list[str] = []
        self.opportunity_news_sent: list[str] = []
        self._load()
    
    def _load(self):
        """Load state from disk."""
        if REPORT_STATE_FILE.exists():
            try:
                with open(REPORT_STATE_FILE, "r") as f:
                    data = json.load(f)
                self.last_portfolio_report = data.get("last_portfolio_report")
                self.last_opportunity_report = data.get("last_opportunity_report")
                self.portfolio_news_sent = data.get("portfolio_news_sent", [])
                self.opportunity_news_sent = data.get("opportunity_news_sent", [])
            except Exception as e:
                print(f"Error loading report state: {e}")
    
    def _save(self):
        """Save state to disk."""
        data = {
            "last_portfolio_report": self.last_portfolio_report,
            "last_opportunity_report": self.last_opportunity_report,
            "portfolio_news_sent": self.portfolio_news_sent,
            "opportunity_news_sent": self.opportunity_news_sent,
        }
        with open(REPORT_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def mark_portfolio_report_sent(self, news_ids: list[str]):
        """Mark that a portfolio report was sent with these news IDs."""
        self.last_portfolio_report = get_utc_now()
        self.portfolio_news_sent = news_ids
        self._save()
    
    def mark_opportunity_report_sent(self, topics: list[str]):
        """Mark that an opportunity report was sent for these topics."""
        self.last_opportunity_report = get_utc_now()
        self.opportunity_news_sent = topics
        self._save()
    
    def get_portfolio_news_since_last_report(self, all_news: list[dict]) -> list[dict]:
        """Filter news to only those since last portfolio report."""
        if not self.last_portfolio_report:
            # First run - return all recent news
            return all_news[:20]
        
        try:
            last_time = datetime.fromisoformat(self.last_portfolio_report.replace('Z', '+00:00'))
        except ValueError:
            return all_news[:20]
        
        filtered = []
        for article in all_news:
            if article.get('published') and article['published'] > last_time:
                filtered.append(article)
            elif article.get('published') is None:
                # If no date, include it (might be recent)
                filtered.append(article)
        
        return filtered
    
    def load_report(self, report_type: str) -> Optional[str]:
        """Load a saved report from disk."""
        report_file = DATA_DIR / f"{report_type}_report.md"
        if report_file.exists():
            with open(report_file, "r") as f:
                return f.read()
        return None
    
    def save_report(self, report_type: str, content: str):
        """Save a report to disk."""
        report_file = DATA_DIR / f"{report_type}_report.md"
        with open(report_file, "w") as f:
            f.write(content)


def get_report_state() -> ReportState:
    """Get the singleton report state instance."""
    return ReportState()


def days_since_transaction(transaction_date: str) -> int:
    """Calculate days since a transaction date."""
    try:
        txn_date = datetime.fromisoformat(transaction_date.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - txn_date
        return delta.days
    except (ValueError, TypeError):
        return 999  # Assume very old if can't parse


def check_hold_rule(transactions: list, symbol: str, min_days: int = 30) -> dict:
    """
    Check if a stock has been held long enough to consider selling.
    
    Returns:
        dict with 'can_sell' (bool), 'days_held' (int), 'min_days' (int)
    """
    symbol_txns = [t for t in transactions if t.symbol == symbol]
    
    if not symbol_txns:
        return {'can_sell': False, 'days_held': 0, 'min_days': min_days, 'reason': 'No transactions found'}
    
    # Find the most recent buy
    buy_txns = [t for t in symbol_txns if t.action.value == 'buy']
    if not buy_txns:
        return {'can_sell': True, 'days_held': 999, 'min_days': min_days, 'reason': 'No buy transactions'}
    
    # Get the most recent buy date
    most_recent_buy = max(buy_txns, key=lambda t: t.transaction_date)
    
    days_held = days_since_transaction(most_recent_buy.transaction_date.isoformat())
    can_sell = days_held >= min_days
    
    if not can_sell:
        reason = f"Too recent to sell - only {days_held} days held, minimum {min_days} required"
    else:
        reason = f"Hold period met - {days_held} days held"
    
    return {
        'can_sell': can_sell,
        'days_held': days_held,
        'min_days': min_days,
        'reason': reason,
        'last_buy_date': most_recent_buy.transaction_date.isoformat()
    }