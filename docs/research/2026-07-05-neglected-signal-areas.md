# Where the Crowd Is Not Looking: a Verified Survey

> **Date:** 2026-07-05. **Status:** research input to the signal-model plan, not a commitment to build.
> **Framing:** everything here is candidate material for analysis and signals in a research/education app. Nothing is investment advice, and no area below is claimed as a tradable edge.

## Method and headline

Six research passes generated 42 candidate "neglected areas" across capacity limits, messy public data, market structure, crowding complements, universe expansion, and behavioral/calendar effects. Each candidate then faced one adversarial skeptic instructed to refute it with current (2026) evidence: vendors selling the data, funds known to trade it, published decay, or free-data infeasibility.

**40 of 42 were refuted as pitched.** That is the headline finding: almost everything that looks neglected from the outside is already commoditized by alt-data vendors, ETFs, or free retail dashboards. The two clean survivors, and the ~20 narrower variants the skeptics salvaged, share a structure worth internalizing before chasing anything new.

## The four durable neglect mechanisms

1. **Capacity.** Edges sized below institutional minimums (sub-$500M stocks, sub-$200M closed-end funds, a few hundred events per year) survive publication because funds cannot deploy in them. They pay only at personal scale and only net of 2-3% round-trip costs, which eat most published gross numbers.
2. **Mandate and career risk.** Nobody at a pod gets paid to go long recently sued companies, index deletions removed for cause, or zero-coverage names. The discomfort is the moat.
3. **Horizon.** Pod platforms penalize positions held past roughly 30 days, vacating multi-month horizons. Caveat: the classic anomalies at those horizons (drift, reversal) are published and mostly cost-eaten; the vacancy is real but not free money.
4. **Grunt work without a vendor.** Messy free data is only a moat where no vendor has productized it. The graveyard below shows vendors almost always got there first; verify before assuming.

## Standing warnings (apply to everything below)

- **Free-data survivorship bias is worst exactly where the edges live.** Delisted microcaps vanish from yfinance, and they are the losing tail of every microcap strategy. A yfinance-only microcap backtest overstates returns by construction. This strengthens the plan's Tiingo permaTicker decision, and for the microcap tail it argues for forward measurement over backfilled backtests.
- **Short legs are uncapturable.** Most published anomaly profit sits in hard-to-borrow short legs (Muravyev et al., JF 2025). Every surviving variant here is long-only, an avoidance flag, or descriptive analysis.
- **Expect 50%+ post-publication decay** (McLean-Pontiff). Single-paper areas need self-replication through the backtest harness before any trust.

---

## Tier 1: survived adversarial review

### 1. Patent-litigation defendants, long tilt (neglect 7/10, feasibility 7/10)

Firms sued for patent infringement get oversold at filing; alleged infringers earned +0.48% to +0.61% per month over the following year versus matched firms (Bereskin et al., Journal of Banking and Finance 2022, sample 2000-2014). Most suits settle cheaply or die. Institutions avoid it for mandate reasons; legal-data vendors serve lawyers, not quant pipelines; the skeptic found no fund trading a diversified long-defendants factor and no replications.

**Skeptic conditions:** the sample predates Alice (2014) and TC Heartland (2017), so expect roughly half the published effect and treat it as unvalidated until a self-run 2015-2025 replication on CourtListener/RECAP data passes the harness. Strongest variant: long small/mid-cap operating-company defendants only (exclude mega-caps sued constantly), monthly rebalance, one-year hold, long tilt versus matched peers rather than long-short. Data: CourtListener REST API (free, nature-of-suit 830), PACER under the $30/quarter fee waiver. The real work is entity resolution from case captions to tickers.

### 2. Microcap coverage gap: post-filing drift on fundamental inflections (neglect 5/10, feasibility 7/10)

Listed $50M-$500M names with zero or one analyst price filings slowly. The skeptic killed the "nobody is watching" framing (retail tools poll EDGAR within minutes) but confirmed the capital-side neglect: transaction costs eat 63-100% of gross drift profits at fund scale, so the information is watched while the capital stays away.

**Skeptic conditions:** drop the speed race on 8-K/Form 4 alerts (commoditized). The survivable variant is multi-week drift on fundamental inflections from 10-Q XBRL in zero-coverage names, with a hard liquidity floor (~$100k+ average daily dollar volume), returns reported net of a 2-3% round-trip assumption, point-in-time filing dates, and delisting-aware prices. Capacity is a feature: sized for one person, not a fund. Data: EDGAR companyfacts and full-text search, both free; this rides directly on the plan's EDGAR pipeline.

---

## Tier 2: refuted as pitched, salvaged as narrower variants

The skeptics rejected these as "neglected alpha" but named variants that survive scrutiny, most of them fitting this app better as analysis features than as edge claims.

### A. EDGAR-native red-flag and insider analytics (best fit; rides the planned EDGAR pipeline)

| Variant | Salvaged from | Shape |
|---|---|---|
| Filing red-flag screen: 8-K Items 4.02/4.01/5.02, SEC comment-letter severity, material 10-K/10-Q language changes | 8-K drift, comment letters, Lazy Prices (all refuted as short alpha: vendor-served, drift cost-eaten) | Long-only avoidance and diligence flags with text-severity conditioning. No borrow needed, education-mandate fit |
| Insider analytics layer | Insider cluster buys (refuted 3x: OpenInsider/2iQ/VerityData commoditized surfacing) | Score each insider's historical hit rate, separate opportunistic from routine (Cohen-Malloy-Pomorski), report spread-adjusted event CARs so users see whether a cluster survives realistic microcap costs |
| 13F holder-breadth decline as the neglect proxy | Analyst-coverage terminations (refuted: no free point-in-time analyst-count history exists) | Quarterly EDGAR 13F breadth, decades of free history, conditions insider and value signals in low-breadth small caps; backtestable now |
| Congress event-study module | Conditioned congress trades (refuted: Unusual Whales/Quiver productized the conditional slices) | Measure disclosure-day pops and post-disclosure drift for committee-aligned and leadership trades; negative-disclosure risk flag. Uses the existing `congress_trades.py`; small samples reported with uncertainty rather than traded |

### B. Catalyst and event layers

| Variant | Salvaged from | Shape |
|---|---|---|
| CEF catalyst monitor, sub-$200M funds | CEF discount z-scores (refuted: CEFConnect publishes z-scores free; RiverNorth/Saba/Matisse saturate the space) | EDGAR full-text alerts on 13D, tender offers, rights offerings, open-ending/liquidation proposals, managed-distribution changes; term funds tracked by discount-to-maturity. Z-scores demoted to a secondary filter |
| Index deletion and spinoff tracker, forward-looking | Deletion reversal, spinoff orphans (refuted 5x: NIXT ETF, Greenwood-Sammon show the effect collapsed, survivorship-biased backfills) | Announcement-based cohorts from now on: classify deletion reason, track discretionary cohort against small-value and against NIXT; micro-cap spinoff orphans timed off observable ETF-holdings liquidation, not fixed windows. Measurement of whether anything remains, not an assumed edge |
| Korea treasury-share deadline screen | Korea value-up (refuted: consensus trade, Weiss fund wound down) | DART screen for small-cap sub-1x-PBR firms holding 5-10%+ treasury stakes that have not filed required holding/disposal plans before the Sept 2026 statutory deadline; cancellation-announcement events in the illiquid tail |
| Japan micro-tail rerating basket | Japan sub-book screen (refuted: 56 activist campaigns in 2025, retail screeners sell it) | Sub-¥10-15B names on Standard/Growth where activist median positions run ~37x daily volume; slow basket through the TSE disclosure cycle, TDnet/EDINET triggers |
| Clinical-trials registry deltas, sub-$300M biotech | Registry surveillance (refuted: RxDataLab/Ozmosi sell exactly this to funds) | Systematic study of recruiting-to-terminated flips and completion-date slips below vendor coverage floors, via the free AACT database; sponsor-to-ticker mapping is the work |

### C. Context and attribution layers (descriptive analysis, education-mandate fit)

- **Crowding context panel:** short-interest percentile, days-to-cover, correlation with most-shorted and momentum-spread baskets, framed as after-the-fact attribution ("consistent with a positioning unwind") rather than a crash-risk signal. Salvaged from crowding-signal area (MSCI/S3 own the live version; the lagged educational version is unserved).
- **Illiquidity decomposition:** rolling Amihud as a diagnostic flagging which apparent signals are untradable cost compensation. Salvaged from the illiquidity-premium area (premium itself decayed).
- **Retail-attention flag:** extreme mention-plus-volume z-scores as a do-not-buy/underweight overlay, attention-cooling as a long filter. Free ApeWisdom data; near-zero standalone value but honest as a risk flag.
- **Leveraged-ETF rebalance pressure:** estimated per-name close rebalance demand as % of ADV from issuer NAV files, flagging only tail days (above ~3-5% of ADV) as an explanatory driver of late-day moves.
- **H-1B/PERM policy-exposure analytics:** firm-level visa dependence from free DOL files, studied on 2025-26 policy event days. A risk-exposure product, not a return signal; genuinely undone.
- **FINRA off-exchange short-ratio overlay:** avoidance/timing only, and only after validating the ratio against a known retail-flow measure; the proxy is contaminated by hedging flows.

### D. Forward collection to start now (same logic as plan Phase 1)

Several variants need history that only exists if collection starts today: analyst-count and estimate snapshots (already in the plan), a patent-docket archive (CourtListener), deletion/spinoff announcement calendars, CEF filing alerts, and Korea DART treasury-plan filings. Cheap collectors, compounding value.

---

## Tier 3: the graveyard (looks neglected, is not)

Kept as a do-not-chase list; each was refuted with specifics.

| Area | Why it is not neglected |
|---|---|
| Microcap characteristic screens (value/momentum composites) | Anomaly profit sits in uncapturable short legs; DFA/OSAM/retail screeners sold the long side for decades |
| Small-cap PEAD / multi-month drift | Most-replicated anomaly in finance; Zacks sold revision drift retail since 1988; costs eat 70-100% in the names where it persists |
| Borrow-fee overpricing screens | Markit/S3/Ortex sell it; Fintel/iBorrowDesk free since ~2014; QuantRocket published the exact study |
| Orphan/neglect scores from analyst counts | Naive premium dead since 1997; conditioning result is 20-year-old textbook material; no free PIT analyst history |
| Lazy Prices filing diffs | Brain sells the signal down-cap via Bloomberg/QuantConnect; Quantopian replicators found it gone |
| Government contract awards | DoD data hits USAspending on a 90-day delay; HigherGov/GovWin/Quiver productized every layer |
| Index add/delete front-running and reversal | Pod staple; NIXT ETF wraps the delete side; effect collapsed per Greenwood-Sammon (JF 2025) |
| Closed-end fund z-scores | CEFConnect publishes them free; dedicated funds saturate sub-$200M names |
| Overnight-vs-intraday split | Heavily published, decayed, and daily-bar backtests use unachievable open prints; NightShares liquidated |
| N-PORT monthly window-dressing shift | Premise false: SEC delayed to 2027-28 and proposed rescinding monthly disclosure entirely |
| Single-stock leveraged-ETF close flows | Nomura publishes daily estimates; impact studied and short-lived |
| Retail herding fade (BJZZ-style) | Unprofitable pre-cost in replication; vendor ecosystem sells retail-flow signals |
| Tax-loss rebound in microcaps | Bid-ask bounce manufactures the effect in close-to-close data; sell-side publishes candidate screens annually |
| Turn-of-month / pre-holiday calendar | Own source shows US large-cap effect statistically dead this decade |
| Attention-spike fade | Da-Engelberg-Gao 2011; Quiver sells WSB mentions; live replication found -0.5% vs the -4.7% headline |
| Congress-trade copying (incl. committee slices) | NANC/Autopilot/Unusual Whales productized every slice |
| Japan value-up / Korea value-up (broad) | The consensus international trades of 2025-26 |
| Lottery-stock pre-earnings demand | JFE 2020 published; factor-model-fragile; survivorship-biased to validate free |
| Spinoff forced-selling window | Greenblatt 1997 centerpiece; sell-side packages it; CSD ETF underperforms |
| Post-bankruptcy relistings | Edge documented as gone post-2010; Octus/BankruptcyData service the space |

---

## How this feeds the plan

Everything above enters through the existing machinery, not around it:

1. **Gate:** any variant that becomes a signal goes through the backtest harness (`pipeline/backtest/`) with its tripwires, cost assumptions stated, and the experiment logged. Null results ship.
2. **Data reuse:** Groups A and D ride pipelines the plan already schedules (EDGAR facts, Form 4, 13F, congress archive, estimate snapshots). The genuinely new collectors (dockets, deletion calendars, CEF alerts, DART) are small and follow the plan's collector checklist.
3. **Suggested order** (evidence-per-effort, after plan Phases 0-2): EDGAR red-flag suite, then insider/13F-breadth analytics, then the congress event-study module, then the CEF catalyst monitor, then the patent-docket replication (bigger lift, needs the archive first), then the microcap drift panel (needs delisting-aware prices).
4. **Framing discipline:** per CLAUDE.md, every one of these ships as analysis with measured uncertainty and disclaimers. The honest pitch for this app is not "here is an edge" but "here is what the data shows, including the cost and bias caveats that usually go unstated."

## Sources

Primary citations live inline above. Verification searches, vendor checks, and refutation details are from the 2026-07-05 research run (42 candidate areas, one adversarial verification each; 48 agents total).
