# Project Status

> **Audience:** any agent (or human) starting work on this repo. Read this, then follow the rules in `CLAUDE.md`.
> **Keep it current:** when you merge meaningful work, update "Where we are" and "Next up" in the same PR. Keep this document short; details belong in the linked docs.

**Last updated:** 2026-07-06

## What this project is

A stock analysis app for research and education: Python pipeline modules plus a Streamlit dashboard that explain price movements (technical indicators, fundamentals, money flow, events, congressional trades). Output is always analysis, signals, and indicators. Never financial advice.

Run it: `pip install -r requirements.txt && streamlit run dashboard/app.py`

## What has been built (merged to main)

| PR | What |
|---|---|
| #1 | Pipeline (yfinance fetch, technical + fundamental analysis) and Streamlit dashboard |
| #3 | Money flow, pattern detection, color-coded dashboard |
| #6 | Signal aggregator, market context, earnings analysis, congressional trade tracker (kadoa-org STOCK Act dataset), module reference doc |
| #7 | Approved plan for signal-model data pipelines (2026-07-05). Plan only |
| #9 | Backtest harness: purged walk-forward splits, rank-IC/decile evaluation, leakage tripwires, experiment log, first test suite, `/backtest` skill |
| #10 | Verified survey of neglected signal areas: 42 candidates adversarially checked, 2 survivors, ~20 salvaged variants, do-not-chase list |
| #11 | Verified survey of tail-risk signals: 36 candidates, 3 survivors; raises Phase 1 option-chain snapshot urgency; bans yfinance-only tail backtests (survivorship bias) |
| #12 | CI: pytest + prose lint on every PR, `scripts/check_prose.py` enforcing CLAUDE.md section 4, Claude Code hook linting markdown as agents write it |

## Where we are

The dashboard works end to end for any ticker, fetching on demand. Nothing persists to disk, nothing runs on a schedule, and most non-price data is a current-only snapshot with no history. That is fine for the live dashboard and useless for model training, which is why the next phase exists.

The evaluation half of plan Phases 2-3 is already built: `pipeline/backtest/` provides purged walk-forward splits, rank-IC and decile evaluation, leakage tripwires, and the experiment log, with a passing test suite in `tests/`. Any signal work must go through it (see `.claude/skills/backtest/SKILL.md`). The data phases (0 and 1) are still the blocking work.

## Next up

Execute `docs/plans/2026-07-05-signal-model-data-pipelines.md`, in phase order:

1. **Phase 0, skeleton:** `data/` bronze/silver/gold layout, state DB with watermarks, typer CLI, exchange calendar, `.env` secrets, symbol map, vendored S&P 500 constituents CSV.
2. **Phase 1, forward collectors + prices:** nightly snapshot collectors (option chains, yfinance info, analyst estimates, news, congress archive) and Tiingo price backfill. Urgent: snapshot history is unrecoverable, every day not collected is lost.
3. **Phases 2-4:** feature panel with leakage tripwires, first cross-sectional model (M0) with purged walk-forward validation, dashboard Signal Research page.
4. **Phases 5-6:** source backlog (FRED/ALFRED, FINRA, EDGAR, earnings surprises, insiders) feeding M1, then forward-collected features feeding M2.

Each phase: own branch, own PR, tests, and a `docs/research-pipelines.md` update in the same commit. Run the plan's section 11 verification checklist items before building on any free-tier assumption.

## Key documents

| Doc | Purpose |
|---|---|
| `CLAUDE.md` | Binding rules: branch workflow, prose style, vocabulary, disclaimers |
| `docs/status.md` | This file: state and next steps |
| `docs/pipeline.md` | Human-oriented overview and how to run |
| `docs/research-pipelines.md` | Module-by-module reference; must stay in sync with code |
| `docs/plans/` | Approved build plans |
| `docs/research/` | Verified research surveys feeding the plan backlog |

## Gotchas for new agents

- **Lookahead bias is the project's biggest trap.** Never join current-snapshot data (yfinance `.info`, options chains, analyst endpoints) to historical dates. The plan's section 2 standing rules are binding for all model-facing work.
- Parallel sessions happen. Use a git worktree and never revert another session's in-flight work (CLAUDE.md section 8).
- All model output vocabulary: "analysis", "signal", "score", "rank". Not "prediction" or "forecast".
