# Stock Portfolio Monitor — SPEC.md

## 1. Concept & Vision

A minimal, focused portfolio tracker that lives on your Mac. Enter your transactions once, and the app fetches live prices to show you exactly where you stand — today's PnL, total PnL, cost basis, and position sizing. No account needed, no cloud sync, just a local web server and a clean dashboard.

**Tech Stack**: Python FastAPI backend + vanilla HTML/JS frontend. No build step. Data stored in local JSON files.

---

## 2. Design Language

- **Aesthetic**: Terminal-meets-finance. Dark theme with monospace accents. Clean data density.
- **Colors**:
  - Background: `#0d1117` (GitHub dark)
  - Surface: `#161b22`
  - Border: `#30363d`
  - Text primary: `#e6edf3`
  - Text muted: `#8b949e`
  - Positive/gain: `#3fb950` (green)
  - Negative/loss: `#f85149` (red)
  - Accent: `#58a6ff` (blue)
- **Typography**: `JetBrains Mono` for numbers, `Inter` for labels
- **Motion**: Minimal — subtle fade-in on load, flash on price updates

---

## 3. Architecture

```
stock-portfolio-monitor/
├── SPEC.md
├── README.md
├── requirements.txt
├── .gitignore
├── DATA_TEMPLATE.json          # Transaction template (committed)
├── data/
│   ├── transactions.json        # Actual transactions (NOT committed)
│   └── prices_cache.json       # Price cache (NOT committed)
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── models.py               # Pydantic data models
│   ├── portfolio.py            # Portfolio calculations
│   ├── price_fetcher.py        # Yahoo Finance fetcher
│   ├── storage.py              # JSON file persistence
│   └── router.py               # API routes
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_portfolio.py
    ├── test_price_fetcher.py
    └── test_storage.py
```

---

## 4. Data Models

### Transaction
```json
{
  "id": "uuid",
  "symbol": "BBD",
  "quantity": 100,
  "price": 12.50,
  "date": "2024-01-15",
  "action": "buy" | "sell"
}
```

### Position (computed)
```json
{
  "symbol": "BBD",
  "quantity": 150,
  "avgCost": 11.20,
  "costBasis": 1680.00,
  "currentPrice": 10.50,
  "currentValue": 1575.00,
  "todayGain": -15.00,
  "todayGainPercent": -0.94,
  "totalGain": -105.00,
  "totalGainPercent": -6.25,
  "percentOfAccount": 15.75
}
```

### Portfolio Summary (computed)
```json
{
  "totalValue": 10000.00,
  "totalCostBasis": 8500.00,
  "totalTodayGain": 125.50,
  "totalTodayGainPercent": 1.27,
  "totalGain": 1500.00,
  "totalGainPercent": 17.65,
  "positions": [...]
}
```

---

## 5. Features & Interactions

### Core Features

1. **Transaction Management**
   - Load transactions from `data/transactions.json`
   - Support buy/sell transactions
   - Multiple transactions per symbol build up position
   - FIFO-style cost basis calculation

2. **Price Fetching**
   - Fetch current prices from Yahoo Finance API
   - Cache prices in `data/prices_cache.json`
   - Refresh on demand (manual button)
   - Store cache timestamp

3. **Portfolio Dashboard**
   - Show all positions with columns:
     - Symbol
     - Quantity
     - Cost Basis
     - Last Price
     - Current Value
     - Today's Gain/Loss ($ and %)
     - Total Gain/Loss ($ and %)
     - % of Account
   - Summary row at bottom: totals
   - Grand totals row

4. **Refresh Button**
   - Fetches latest prices
   - Recalculates all metrics
   - Shows last updated timestamp

### UI States

- **Loading**: Skeleton shimmer while fetching prices
- **Error**: Red banner if price fetch fails
- **Empty**: Message if no transactions exist
- **Stale**: Warning if prices older than 15 minutes

---

## 6. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Full portfolio with all positions |
| GET | `/api/prices` | Current cached prices |
| POST | `/api/prices/refresh` | Force refresh prices from Yahoo |
| GET | `/api/transactions` | List all transactions |
| POST | `/api/transactions` | Add a transaction |
| DELETE | `/api/transactions/{id}` | Remove a transaction |

---

## 7. Price Fetching

- **Source**: Yahoo Finance via `yfinance` Python package
- **Fallback**: If yfinance fails, use cached prices with warning
- **Cache**: Store in `data/prices_cache.json` with timestamp
- **Symbols**: Read from transactions dynamically (no hardcoded list)

---

## 8. Testing Strategy (TDD)

Tests drive the core calculation logic:

1. **test_models.py**: Validate Pydantic models
2. **test_portfolio.py**:
   - Test cost basis calculation with multiple transactions
   - Test FIFO sell logic
   - Test gain/loss calculations
3. **test_storage.py**: Test JSON read/write
4. **test_price_fetcher.py**: Mocked tests for price fetching

---

## 9. GitHub & Data Privacy

- **Repo**: `macbethoc/stock-portfolio-monitor`
- **Committed**: All code, tests, templates, requirements
- **NOT Committed** (via `.gitignore`):
  - `data/transactions.json` (actual holdings)
  - `data/prices_cache.json` (live data)
- **DATA_TEMPLATE.json**: Example structure, committed as reference

---

## 10. Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Copy template to create your transactions
cp DATA_TEMPLATE.json data/transactions.json

# Run the server
python -m src.main

# Open in browser
open http://localhost:8765
```

---

## 11. Initial Stocks

Per Mark's request, starting with:
- BBD (Bank of Montreal)
- DBX (Dropbox)
- SNAP (Snap Inc.)
- T (AT&T)
- VZ (Verizon)
- WSE (Waters Corporation)

These will be added to the template transactions file with placeholder data.
