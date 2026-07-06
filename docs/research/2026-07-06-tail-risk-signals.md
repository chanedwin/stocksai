# Tail-Risk Signals: a Verified Survey

> **Date:** 2026-07-06. **Status:** research input to the signal-model plan, not a commitment to build.
> **Framing:** candidates for analysis and signals in a research/education app. Nothing here is investment advice, and no area is claimed as a tradable edge. Companion to `2026-07-05-neglected-signal-areas.md`, which covered neglected alpha areas; this survey covers predictors of extreme moves, left tail (crashes, drawdowns) and right tail (jackpots, squeezes).

## Method and headline

Three research passes gathered 36 candidates across (a) options-derived tail signals, (b) market-level stress and fragility precursors, and (c) single-stock crash and jackpot predictors from the academic literature. The 14 strongest were then put through one adversarial pass instructed to refute each with 2024-2026 evidence: vendors selling it, free dashboards publishing it, published decay, or free-data infeasibility.

Headline findings:

1. **Almost no tail signal is a leading indicator.** The honest evidence for nearly everything (turbulence, correlation spikes, VIX inversion, funding stress) is regime identification and amplification, not advance warning. The CBOE SKEW index, the one product marketed as a crash predictor, demonstrably fails at it.
2. **Market-level stress series are free and official.** OFR FSI, NFCI, STLFSI4, HY OAS, the excess bond premium, and CBOE's whole index family are published daily or weekly at zero cost. Nothing built on top of them is differentiation; it is convenience and education.
3. **The only real data moat is forward collection.** Per-stock option skew history does not exist for free, and yfinance chains are snapshot-only. Nightly chain snapshots (already plan Phase 1) are the one asset here that compounds and cannot be bought cheaply later.
4. **Free-data backtests of tail events are structurally biased.** Crashes, delistings, and jackpots concentrate in exactly the names that vanish from survivor-only data (yfinance). Estimating tail models on such a panel censors the outcome variable itself. Forward measurement or delisting-aware prices (Tiingo permaTicker, per the plan) are the only honest routes.

## Standing warnings

- **Regime vs forecast.** Per CLAUDE.md vocabulary rules, everything below ships as "historical stress indicator" or "tail-state descriptor" with hit and false-alarm rates shown. High readings mean fat tails are priced or present, not that a crash is coming.
- **Post-publication decay applies.** McLean-Pontiff decay (~26% out-of-sample, ~58% post-publication) hits every single-stock anomaly below; several originals are pre-2010 samples.
- **Threshold instability.** Structural shifts (index composition, 0DTE options, ETF growth, LIBOR's death) break fixed thresholds on long-history series. Use rolling percentiles and standardized shifts, not published cutoff levels.

---

## Tier 1: survived adversarial review

### 1. Nightly option-chain snapshot collection, per-stock tail-state history (the data moat)

The strongest candidate, and it is a data asset, not a signal. yfinance option chains are current-snapshot only (no historical endpoint exists; community consensus is "start your own collection"). Collecting nightly snapshots for liquid optionable names unlocks, over time: implied volatility smirk (Xing-Zhang-Zhao, JFQA 2010: steepest-smirk decile underperformed ~10.9%/yr risk-adjusted, 1996-2005), option-to-stock volume ratio (Johnson-So, JFE 2012), call-put IV spread (Cremers-Weinbaum, JFQA 2010), risk-neutral skewness, and pre-earnings skew and implied move.

**Skeptic conditions:** the underlying alphas are pre-2010 samples in the decay regime, and vendors (ORATS, OptionMetrics, Market Chameleon) sell clean histories of all of them. What survives is the free path to a per-stock skew history used for tail-state description ("skew is at its 95th percentile vs own collected history"), not alpha. Restrict to liquid names with tight-spread filtering (Yahoo IV is stale-quote noisy), disclose that history starts on collection day, and expect permanent holes from outages. Already scheduled as plan Phase 1; this survey raises its priority: every uncollected day is lost.

### 2. SKEW-with-its-failure, and honest tail-gauge education

The CBOE SKEW index survives precisely because the product is the explanation. Bevilacqua-Tunaru (Journal of Financial Stability 2021) show headline SKEW has no significant relation to realized skewness and weak crash prediction; only their decomposed negative-side component carries signal (predicting downturns up to a year ahead). Practitioner evidence agrees: none of the worst drawdowns since 1990 were preceded by top-5% SKEW readings. Data is free (Cboe CSV, ^SKEW).

**Skeptic conditions:** frame as "headline SKEW is a poor crash timer; here is the component that carries what signal exists," not "SKEW is useless." This generalizes into the app's honest niche: showing popular tail gauges next to their measured hit and false-alarm rates.

### 3. Lottery-shape descriptor (MAX effect family)

MAX (largest daily return in the past month; Bali-Cakici-Whitelaw, JFE 2011, low-minus-high spread >1%/month) is one of the few anomalies showing little post-publication decay in replications, and is trivially computable from prices. As a descriptor ("this stock currently has a lottery-shaped return distribution, historically associated with poor average returns and fat tails") it fits the education mandate.

**Skeptic conditions:** the mechanism is disputed (Critical Finance Review 2022 argues overreaction, not lottery preference; state the alternative), and single proxies are fragile (Jiang, Financial Management 2025). Ship an aggregate lottery score (MAX + idiosyncratic vol + skew proxy), not one number.

---

## Tier 2: survives only as educational reimplementation or composite input

These are real, evidenced, and free to compute, but free official incumbents or dashboards already publish them. Build them only as context layers benchmarked against the incumbent, never as headline differentiation.

| Candidate | Evidence | Skeptic's refutation | Surviving shape |
|---|---|---|---|
| Financial turbulence index (Kritzman-Li, FAJ 2010; Mahalanobis distance on asset-class returns) | Turbulence regimes persist; risk-asset Sharpe much lower in top-decile turbulence; beat absorption ratio out-of-sample in a 2022 comparison | State Street sells it; multiple free replications and an API exist; OFR FSI/NFCI cover the use case | In-app regime overlay labeled as a reimplementation of a known index, shown against OFR FSI |
| Absorption ratio (Kritzman et al., JPM 2011; rolling PCA variance share) | All worst 1% drawdowns 1998-2010 preceded by a >1 sigma AR shift in the original paper | Free TradingView indicator exists; documented false positives; sensitive to universe/window; fragility gauge, not timer | Standardized shift only, on the paper's standard universe, with false-positive caveat |
| Variance risk premium (VIX squared minus realized variance; Bollerslev-Tauchen-Zhou, RFS 2009) | Strongest academic pedigree of the set; quarterly-horizon return predictability | Hao Zhou publishes the canonical series free; 2024 AFA work finds no predictability across most assets; daily-close RV weakens the measure | Risk-appetite/stress gauge cross-checked against Zhou's series, with the caveat stated |
| VIX/VIX3M term-structure ratio | Inversion accompanied every major dislocation since 2008; few false positives as a stress confirmer | Cboe and vixcentral publish the curve free in real time; inverts as the selloff starts, not before | One line of code inside a composite regime panel |
| Aggregate Amihud illiquidity | Unexpected illiquidity shocks crush prices (Amihud 2002); depth collapse amplified Feb 2018 and Mar 2020 | Premium attenuated post-decimalization; a yfinance-backfilled aggregate is survivorship-biased in exactly the stressed periods | Forward-computed, fixed liquid universe, down-move-day variant, framed as amplifier context. Extends the existing illiquidity-decomposition item in the neglected-areas survey |
| Macro stress context panel (HY OAS, NFCI/OFR FSI, excess bond premium, yield curve, margin debt) | EBP and NFCI have the best-evidenced left-tail links (Gilchrist-Zakrajsek AER 2012; Adrian et al. AER 2019 growth-at-risk) | All free official products, charted everywhere; yield curve gave a live counterexample in 2022-24; margin debt largely lags returns | One dashboard panel of FRED series (`BAMLH0A0HYM2`, `NFCI`, `T10Y3M`, EBP CSV) with real-time-vintage (ALFRED) discipline in any model use |
| Naive distance-to-default (Bharath-Shumway, RFS 2008) | Naive form forecasts default about as well as solved Merton; inputs are free (prices + XBRL + FRED) | NUS-CRI gives away daily PDs/DTDs for 80,000+ firms; XBRL debt tags are inconsistent | Transparent formula-shown educational field, benchmarked against CRI |
| Two-sided "bubble singles" flag (high valuation x high short interest x low institutional ownership; Boehme et al., JFQA 2006) | Underperformance severe only when constraint and disagreement are both present; the 2021 meme episode showed the squeeze-up tail of the same cohort | Squeeze half fully commoditized (Fintel, Finviz); inputs are snapshot-only free, so no free backtest | Forward-only descriptive flag: "this configuration historically has fat tails in both directions." The genuinely unserved piece is the two-sidedness |
| Breadth fragility (percent above 200dma, new highs/lows) | Hindenburg-omen-family hit rate ~25% for >5% declines, ~75% false alarms | Barchart $MMTH and StockCharts publish it all free; backfilled fixed-universe series still survivorship-biased | Internal composite input only, never a headline series |

## Tier 3: refuted

| Candidate | Why refuted |
|---|---|
| Jackpot-probability logit re-estimated on free data (Conrad-Kapadia-Xing, JFE 2014) | Structurally infeasible: jackpots and deaths concentrate in delisted-prone microcaps that vanish from yfinance, censoring the label itself. Only salvage: apply the published 2014 coefficients as a descriptive flag, clearly labeled |
| Standalone EDGAR dilution/going-concern product | Mature retail vendor space: DilutionTracker, DilutionWatch (free tier), Dilutracker, StockTeller, edgar.tools, all live 2025-26. Salvage is UX integration only: going-concern language and shelf/ATM capacity shown inline on a stock's page, which folds into the EDGAR red-flag suite already in the neglected-areas survey |
| IPO/SPAC lockup-expiry calendar from prospectus parsing | Free calendars abound (MarketBeat, Briefing.com, IPOScoop); effect is small (~1-3%) and front-run; SPAC early-release triggers make naive parsing error-prone. Link out instead |
| Put/call ratios as informed-flow signal | The strong result (Pan-Poteshman, RFS 2006) needed proprietary signed open-buy volume; public-volume versions are weak, and 0DTE flow distorted the market-level ratio post-2021 |
| Deep-OTM jump-tail measures at academic fidelity (Bollerslev-Todorov) | Needs dense strike data (OptionMetrics/CME); deep-OTM quotes are least reliable exactly when the signal matters. Crude free versions collapse into SKEW, already covered |
| Single-signal crash-risk regressions (NCSKEW/DUVOL determinants, accounting opacity, dispersion) | Opacity effect weakened materially post-SOX (Hutton et al. 2009's own finding); dispersion needs point-in-time IBES history that has no free source; NCSKEW determinants predict skewness, not returns. Keep NCSKEW/DUVOL as computed diagnostics, not signals |

---

## How this feeds the plan

1. **Raises the urgency of plan Phase 1 collectors.** Option-chain snapshots (Tier 1, #1) plus two cheap additions to the nightly run: FINRA bi-monthly short interest archiving and the FRED/ALFRED stress series pulls. Forward-collected history is the only asset here that compounds.
2. **Suggests one new dashboard surface, not many signals:** a "Tail Risk" panel combining the macro stress context (Tier 2 FRED series), one computed regime series (turbulence, labeled as a reimplementation), and per-stock descriptors (lottery score, skew percentile once collected, naive DTD, two-sided crowding flag), each displayed with hit and false-alarm rates.
3. **Gate unchanged:** anything promoted from descriptor to signal goes through `pipeline/backtest/` with its tripwires, cost assumptions stated, and the experiment logged. Tail-event backtests additionally require delisting-aware prices (Tiingo permaTicker); yfinance-only tail backtests are prohibited by the survivorship findings above.
4. **Framing discipline:** all of it ships as analysis with measured uncertainty. The honest pitch is "here is what this stress gauge has and has not called historically," which no free incumbent bothers to show.

## Sources

Key references (full URL lists live in the research transcripts): Xing-Zhang-Zhao (JFQA 2010); Johnson-So (JFE 2012); Cremers-Weinbaum (JFQA 2010); Bevilacqua-Tunaru (J. Financial Stability 2021); Bollerslev-Tauchen-Zhou (RFS 2009) and Hao Zhou's public VRP series; Kritzman-Li (FAJ 2010); Kritzman-Li-Page-Rigobon (JPM 2011); Adrian-Boyarchenko-Giannone (AER 2019); Gilchrist-Zakrajsek (AER 2012); Amihud (JFM 2002) and Amihud-Noh (2020); Bali-Cakici-Whitelaw (JFE 2011); Conrad-Kapadia-Xing (JFE 2014); Bharath-Shumway (RFS 2008); Campbell-Hilscher-Szilagyi (JF 2008); Hutton-Marcus-Tehranian (JFE 2009); Boehme-Danielsen-Sorescu (JFQA 2006); Pan-Poteshman (RFS 2006); Field-Hanka (JF 2001); McLean-Pontiff (JF 2016); Chen-Zimmermann Open Source Asset Pricing (openassetpricing.com). Data: FRED (`BAMLH0A0HYM2`, `NFCI`, `STLFSI4`, `T10Y3M`, `VIXCLS`, `VXVCLS`), OFR FSI, Fed Board EBP CSV, Cboe index CSVs (SKEW, VVIX, PPUT, VXTH), FINRA short interest and margin statistics, EDGAR full-text search and XBRL, Ken French data library, NUS-CRI.
