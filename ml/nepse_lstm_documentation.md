# NEPSE Stock Price Prediction using LSTM
## Data Cleaning & Feature Engineering Documentation

---

## 1. Dataset Overview

- **Source**: NEPSE full market historical data (`nepse_full_market.csv`)
- **Raw shape**: 342,792 rows, 9 columns
- **Columns**: `date, open, high, low, close, pct_change, volume, turnover, symbol`
- **Date range**: 2021-01-03 to 2026-06-05

---

## 2. Data Cleaning

### 2.1 Type Conversion & Sorting
- Converted `date` column from string to `datetime64` using `pd.to_datetime()`.
- Sorted data by `['symbol', 'date']` to ensure chronological order **within each stock**, preventing cross-contamination of time-dependent features between different symbols.

### 2.2 Duplicate Removal
- Checked for duplicate `(symbol, date)` pairs using `df.duplicated()`.
- **Result**: 0 duplicates found initially at first check; later re-verified after re-load — dropped using `keep='first'`.

### 2.3 Invalid Price Validation
Checked for values that are structurally impossible in financial data:

| Check | Condition | Result |
|---|---|---|
| Non-positive prices | `open, high, low, close ≤ 0` | 0 rows |
| Negative volume | `volume < 0` | 0 rows |
| Negative turnover | `turnover < 0` | 0 rows |

### 2.4 OHLC Consistency Validation

**Invariant enforced:**
```
low ≤ open, close ≤ high
high ≥ open, close ≥ low
```

**Violation detected**: 909 rows (~0.27%) violated this rule.

**Correction applied** (patch method, preserves row count):
```
high_corrected = max(open, high, low, close)
low_corrected  = min(open, high, low, close)
```

This guarantees the OHLC invariant holds for every row without discarding data. It is a heuristic correction (not a recovery of the true high/low) applied to the affected rows only.

### 2.5 Trading Continuity Check

**Formula:**
```
date_diff(t) = date(t) - date(t-1)   [per symbol]
```

Rows where `date_diff > 30 days` were flagged as abnormal gaps (beyond normal weekend/holiday spacing).

**Result**: 11 symbols had at least one gap > 30 days (max 2 occurrences per symbol) — negligible impact on the final selected symbols.

### 2.6 Corporate Action (Bonus Share / Split) Detection

**Formula for recalculated percentage change:**
```
pct_change_calc(t) = [ close(t) - close(t-1) ] / close(t-1) × 100
```

**Mismatch metric:**
```
pct_diff(t) = | pct_change_reported(t) - pct_change_calc(t) |
```

Rows with `pct_diff > 5` were flagged via a binary indicator:
```
split_flag(t) = 1  if pct_diff(t) > 5
              = 0  otherwise
```

**Result**: 381 rows (~0.18%) flagged — consistent with bonus share / rights share adjustments common in NEPSE-listed companies. The dataset's original `pct_change` column was retained as the primary return feature (assumed to be corporate-action-adjusted), while `split_flag` was kept as an auxiliary feature marking unusual events.

### 2.7 Extreme Move Verification

Rows with `|pct_change| > 10%` (25 rows) were manually cross-referenced against surrounding OHLC data and confirmed to be **legitimate price movements** (verified via exact recomputation from consecutive close prices), not data errors. NEPSE's circuit breaker is not a strict ±10% cap and varies by price tier/segment (values up to ±15% were observed).

### 2.8 Symbol Filtering

- Symbols with `< 100` total trading days were removed (544 → 430 symbols) — insufficient length for LSTM sequence windows.
- Further narrowed to symbols with `> 1000` rows (172 symbols) as a candidate pool for final selection.

### 2.9 Final Cleaned Dataset
- Shape: **211,803 rows × 10 columns**
- Saved as checkpoint: `nepse_cleaned.csv`

---

## 3. Exploratory Data Analysis (Summary)

| Analysis | Purpose | Key Finding |
|---|---|---|
| `describe()` summary stats | Understand scale/spread | `close` ranges Rs. 6.78–55,000 → per-symbol scaling required |
| Distribution histograms | Visualize skew | `close` and `volume` heavily right-skewed → log-transform recommended for `volume`/`turnover` |
| Correlation heatmap | Detect redundancy | `open/high/low/close` correlated at 1.00 (perfect multicollinearity); `volume`/`turnover` correlated at 0.71 |
| Turnover ranking | Liquidity assessment | Used to identify actively-traded symbols |
| Volatility ranking | Risk profiling | `std(pct_change)` per symbol, used for symbol selection balance |
| Market-wide normalized index | Sector-level trend | Base-100 index per symbol: `close_norm(t) = close(t) / close(0) × 100`, then averaged across symbols per date |

---

## 4. Final Symbol Selection

**Selection criteria:**
1. Complete trading history: `days == 1262` (no missing trading days across the full date range)
2. High liquidity: ranked by `avg_turnover`
3. Sector diversity: manually balanced across NEPSE sectors (rather than pure volatility/liquidity ranking) to enable cross-sector performance comparison

**Final 10 symbols:**

| Symbol | Sector |
|---|---|
| NABIL | Commercial Bank |
| NICA | Commercial Bank |
| NLIC | Life Insurance |
| NRIC | Non-Life Insurance / Reinsurance |
| SHIVM | Manufacturing (Cement) |
| HDL | Manufacturing (Distillery) |
| NTC | Telecom / Others |
| AHPC | Hydropower |
| UPPER | Hydropower |
| NGPL | Hydropower |

*Note: sector labels were cross-referenced against public NEPSE company classifications, not derived from a column in the raw dataset.*

**Resulting subset**: `df_selected` — 10 symbols × 1,262 trading days ≈ 12,620 rows.

---

## 5. Feature Engineering

### 5.1 Log Return

```
log_return(t) = ln( close(t) / close(t-1) )
```

Computed per symbol using `groupby('symbol')`. Preferred over simple percentage change because log returns are:
- **Time-additive**: multi-period log returns are the sum of single-period log returns.
- **More symmetric**: better-behaved distribution for modeling than simple returns.

First row of each symbol is `NaN` (no prior close available).

### 5.2 Daily Range

```
daily_range(t) = high(t) - low(t)
```

Captures intraday volatility, independent of direction. No `NaN` values (does not depend on prior rows).

### 5.3 Opening Gap

```
prev_close(t) = close(t-1)          [per symbol]
gap(t) = open(t) - prev_close(t)
```

Captures the overnight price jump between the previous close and the current session's open — reflects information/sentiment shifts occurring outside trading hours. First row of each symbol is `NaN`.

---

## 6. Known Limitations (for methodology/limitations section)

1. **OHLC correction (Section 2.4)** is a heuristic patch for 909 rows (~0.27%), not a recovery of true historical values.
2. **Split adjustment (Section 2.6)** uses the dataset's provided `pct_change` as a proxy for a corporate-action-adjusted return series rather than fully reconstructing a split-adjusted price history.
3. **Sector classification** for the final 10 symbols was manually mapped from public sources, not present as a native column in the dataset.
4. Feature engineering (Section 5) has not yet included scaling — given the wide price-level variation across symbols (confirmed in Section 3), **scaling must be performed per-symbol** (e.g., separate `MinMaxScaler`/`StandardScaler` fit per symbol on training data only) rather than globally, to avoid distorting low-price stocks.

---

*Document reflects pipeline state as of feature engineering step: log_return, daily_range, gap.*
