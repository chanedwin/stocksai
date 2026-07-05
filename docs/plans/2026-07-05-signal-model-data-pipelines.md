# Plan: Data Pipelines for Cross-Sectional Signal Models

> **Status:** Approved plan, not yet built. Written 2026-07-05.
> **Purpose:** Extend the app from a live single-ticker dashboard into a research platform that collects technical, fundamental, and alternative data over time and trains cross-sectional equity signal models on it.
> **Framing:** Everything here produces analysis, signals, and indicators for research and education. No output is financial advice, and no model score is a buy/sell recommendation (CLAUDE.md sections 2 and 7).

---

## 1. Where the repo stands today

The nine existing pipeline modules are dashboard-oriented: every call fetches on demand from yfinance (plus one GitHub congress-trades feed), returns in-memory frames, and persists nothing. Two kinds of data flow through them, and the distinction drives this whole plan:

| Kind | Modules | Usable for training data? |
|---|---|---|
| True history (replayable at past dates) | `data_fetcher.fetch_price_data` (OHLCV), `technical_analysis.compute_indicators` (vectorized over full history), `market_context.get_earnings_impact` (earnings event study), peer/macro price downloads | Yes, directly |
| Current-only snapshots (no as-of date, restated values) | `fundamental_analysis` ratios (yfinance `info`), `flow_analysis` (ownership, short interest, options chains, insider window), analyst endpoints, `pattern_detection.compute_trend_scores`, `signal_aggregator` composite | No. Joining today's snapshot to past prices trains on information the market did not have. Display only. |

Concrete gaps that block model building: no disk persistence, no scheduler, no multi-ticker batch path, no point-in-time fundamentals, no record of snapshot-type data over time, and signal functions that evaluate only the latest bar.

The plan below fixes these in an order chosen from three competing drafts (MVP-first, correctness-first, breadth-first) that were scored through feasibility, methodological soundness, and coverage lenses. The synthesis: a fast path to one honestly evaluated price-only model, with the unrecoverable forward collectors shipped first because their history only exists if collection starts now, and point-in-time rules enforced as infrastructure from day one so later sources join safely.

---

## 2. Standing rules (apply to all work under this plan)

1. **Two timestamps on every fact.** Every silver-layer row carries `event_time` (when the fact occurred: period end, trade date, observation date) and `knowledge_time` (when it became public: EDGAR `filed` date, FINRA dissemination date, our own `captured_at` for snapshots). Feature joins key on `knowledge_time` only. A fact with no defensible `knowledge_time` never enters a training set.
2. **Snapshot ban.** Output from modules that read yfinance `.info` or any other undated snapshot never joins a training panel. Those values are dashboard display, or raw material for the forward-snapshot archive, nothing else.
3. **Bronze is append-only.** Raw payloads are written exactly as received, with `fetched_at` timestamps, and never mutated. Silver and gold are rebuildable from bronze at any time. Bronze is the only irreplaceable layer and gets backed up offsite.
4. **Per-date cross-sectional rank normalization, no fitted scalers.** Every feature is ranked across the universe per date and mapped to [-1, 1], missing filled with 0 plus a paired `_missing` flag (Gu-Kelly-Xiu convention). No scaler, imputer, or selector is ever fitted on pooled history.
5. **Leakage tripwires run on every gold build** (section 8). A suspiciously good result fails the build.
6. **Every experiment is logged.** Trial counts feed the significance bar. A null result still ships, reported as "no reliable signal found at this horizon."
7. **New source checklist:** bronze-first with `fetched_at`, declared `knowledge_time` rule before any feature uses it, registered coverage-start date, pandera schema, one edge-case test (split day, holiday, or missing data), matching section in `docs/research-pipelines.md` in the same commit.
8. **Dates:** ISO 8601, stored and processed in UTC. Business-day arithmetic goes through an exchange calendar library (`exchange_calendars` or `pandas_market_calendars`), never naive weekday math. Collector schedules are pinned to America/New_York with DST handled, since "after the close" is an exchange-time concept.
9. **Vocabulary and disclaimers:** model output is a "score", "rank", or "signal"; user-facing surfaces carry the education disclaimer plus a survivorship-bias note where the free-universe compromise applies. A grep-based lint in the test suite keeps advice language out.

---

## 3. Universe, horizon, and labels

| Decision | Choice | Rationale |
|---|---|---|
| Universe | S&P 500 with point-in-time membership | Liquid names avoid the microcap concentration of reversal/IVOL/MAX/Amihud effects; free membership history exists |
| Membership source | `fja05680/sp500` historical constituents CSV, vendored into `data/reference/` with attribution, refreshed quarterly from Wikipedia's changes table | Only free point-in-time source. Spot-check known add/drop events and per-date member counts before trusting it |
| Price history | 2010-01-01 forward, daily bars | Several regimes, fits free-tier backfill quotas, EDGAR XBRL and FINRA archives reach back that far |
| Label | Forward 21-trading-day return minus the equal-weight universe mean over the same window; secondary 5-day variant | Relative ranking is the task; excess return removes the common market move. Monthly cadence keeps turnover below the ~50%/month band where costs erase signals |
| Rebalance / scoring | Monthly (last trading day) | Fewer overlapping labels, cheaper evaluation, standard in the literature |
| Delisting policy | If a stock stops trading inside the label window, the label uses the return through the last traded day and assumes zero excess return for the remainder; the row is flagged `label_truncated`. Counts of truncated and dropped rows are reported with every dataset build. Silent dropping is forbidden (it biases labels upward) | Cheap, explicit, honest v1. A Shumway-style delisting-return assumption can replace the zero-fill later |
| Sector handling | GICS sector from the constituents table for sector-relative diagnostics; EDGAR SIC code as the point-in-time fallback. Report sector-neutralized rank IC alongside raw IC | Without it, a "signal" can be a sector bet in disguise |
| Survivorship stance | Point-in-time membership plus a price source that retains delisted tickers (Tiingo permaTicker). Measure and report the per-year fraction of historical members with missing prices. Disclose the residual bias in the dashboard and in every result | The accepted free-stack compromise; disclosure instead of a $630/yr Norgate subscription until the project earns it |

Scale check: 500 tickers x 16 years is roughly 2M OHLCV rows, well under 500 MB as Parquet. Everything runs on a laptop; forward collectors need an always-on host (small VPS or an always-on Mac with launchd catch-up semantics).

---

## 4. Storage and architecture

Parquet + DuckDB, cron + typer CLIs, no database server, no orchestrator framework. Prefect only if cron demonstrably fails; skip Dagster and DVC.

```
data/
  reference/                  # git-tracked: constituents CSV, symbol map, concept map, sector map
  bronze/                     # append-only raw payloads, never mutated
    tiingo_prices/ingest_date=YYYY-MM-DD/
    edgar/companyfacts/ingest_date=YYYY-MM-DD/
    finra_short_interest/settlement=YYYY-MM-DD/
    av_earnings/ingest_date=YYYY-MM-DD/
    fred/{series_id}/vintage_date=YYYY-MM-DD/
    congress_trades/ingest_date=YYYY-MM-DD/
    news/{source}/ingest_date=YYYY-MM-DD/
    snapshots/{option_chains,yf_info,analyst_estimates}/capture_date=YYYY-MM-DD/
  silver/                     # validated canonical Parquet, hive-partitioned by year, ticker-sorted
    prices/year=YYYY/
    fundamentals_facts/year=YYYY/
    shares_outstanding/ ...
  gold/
    features-{sha256[:12]}/panel.parquet + manifest.json
  state/
    pipeline.sqlite           # watermarks per (source, ticker), run log, quota ledger, http cache
```

- **Query engine:** DuckDB over hive-partitioned Parquet; `ASOF LEFT JOIN` builds gold panels in SQL. Partition by year, never by ticker.
- **Idempotency:** watermark table keyed `(source, ticker)`; each run fetches `[watermark+1, today]`, rewrites whole affected partitions to a `.partial` path, atomically renames (the CLAUDE.md checkpoint rule), then advances the watermark. Rerunning a day produces identical bytes. Backfill is the same CLI with explicit `--start/--end`.
- **Corporate-action drift guard:** adjusted closes are rewritten across full history whenever a new split or dividend lands, so incremental ingestion alone corrupts old partitions. Store raw close plus split/dividend events, detect new corporate actions per ticker on each run, and trigger a full-history rebuild of that ticker's silver rows when one appears.
- **Validation:** pandera schemas at the bronze-to-silver boundary (dtypes, `high >= low`, `volume >= 0`, unique `(ticker, date)`, monotonic dates, no future timestamps, split-day sanity). Failing rows quarantine to `silver/_rejects/` with reasons; nothing drops silently.
- **Resilience:** tenacity exponential backoff with jitter per ticker fetch (never around the whole run); requests-cache for REST sources; client-side token bucket at 8 req/s for EDGAR with the mandatory `User-Agent: stocks-research <owner email>` header.
- **Quota ledger:** shared free-tier budgets (Alpha Vantage 25 req/day serves three consumers) are arbitrated by a priority ledger in the state DB, so one consumer cannot silently starve the others. Quota gaps are recorded in the run log, never silently skipped.
- **Symbol normalization:** a versioned mapping table reconciles source formats (`BRK.B` vs `BRK-B`), renames (`FB` to `META`), and recycled symbols across constituents CSV, Tiingo, EDGAR CIK, and FINRA. Every panel build emits a reconciliation report separating join failures from genuine delistings, so ticker mismatches cannot masquerade as survivorship loss.
- **Secrets:** API keys live in `.env` (git-ignored), loaded via python-dotenv; the EDGAR User-Agent email is configuration, not code. Key rotation is a documented one-file change.
- **Backups:** nightly `rclone` sync of `data/bronze/` to cloud storage (or a second disk at minimum), with a quarterly restore test. Only bronze needs this.
- **Reproducibility:** gold datasets are named by the sha256 of their canonical-JSON build config; `manifest.json` records config, git commit, input checksums, row counts, truncated-label counts, and build timestamp.
- **Collector health:** every run writes a run-log row; a health check alerts (and the dashboard shows) any collector with 2 consecutive missed days, because each missed day of a forward collector is permanent data loss.

New code lives in `pipeline/collect/` (collectors), `pipeline/features.py`, `pipeline/panel.py`, and `pipeline/models/`. Existing dashboard modules stay untouched until the dashboard phase.

---

## 5. Data pipelines

Ordered by build priority. "Forward-collect" means history cannot be reconstructed; those ship first, before any modeling, because their value is a function of how early they start.

### 5.1 Forward-snapshot collectors (week 1, non-blocking, unrecoverable)

| Collector | Source | Cadence | Notes |
|---|---|---|---|
| Option chains | yfinance `option_chain()`, nearest 4 expirations, full universe | Nightly ~16:45 ET | Strikes, bid/ask, volume, OI, Yahoo IV. Quality gate before trusting the archive: validate Yahoo's `impliedVolatility` against IV recomputed from bid/ask mids on a sample; archive both. Unlocks put/call ratios and the OTM-put-minus-ATM-call skew (Xing-Zhang-Zhao) prospectively |
| yfinance info snapshot | `.info` dict verbatim | Nightly | A year of daily snapshots turns the repo's weakest data (undated ratios, ownership, short % float, shares outstanding, analyst targets) into a real history with `capture_date = knowledge_time` |
| Analyst estimate snapshots | yfinance analyst endpoints + Alpha Vantage `EARNINGS_ESTIMATES` (within the shared 25/day budget) | Daily rotation | This is a self-built point-in-time consensus history, the free stand-in for IBES. Revision features unlock after ~3-6 months |
| News archive | Tiingo news (ticker-tagged, free key, only 3 months of queryable history, so every day of delay loses a day) + PR-wire RSS via feedparser | Every 2 hours | Raw articles only in this phase; scoring comes later. Dedup: canonical URL sha256 + SimHash near-dup pass for syndicated wire copy. `published_at` and `fetched_at` both stored |
| Congress trades archive | Existing `congress_trades.py` fetch logic, rewrapped to persist bronze | Daily | The upstream GitHub dataset may prune or vanish; our archive should not. Verify the disclosure-date field before any feature uses it |

### 5.2 Prices (the backbone)

- **Source of record:** Tiingo free tier (1,000 req/day, 500 unique symbols/month, 30+ years adjusted EOD, delisted coverage via permaTicker). yfinance stays as interactive fallback and cross-check, never as the scheduled bulk source (unofficial, recurring IP-level 429 blocks, personal-use terms).
- **Cadence:** nightly after Tiingo's EOD processing; one-time backfill spread over 2-3 nights of quota.
- **Silver schema:** `ticker, perma_ticker, date, open, high, low, close, adj_close, volume, split_factor, div_cash, source, fetched_at`. Raw and adjusted closes both stored.
- **Watch item:** the 500-unique-symbols/month cap is at the edge of a 503-name universe before churn, ETFs (SPY, sector SPDRs, RSP), and delisted backfills. Measure actual consumption in week 1; the first paid dollar is EODHD All World at $19.99/mo if the cap binds.
- **Cross-checks:** 20-ticker adjusted-close comparison against yfinance on every backfill; measure the fraction of historical members Tiingo actually serves (including delisted), per year, and publish it in the survivorship note.

### 5.3 EDGAR fundamentals and insider filings (point-in-time backbone)

- **Source:** nightly `companyfacts.zip` bulk download (~3:00 a.m. ET, replaces tens of thousands of API calls), `submissions.zip` for filing timestamps, `company_tickers.json` for the CIK map. Free, keyless, 10 req/s hard cap on ad-hoc calls with declared User-Agent.
- **Facts table:** long format, one row per fact per filing: `cik, ticker, taxonomy, tag, unit, period_start, period_end, value, form, accession, filed_date (= knowledge_time)`. Restatements coexist as separate rows; an as-of query returns what was most recently filed as of that date. Concept fallback chains (`Revenues` → `RevenueFromContractWithCustomerExcludingAssessedTax` → ...) live as versioned data in `reference/concept_map.yaml`, unit-tested against 20 hand-checked filings.
- **Shares outstanding:** `dei:EntityCommonStockSharesOutstanding` with filed dates gives point-in-time share counts. This one series unlocks market cap, turnover, B/M and E/P denominators, and value-weighted evaluation, and no free vendor provides it point-in-time. Until it lands, features needing shares outstanding are null, never approximated from today's snapshot.
- **Insider trades:** SEC quarterly Insider Transactions Data Sets (Forms 3/4/5 since 2006, pre-flattened TSVs) for history; submissions API for the live tail. `transaction_date = event_time`, `filed_date = knowledge_time`. Multi-year per-insider history enables the Cohen-Malloy-Pomorski routine/opportunistic split (routine trades carry no signal; opportunistic buys do).

### 5.4 Event and positioning sources (backfillable)

| Source | Access | Point-in-time rule |
|---|---|---|
| FINRA bi-monthly short interest | Free CSVs, archives to 2014 | `settlement_date = event_time`; `knowledge_time` = FINRA's published dissemination date for each cycle, ingested from their schedule, not a hardcoded settlement-plus-7 offset |
| FINRA Reg SHO daily short volume | Free daily files | A flow proxy, not a position; labeled with FINRA's own caveat (includes market-maker shorts) |
| Earnings surprises | Alpha Vantage `EARNINGS` (free, ~20 years of quarterly estimate/actual/surprise), 25 req/day rotation, each ticker refreshed only after its next report date | `reported_date = knowledge_time`. Before building 16 years of SUE/PEAD features on it, verify on a handful of known announcements that `estimatedEPS` is genuinely frozen as of the announcement rather than backfilled |
| Congress trades | Bronze archive from 5.1 | Features key on `disclosure_date`, never `transaction_date`; missing disclosure dates are imputed at transaction + 45 calendar days (the STOCK Act ceiling) and flagged |

### 5.5 Macro, regime, and factor reference data

- **FRED via fredapi** (installed, currently unused; free key, ~120 req/min, cached locally). Two classes, handled differently:
  - Never revised (safe as published): `DGS2, DGS10, T10Y2Y, T10Y3M, BAMLH0A0HYM2, VIXCLS`.
  - Revised (CPI, ICSA, UNRATE, PAYEMS, NFCI): fetched as ALFRED vintages (`get_series_all_releases` / `get_series_first_release`); features use first-release values aligned to release dates. Regression test: the CPI feature at an as-of date in 2015 equals the first release, not today's revision.
- **VIX term structure:** free CBOE CSVs (`VIX, VIX9D, VIX3M, VIX6M` history from cdn.cboe.com, verified live). Slope features VIX3M/VIX and VIX9D/VIX.
- **Sector rotation and breadth proxies:** 11 SPDR sector ETFs plus RSP/SPY from the price pipeline; no separate source needed.
- **Fama-French daily factor returns** (Ken French library, free): needed for market beta as a feature, idiosyncratic-vol residuals, event-study abnormal returns in PEAD windows, and for validating our own factor implementations. Chen-Zimmermann open-source portfolio returns as a second validation reference.
- Regime data conditions models (interaction features, regime-bucket reporting); it is not a target.

### 5.6 News and social scoring (after the archive has depth)

- **Scoring:** FinBERT (ProsusAI, laptop CPU) as the default scorer over the archived articles; VADER only as a prefilter; Claude Haiku batch scoring reserved for ambiguous multi-ticker headlines (~$0.04 per 1,000 headlines). Scores live in a separate `news_scores` table keyed by `model_name, model_version` with raw articles retained, so any future scorer re-runs over full history without refetching.
- **Ticker mapping:** SEC `company_tickers.json` + alias table + rapidfuzz fallback + cashtag regex, versioned by date.
- **Marketaux** (free, 100 req/day x 3 articles, per-entity sentiment) for a 50-name watchlist as a labeled cross-check; **Alpha Vantage NEWS_SENTIMENT** nightly within the shared budget as a second opinion.
- **Skipped deliberately:** NewsAPI.org (24-hour delay, dev-only license), StockTwits (registrations frozen), pytrends (archived upstream, blocked by Google). Reddit via PRAW free tier (non-commercial) is optional later breadth, not core.
- Evidence check: news/social sentiment carries modest signal at 1-day to 2-week horizons, concentrated around events. It earns its place through the M1-to-M2 delta (section 8), not by assumption.

---

## 6. Feature engineering

A feature registry (data, not code) declares for every feature: definition, inputs, `knowledge_time` rule, coverage-start date, and expected sign. Training runs cannot use a feature before its registered coverage start.

**Wave 1, price/volume (backfillable to 2010, powers the first model).** The Gu-Kelly-Xiu horse race found momentum, liquidity, and volatility variants dominate all other feature families, so this is the highest-evidence set, not just the easiest:

| Feature | Definition | Expected sign |
|---|---|---|
| `mom_12_1` | return over t-252 to t-21 | + |
| `ret_1m` | return over t-21 to t (short-term reversal) | - |
| `high_52w_prox` | close / rolling 252d max | + |
| `vol_21d`, `vol_252d` | annualized std of daily returns | - |
| `max_21d` | max daily return in prior month (lottery effect) | - |
| `amihud_252d` | log mean(abs(ret) / dollar volume), winsorized | + |
| `dollar_vol_21d` | log mean daily close x volume | - |
| `ma_ratio_10/50/200` | close / SMA (reuses `compute_indicators`) | mixed |
| `rsi_14`, `macd_hist_norm`, `bb_pctb`, `bb_bandwidth` | continuous indicator states, scale-free | mixed |
| `info_discreteness` | frog-in-the-pan path smoothness over the momentum window | interacts with momentum |
| `seas_month` | mean same-calendar-month return over available history (min 5 years) | + |

Continuous states only; no binary crossing events (golden cross et al. lose information and inflate variance). Excluded until their point-in-time inputs exist: turnover (needs PIT shares outstanding), `cumulative_return` (window-relative artifact).

**Wave 2, backfillable alternative (as each source lands):** B/M, E/P, gross profitability, asset growth, accruals (EDGAR, exposed at `filed_date`); SUE and days-since-announcement (PEAD window); days-to-cover and its change (FINRA, publication-aligned); opportunistic insider net buying trailing 90d; congress net purchases trailing 60d (disclosure-aligned); market beta and idiosyncratic vol (factor returns).

**Wave 3, forward-collected (unlock as archives mature, reported separately):** put/call OI ratio, IV skew, estimate-revision counts, news sentiment means and article-volume spikes, analyst-target dispersion from info snapshots.

**Regime columns (not per-ticker):** VIX 252d rolling-quantile bucket, VIX3M/VIX slope, SPY vs 200DMA, HY OAS threshold, defensive-vs-cyclical sector leadership, RSP/SPY.

**Assembly:** one DuckDB build produces the `(date, ticker)` panel via ASOF joins on `knowledge_time`, writes to `gold/features-{hash}/`, and runs the tripwires (section 8).

---

## 7. Models

- **Framing:** one pooled cross-sectional panel; the model scores all universe members per rebalance date and the score is consumed as a rank. No per-ticker time-series models.
- **Exactly two model classes in iteration 1:** ridge/elastic-net (mandatory linear baseline) and LightGBM (depth 4-6, feature/row subsampling, L1/L2, early stopping on a temporally later block). A simple average of the two as the only ensemble. No neural nets until the harness has proven itself end to end; tabular evidence (Grinsztajn 2022, qlib benchmarks) says the marginal gain is small.
- **Staged versions tied to data waves:** M0 = wave-1 features only (trainable immediately on the price backfill). M1 = + wave-2 backfillable alternative data. M2 = + wave-3 forward-collected features, trained on the shorter accumulated window and reported separately with sample-length caveats. The M0→M1→M2 deltas, per source, are the headline analysis: what does each information source add?

---

## 8. Validation protocol

Fixed before the first run, versioned with the code.

- **Walk-forward:** expanding window. Train 2010 through year T, tune on year T+1 (hyperparameters and early stopping only), test on year T+2, roll annually.
- **Purging and embargo:** drop training rows whose 21-day label window overlaps validation/test; embargo 21 additional trading days after each test block.
- **Locked holdout:** the most recent 12 months, evaluated exactly once by the single pre-registered final config after all iteration is done.
- **Experiment log:** every run appends config hash, feature set, model, dates, metrics, git commit to `experiments.csv`. The trial count feeds a Harvey-Liu-Zhu significance bar: mean-IC t-stat above 3.0 before any signal is called real.
- **Leakage tripwires, automated on every gold build and harness run:**
  1. Mean rank IC above 0.10 fails the build as a leakage alarm, not a success.
  2. A model trained on the label lagged backward one day must score near-zero IC.
  3. Full-table DuckDB scan asserting no feature value has `knowledge_time > as_of_date`.
  4. Knowledge-time shuffle canary: shifting `knowledge_time` forward one day must change joined values (proves the join keys on it).
  5. A deliberate-leak fixture that the purged-CV harness must catch, as a unit test of the harness itself.

---

## 9. Evaluation

| Metric | Definition | Honest target |
|---|---|---|
| Rank IC | per-date Spearman(score, forward excess return), mean and t-stat across dates | stable 0.02-0.05 (qlib's LightGBM/Alpha158 anchor: 0.048) |
| ICIR | mean(IC) / std(IC) | > 0.3 |
| Decile spread | top minus bottom decile forward return | positive, monotonic through the deciles |
| Long-short Sharpe | annualized, gross and net of 10-25 bps per side | net > 0.5 counts as a success |
| Turnover | mean monthly one-way | < 50% |
| Stability | IC by calendar year and by regime bucket | positive in most years; a one-regime signal is labeled as such |

Tooling: a maintained alphalens fork (verify pandas 3.0 compatibility first; see section 11) plus ~100 lines of pandas. Factor implementations are validated against Ken French portfolio sorts and Chen-Zimmermann portfolio returns before any self-built backtest is trusted. Expect roughly a 50% haircut versus published anomaly spreads (McLean-Pontiff); most experiments will show IC indistinguishable from zero, and that outcome ships.

**Model lifecycle after the backtest:** monthly refit and score on the walk-forward schedule; trained models serialized and versioned by config hash; realized forward IC of live scores tracked monthly against the backtest band on the dashboard, which is the only way to see decay or train/serve skew. A live IC persistently outside the band triggers review, not silent retraining.

---

## 10. Dashboard surfacing

A new "Signal Research" page, reading gold only:

- Current rebalance date's cross-sectional ranks, labeled "historical model score, informational only", with the education disclaimer and the survivorship note (including the measured missing-member fraction).
- IC time series, decile spread chart, per-year and per-regime stability tables, M0/M1/M2 per-source delta view.
- Live-vs-backtest IC tracking.
- Collector health panel: last run, row counts, and gap detection per source, so a silently failing cron is visible the day it happens.
- Per-source attribution lines (Tiingo, SEC EDGAR, FINRA, FRED/ALFRED, ICE BofA via FRED display-only, CBOE, Alpha Vantage, congress-trades upstream).

---

## 11. Verify-before-building checklist

Free-tier terms moved repeatedly through 2024-2026. Each item gets checked at implementation time, not assumed from this document:

1. Tiingo free tier: actual unique-symbol consumption for our universe plus ETFs and churn; whether price history is actually served for delisted permaTickers; News API enabled on a free key.
2. Alpha Vantage `EARNINGS.estimatedEPS` frozen-at-announcement behavior, spot-checked against known announcements.
3. FINRA's published dissemination schedule per cycle (join to it, never to a hardcoded offset).
4. kadoa-org congress feed: disclosure-date field presence, schema stability, upstream retention.
5. `fja05680/sp500` CSV: membership-count sanity per date, spot-check known index changes.
6. alphalens fork compatibility with the pinned pandas 3.0.x; fall back to hand-rolled IC/decile code if broken.
7. yfinance `option_chain` viability at 500-ticker nightly scale, and Yahoo IV quality versus mid-recomputed IV.
8. Measured fraction of 2010-era ex-members recoverable from Tiingo/yfinance before committing to the backtest start date.
9. All quoted rate limits (AV 25/day, Marketaux 100/day, Tiingo 1,000/day, EDGAR 10/s, FRED 120/min) re-read from provider docs.

---

## 12. Phased milestones

Solo developer, part-time. Every phase is its own branch and PR, updates `docs/research-pipelines.md` in the same commits, and ships tests for its calculations and edge cases (holidays, splits, missing data).

| Phase | Deliverable | Effort |
|---|---|---|
| **0. Skeleton** | `data/` layout, state DB, watermark + atomic-swap helpers, typer CLI, pandera base, exchange calendar dependency, `.env` secrets, symbol map v1, vendored constituents CSV + verification pass | 2 days |
| **1. Forward collectors + prices** | The five 5.1 collectors live with health alerting and bronze backup sync; Tiingo nightly prices + backfill; cross-checks and coverage measurement; quota ledger | 4-5 days |
| **2. Panel** | `features.py` wave 1, label builder with delisting policy, registry, gold builder with ASOF joins, all five tripwires, full feature test suite | 4-5 days |
| **3. M0 + harness** | Ridge + LightGBM, purged walk-forward runner, experiments log, evaluation tear sheets; locked holdout touched once at the end | 4-5 days |
| **4. Dashboard + docs** | Signal Research page, collector health panel, disclaimers/attribution, vocabulary lint | 2-3 days |
| **5. Source backlog → M1** | In evidence-per-effort order, each its own PR: FRED/ALFRED + VIX structure + factor returns; FINRA short interest; EDGAR facts + PIT shares outstanding; AV earnings surprises (after the frozen-estimate check); insider filings; congress features (after feed verification) | ordered backlog, ~2-14 days each |
| **6. Scoring + M2** | FinBERT scoring over the news archive; wave-3 features as archives cross ~6 months; M2 reported separately; live IC monitoring | ongoing |

First trained, honestly evaluated, dashboard-surfaced model: roughly 4-5 weeks part-time, with every unrecoverable archive accumulating from week 1.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| yfinance blocks break snapshot collectors | Throttle + backoff + watermark resume; watchlist-first fetch order so partial runs keep the highest-value slice; prices never depend on yfinance |
| Tiingo symbol cap binds | Measured in week 1; EODHD $19.99/mo is the planned first paid dollar |
| Forward collectors miss days (sleeping laptop, host down) | Always-on host requirement, catch-up on wake, 2-missed-days alert, health panel; accepted residual: missed snapshot days are logged as permanent gaps |
| Adjusted-close drift corrupts old partitions | Corporate-action detection triggers per-ticker full-history rebuild; raw close stored alongside adjusted |
| Ticker mismatch inflates apparent survivorship loss | Symbol map + per-build reconciliation report separating join failures from delistings |
| EDGAR tag inconsistency yields wrong fundamentals | Versioned concept map with fallback chains; per-company coverage report; below-threshold issuers get nulls + missing flags, never guesses |
| Silent leakage | Five automated tripwires on every build, not one-time discipline |
| Backtest overfitting by iteration | Experiments log, t > 3.0 bar, one-shot locked holdout |
| Yahoo IV archive worthless | Quality gate in week 1 before the archive is trusted; bid/ask mids archived so IV can be recomputed |
| Free-tier regime change mid-project | Quotas live in config, run-log gap detection makes tightening loud, per-source degraded mode documented in the collector's doc section |
| Licensing (internal-use-only tiers, ICE BofA redistribution) | No raw-data export features; derived indicators with attribution only; Reddit stays research-scoped |
| Advice-language drift | Vocabulary lint in tests; all output framed as historical analysis with accuracy metrics |

---

## 14. Source attributions

Yahoo Finance via yfinance (unofficial, personal use), Tiingo, SEC EDGAR, FINRA, FRED/ALFRED (ICE BofA series display-only), CBOE, Alpha Vantage, Marketaux, Ken French Data Library, Chen-Zimmermann Open Source Asset Pricing, kadoa-org congress-trading-monitor, fja05680/sp500 constituents. Each pipeline's doc section carries its exact terms.
