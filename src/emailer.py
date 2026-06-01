"""
Email delivery using himalaya CLI.
"""
import subprocess
from datetime import datetime, timezone
from pathlib import Path


RECIPIENT = "mark.sharrock@me.com"
EMAIL_FROM = "macbeth.oc@icloud.com"


def get_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def send_email(to: str, subject: str, body_html: str, body_text: str = "") -> bool:
    """
    Send email via himalaya CLI.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body_html: HTML body
        body_text: Plain text fallback
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        now = get_utc_now()
        
        if not body_text:
            body_text = body_html.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n')
        
        # Build raw email message with From and To headers
        email_content = f"""From: {EMAIL_FROM}
To: {to}
Subject: {subject}
Content-Type: text/html; charset=utf-8

{body_html}
"""
        
        # Use himalaya message send via stdin
        result = subprocess.run(
            ["himalaya", "message", "send"],
            input=email_content,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"Email sent to {to}: {subject}")
            return True
        else:
            print(f"Email send failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("himalaya CLI not found - email not sent")
        return False
    except subprocess.TimeoutExpired:
        print("Email send timed out")
        return False
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def send_portfolio_report(report: str) -> bool:
    """Send portfolio news report via email."""
    subject = f"📊 Portfolio News Report - {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; }}
        h2 {{ color: #16213e; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h3 {{ color: #0f3460; }}
        .buy {{ color: green; font-weight: bold; }}
        .sell {{ color: red; font-weight: bold; }}
        .hold {{ color: orange; font-weight: bold; }}
        .watch {{ color: gray; font-weight: bold; }}
        .bullish {{ color: green; }}
        .bearish {{ color: red; }}
        .neutral {{ color: gray; }}
        .card {{ background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .signal {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        .signal-buy {{ background: #d4edda; color: #155724; }}
        .signal-sell {{ background: #f8d7da; color: #721c24; }}
        .signal-hold {{ background: #fff3cd; color: #856404; }}
        .signal-watch {{ background: #e2e3e5; color: #383d41; }}
    </style>
</head>
<body>
    <div class="container">
        {report.replace('#', '').replace('## ', '<h2>').replace('### ', '<h3>').replace('**', '<strong>').replace('\n', '<br>')}
    </div>
</body>
</html>
"""
    
    return send_email(RECIPIENT, subject, html)


def send_opportunity_report(report: str) -> bool:
    """Send opportunity report via email."""
    subject = f"💰 Stock Opportunities - {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; }}
        h2 {{ color: #16213e; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h3 {{ color: #0f3460; }}
        .sector {{ background: #f0f4ff; border-radius: 8px; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }}
        .bullish {{ color: green; font-weight: bold; }}
        .bearish {{ color: red; font-weight: bold; }}
        .neutral {{ color: gray; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        {report.replace('#', '').replace('## ', '<h2>').replace('### ', '<h3>').replace('**', '<strong>').replace('\n', '<br>').replace('- ', '<li>')}
    </div>
</body>
</html>
"""
    
    return send_email(RECIPIENT, subject, html)