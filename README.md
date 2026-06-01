# Stock Portfolio Monitor

A minimal, local portfolio tracker for macOS. Track your stock positions, view live PnL, and monitor your portfolio — all without cloud accounts or complex setup.

## Features

- **Transaction-based positions**: Add buy/sell transactions to build positions
- **Live price fetching**: Yahoo Finance integration
- **Comprehensive metrics**: Today's gain/loss, total gain/loss, cost basis, position sizing
- **Local-first**: Your data stays on your machine
- **Clean dashboard**: Dark-themed web UI

## Quick Start

```bash
# Clone the repo
git clone https://github.com/macbethoc/stock-portfolio-monitor.git
cd stock-portfolio-monitor

# Install dependencies
pip install -r requirements.txt

# Copy the template and add your transactions
cp DATA_TEMPLATE.json data/transactions.json
# Edit data/transactions.json with your actual trades

# Run the server
python -m src.main

# Open in browser
open http://localhost:8765
```

## Configuration

Edit `data/transactions.json` to add your trades:

```json
{
  "transactions": [
    {
      "id": "uuid-here",
      "symbol": "BBD",
      "quantity": 100,
      "price": 12.50,
      "date": "2024-01-15",
      "action": "buy"
    }
  ]
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Full portfolio with all positions |
| GET | `/api/prices` | Current cached prices |
| POST | `/api/prices/refresh` | Force refresh prices |
| GET | `/api/transactions` | List all transactions |
| POST | `/api/transactions` | Add a transaction |
| DELETE | `/api/transactions/{id}` | Remove a transaction |

## Architecture

```
stock-portfolio-monitor/
├── src/
│   ├── main.py          # FastAPI entry point
│   ├── models.py        # Pydantic data models
│   ├── portfolio.py     # Portfolio calculations
│   ├── price_fetcher.py # Yahoo Finance integration
│   ├── storage.py       # JSON file persistence
│   └── router.py        # API routes
├── static/
│   ├── index.html       # Dashboard UI
│   ├── styles.css
│   └── app.js           # Frontend logic
├── tests/               # pytest unit tests
└── data/                # Local data storage (gitignored)
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT
