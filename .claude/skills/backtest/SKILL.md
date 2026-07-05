---
name: backtest
description: Evaluate any signal, feature, or model score honestly with pipeline/backtest. Use whenever measuring whether something carries signal, before believing or surfacing any result.
---

# Backtest

Run signal evaluation through `pipeline/backtest`. The protocol below is binding; it comes from `docs/plans/2026-07-05-signal-model-data-pipelines.md` sections 8-9.

## Protocol

1. **Build the panel:** one row per (date, ticker) with score column(s), a realized forward label (excess return), and `label_end_date` (when the label window closes). If the panel carries a knowledge-time column, run `check_knowledge_time(panel, col)` before anything else.
2. **Split:** `walk_forward_splits(panel, min_train_periods=..., val_periods=12, test_periods=12)`. Fit on `train_idx`, tune on `val_idx` only, score `test_idx` only. Purging and NaT-label exclusion are built in; the embargo defaults to 30 calendar days (approximately the protocol's 21 trading days until the exchange calendar lands). Do not pass a smaller embargo without a written reason.
3. **Evaluate test folds only:** `rank_ic` then `summarize_ic(ic, nw_lag=overlap_lag(panel))`; the nw_lag argument is mandatory whenever scoring dates are finer than the label horizon, because overlapping label windows inflate the plain t-stat. Then `quantile_returns`, `long_short_spread`, `monotonicity`, `hit_rate`; `top_quantile_turnover` then `net_spread` at 10-25 bps per side. Report gross and net; the first rebalance has NaN net spread by design (no turnover observation), never treat it as free.
4. **Tripwires, every run:** `check_ic_alarm(mean_ic)` (mean rank IC above 0.10 is leakage until proven otherwise) and the shuffle null: `shuffled_labels` into `rank_ic`, passing the resulting IC series to `check_shuffle_null` (it is t-based and scales with panel size).
5. **Log every trial** with `log_experiment(path, config, metrics)` before interpreting results. Claim a real signal only when `clears_significance_bar(t_stat)` holds (t above 3.0) given the logged trial count.
6. **Honest reporting:** per-year stability alongside pooled numbers; expect mean rank IC 0.02-0.05 for a good signal; a null result ships as "no reliable signal found at this horizon". A locked holdout is evaluated exactly once.

## Vocabulary

Model output is a "score", "rank", or "signal" in code, UI, and docs. Never "prediction" or "forecast".
