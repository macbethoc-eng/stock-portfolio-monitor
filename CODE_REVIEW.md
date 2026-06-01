# Code Review: Stock Portfolio Monitor

## Summary

The codebase is generally well-structured with clear separation of concerns (models, storage, portfolio calculations, API routes, frontend). The core financial logic (FIFO cost basis, PnL calculations) appears correct and is well-tested. However, there are several significant issues ranging from data model mismatches to security concerns that should be addressed.

---

## Files Reviewed

### Backend (`src/`)
- `models.py` - Pydantic data models
- `storage.py` - JSON file persistence
- `portfolio.py` - Portfolio calculations (FIFO, PnL)
- `price_fetcher.py` - Yahoo Finance integration
- `router.py` - FastAPI API routes
- `main.py` - FastAPI app entry point

### Frontend (`static/`)
- `index.html` - Dashboard HTML
- `app.js` - Frontend JavaScript
- `styles.css` - CSS styles

### Tests (`tests/`)
- `test_models.py` - Model unit tests
- `test_storage.py` - Storage unit tests
- `test_portfolio.py` - Portfolio calculation tests
- `test_price_fetcher.py` - Price fetcher tests

---

## Issues Found

### Critical

#### 1. **Data Model Field Mismatch: `date` vs `transaction_date`**

**Files:** `models.py`, `data/transactions.json`, `DATA_TEMPLATE.json`

The Pydantic `Transaction` model uses field name `transaction_date`, but the actual JSON data files use `date` as the key:

```python
# models.py
transaction_date: DateType = Field(description="Date of the transaction")
```

```json
// data/transactions.json
{"date": "2024-01-15", "action": "buy", ...}
```

This is a **breaking mismatch**. Pydantic v2's `populate_by_name = True` only allows population via the field name or alias — it does NOT remap arbitrary keys. If you load the current `data/transactions.json` directly with `TransactionsFile(**data)`, it will fail with a validation error because `date` is not a valid field name or alias for `transaction_date`.

The app may appear to work because the data file was created before validation was strict, but any new transaction added via the API would use `transaction_date`, creating inconsistent data.

**Fix:** Either rename the Pydantic field to `date`, or add `alias="date"` to the field definition.

---

#### 2. **Overselling Shares — No Validation**

**File:** `src/portfolio.py`

The `PositionState.remove_shares()` method allows selling more shares than owned:

```python
def remove_shares(self, quantity: int) -> tuple[float, float]:
    ...
    self.total_shares -= quantity  # Can go negative!
```

If a sell transaction has `quantity` greater than the available shares, the position's `total_shares` becomes negative. While the financial math (proceeds, cost basis removed) is computed correctly, a negative share count is logically invalid and would corrupt portfolio calculations.

**Fix:** Add validation to reject sells that exceed available shares:
```python
if quantity > self.total_shares:
    raise ValueError(f"Cannot sell {quantity} shares, only {self.total_shares} available")
```

---

#### 3. **Potential XSS via innerHTML in Frontend**

**File:** `static/app.js`

The frontend uses `innerHTML` to render user-controlled data from the API:

```javascript
row.innerHTML = `
    <td class="symbol-cell">${pos.symbol}</td>
    ...
`;
```

While the data originates from the server and is Pydantic-validated, storing transactions in JSON files means a malicious actor with file system access could inject script content. If the symbol field had `<script>` tags, they would execute.

**Risk:** Low (requires local file system access), but still a best practice concern.

**Fix:** Use `textContent` for text nodes, or sanitize with a library.

---

#### 4. **App Binds to `0.0.0.0` — Exposed on All Interfaces**

**File:** `src/main.py`

```python
uvicorn.run(
    "src.main:app",
    host="0.0.0.0",  # Binds to all network interfaces
    port=8765,
    reload=True
)
```

The app binds to all interfaces (`0.0.0.0`), making it accessible on the local network. While there's no authentication on the API (which is fine for a local-only app), this could expose portfolio data to other users on the same network.

**Fix:** Bind to `127.0.0.1` for local-only access, or document this clearly.

---

### Medium

#### 5. **No Input Validation on Symbol Format**

**File:** `src/models.py`

The `Transaction.symbol` field only validates length (1-10 chars):
```python
symbol: str = Field(min_length=1, max_length=10)
```

There's no validation for valid ticker symbol format (e.g., uppercase letters, no special characters, no spaces). Malformed symbols could cause issues with the Yahoo Finance API or downstream calculations.

**Fix:** Add a regex pattern validator:
```python
symbol: str = Field(min_length=1, max_length=10, pattern=r'^[A-Z]+$')
```

---

#### 6. **API Returns Raw Exception Messages**

**File:** `src/router.py`

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

Raw exception messages are returned to API clients. This could leak internal implementation details or file paths in error responses.

**Fix:** Return a generic error message and log the actual exception:
```python
except Exception as e:
    logging.error(f"Price refresh failed: {e}")
    raise HTTPException(status_code=500, detail="Price refresh failed")
```

---

#### 7. **No Rate Limiting on Price Refresh**

**File:** `src/router.py` — `POST /api/prices/refresh`

The price refresh endpoint has no rate limiting. A malicious or careless client could spam this endpoint, causing:
- Yahoo Finance API rate limits
- Excessive network requests
- Potential IP blocking from Yahoo

**Fix:** Add rate limiting middleware (e.g., `slowapi`) or a cooldown mechanism.

---

#### 8. **No Price Freshness Enforcement**

**File:** `src/router.py`

The `/api/portfolio` endpoint returns data even if prices are stale (hours/days old). There's no validation on the server side to warn or reject stale price data.

**Fix:** Add optional `max_age_minutes` parameter, or include a `is_stale` flag in the response.

---

#### 9. **Silent Failure on Price Fetch**

**File:** `src/price_fetcher.py`

```python
except Exception as e:
    print(f"Error fetching price for {symbol}: {e}")
    return None
```

Price fetch failures are silent — they print to stdout but otherwise fail gracefully. In a production context, this could lead to silently missing price data without clear indication in the API response.

**Fix:** Consider returning partial results with a warning flag, or log to a proper logging framework with levels.

---

#### 10. **Duplicate `get_utc_now()` Functions**

**File:** `src/portfolio.py` and `src/price_fetcher.py`

Both modules define the same `get_utc_now()` function:
```python
def get_utc_now() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
```

This is code duplication and could lead to inconsistencies.

**Fix:** Move to a shared utility module (e.g., `src/utils.py`).

---

### Minor

#### 11. **Test Coverage Gaps**

- **No tests for `router.py` API endpoints** — the API routes have no integration tests
- **No tests for sell validation** — selling more shares than owned has no test
- **No tests for stale price handling** — price staleness logic untested
- **No tests for edge cases** — empty portfolio, single position, zero prices

#### 12. **Hardcoded Port in main.py**

The port `8765` is hardcoded and not configurable via environment variables, making deployment less flexible.

#### 13. **No Logging Configuration**

The application uses `print()` for errors rather than Python's `logging` module. This makes debugging in production difficult.

#### 14. **Inconsistent Error Handling in `compute_positions`**

**File:** `src/portfolio.py`

```python
if price_data is None:
    continue  # Skip if no price data
```

When a symbol has no price data, it's silently skipped with no warning to the user. If all symbols lack price data, the portfolio returns empty with no error indication.

---

## Recommendations

### Priority 1 (Critical Fixes)
1. **Fix the `date` vs `transaction_date` field mismatch** — this is a data corruption bug
2. **Add sell quantity validation** to prevent negative share counts
3. **Change `host="0.0.0.0"` to `host="127.0.0.1"`** or document the network exposure

### Priority 2 (High Value)
4. Add symbol format validation (regex pattern)
5. Add rate limiting to `/api/prices/refresh`
6. Sanitize API error messages (don't leak exception details)
7. Add router/API integration tests

### Priority 3 (Improvements)
8. Move `get_utc_now()` to a shared utility
9. Configure proper logging instead of `print()`
10. Add price freshness validation
11. Use `textContent` instead of `innerHTML` for text rendering

---

## Positive Notes

- **FIFO implementation** is correct and well-tested
- **Pydantic models** provide good validation with clear error messages
- **Test coverage** of core financial logic is excellent
- **Code organization** is clean with clear separation of concerns
- **Data storage** is simple and transparent (JSON files)
- **The UI** is well-designed and handles loading/error states properly