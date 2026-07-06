# Vendor Verification: Plan Section 11 Checklist Results

> **Date:** 2026-07-06. **Status:** verification results for `docs/plans/2026-07-05-signal-model-data-pipelines.md` section 11. Two passes: provider-doc reading (current 2026 terms) and hands-on measurement (live scripts against yfinance, GitHub datasets). Items needing a live API key are marked and stay open until Phase 0 sets up secrets.

## Summary table

| # | Checklist item | Verdict |
|---|---|---|
| 1 | Tiingo free tier | CONFIRMED terms; delisted-history and News activation need a key |
| 2 | Alpha Vantage estimatedEPS frozen at announcement | UNVERIFIED; treat as NOT point-in-time until spot-checked with a key |
| 3 | FINRA dissemination schedule | CONFIRMED; pending rule change to weekly cadence |
| 4 | kadoa congress feed | PASS with one new gotcha (flat file capped at 5,000 trades) |
| 5 | fja05680/sp500 CSV | PASS; pre-2004 undercount quirk |
| 6 | alphalens fork vs pandas 3.0.x | NOT YET TESTED (check at Phase 3) |
| 7 | yfinance option_chain at scale | PASS on speed; quote fields need a market-hours re-test |
| 8 | 2010-era ex-member recoverability | NEEDS TIINGO KEY (Phase 0) |
| 9 | Rate limits re-read | ALL CONFIRMED, one correction (Tiingo also 50/hour) |

## 1. Tiingo free tier

Pricing page (read 2026-07-06): 50 requests/hour, 1,000 requests/day, 500 unique symbols/month, 1 GB bandwidth/month. Resets hourly, daily midnight EST, monthly on the 1st. The 50/hour cap was not in the plan; nightly collection must spread calls or budget ~10 hours for 500 symbols if each needs multiple requests. News API is listed as included on the free tier (3 months queryable history plus data going forward), but historically required emailed activation; confirm on key receipt. Delisted-ticker history: docs are silent by tier; community reports say Tiingo does serve it. Both open items resolve with a key at Phase 0.

## 2. Alpha Vantage

Free tier confirmed at 25 requests/day (support page). The EARNINGS endpoint docs say nothing about whether estimatedEPS is frozen at announcement time; third-party commentary flags Alpha Vantage fundamentals generally as weak on point-in-time discipline. Standing decision until the spot-check passes: do not treat estimatedEPS as an announcement-time consensus; any surprise feature built on it carries a lookahead flag in the feature registry.

## 3. FINRA short interest

Official cycle schedule (settlement, due, publication dates) is published on the FINRA short-interest page; current cadence is twice monthly, disseminated about 7 business days after settlement. Join collectors to the published table, never a hardcoded offset (plan rule confirmed as necessary). New: a May 2026 SEC rule filing proposes weekly reporting with 1-business-day dissemination. Not yet effective. Build the ingester schedule-driven so a cadence change is a data update, not a code change.

## 4. kadoa-org congress feed

Hands-on inspection (2026-07-06): actively refreshed (daily bot commits, latest 2026-07-05), 64,314 trades spanning 2011 to present across house, senate, and executive-branch sources. Every sampled record has both `transaction_date` and `filing_date`, plus `days_to_file` and `is_late`. Median disclosure lag is 31 days, p90 is 172 days: any point-in-time feature must join on `filing_date`, not `transaction_date`. **New gotcha:** the flat `trades.json` is capped at the most recent 5,000 records; full history requires the per-filer and per-ticker files. `pipeline/congress_trades.py` is unaffected (it already fetches the per-ticker and per-filer files), but the planned archive collector must walk the per-filer files rather than the flat file.

## 5. fja05680/sp500 constituents CSV

Hands-on check: current file is `S&P 500 Historical Components & Changes (Updated).csv`, 2,712 event-dated rows, 1996-01-02 through 2026-06-02, maintained (last data commit 2026-06-09). Membership counts are 495-507 for all rows after 2004-04-01; rows before that run 487-494 (known completeness quirk, all undercounts). Spot checks pass: TSLA appears at the 2020-12-21 row, SMCI at 2024-03-18. Point-in-time lookup is last-row-at-or-before-date. Verdict: fine to vendor for the plan's universe construction, with the pre-2004 undercount noted and the repo's own errata history arguing for a pinned commit hash rather than always-latest.

## 6. alphalens / pandas compatibility

Not yet tested; belongs with Phase 3 setup when the model environment is pinned. The fallback (hand-rolled IC/decile code) already exists in `pipeline/backtest/evaluation.py`, so this item is low risk.

## 7. yfinance option_chain at nightly scale

Hands-on measurement (10 liquid tickers, 2 nearest expirations, yfinance 1.5.1): zero failures, 0.84s per ticker average, so 500 tickers extrapolates to roughly 7 minutes single-threaded. Scale is a non-issue. Quality: 58% of contracts had plausible implied volatility (0.01-5.0); most implausible values are Yahoo's sentinel near-zero IV on no-bid deep OTM strikes and filter out with a bid-greater-than-zero, near-the-money screen. Caveat: the test ran on a Sunday after a holiday, so bid/ask were zeroed and last-trade dates stale by construction. Required follow-up before Phase 1 ships: re-run during market hours, and schedule the collector on trading days shortly after the close.

## 8. Ex-member price recoverability

Requires a Tiingo key to measure. Blocked until Phase 0 secrets exist. The tail-risk survey (PR #11) independently concluded delisting-aware prices are mandatory for any tail backtest, which raises the cost of skipping this measurement.

## 9. Rate limits, re-read from provider docs

- Tiingo: 1,000/day CONFIRMED, plus the 50/hour cap noted above (correction to the plan).
- Alpha Vantage: 25/day CONFIRMED.
- Marketaux: 100/day CONFIRMED (resets midnight UTC); free tier also caps at 3 articles per request, which the news collector's pagination must account for.
- FRED: 120/min CONFIRMED via the fredr client's documented correspondence with the FRED team (not stated in official docs; API returns 429 beyond it). ALFRED vintages work on the same free key via realtime parameters.
- SEC EDGAR: 10 requests/second CONFIRMED from sec.gov developer resources, unchanged since 2021; declared User-Agent with contact email remains mandatory.

## Consequences for the plan

1. **Phase 1 collector budget:** Tiingo's 50/hour cap and the 500 unique-symbol monthly cap are the binding constraints, not the daily cap. The quota ledger should track symbols per month, not just requests per day.
2. **Congress archive:** walk per-filer files, not the capped flat file; join on filing_date.
3. **Option snapshots:** proceed; add a market-hours quality re-test to the Phase 1 checklist and filter contracts to bid-positive near-the-money strikes before computing skew.
4. **Earnings surprises (Phase 5):** stays gated behind the frozen-estimate spot check; assume not point-in-time until proven otherwise.
5. **FINRA:** schedule-driven ingestion, ready for the possible move to weekly cadence.

Open items 1 (key-gated Tiingo checks), 6 (alphalens), and 8 (ex-member coverage) move to their owning phases.
