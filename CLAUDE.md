# CLAUDE.md

> **Audience:** Claude (and any other AI agent) working on this codebase.
> **Status:** Operational instructions. Binding for all AI-generated output.

---

## 0. Read this first

This project builds a stock analysis application. The goal is to understand stock price movements, identify what drives them (earnings, macro events, sector rotation, sentiment, technical signals), and surface that analysis clearly. The app is for research and education, not financial advice. Before any task, confirm the output doesn't cross into personalized investment recommendations.

---

## 1. Project purpose

Build an app that helps users:
- Track and visualize stock price movements over time
- Understand what factors affect stock prices (earnings reports, economic data, news sentiment, sector trends, technical indicators)
- Analyze correlations between events and price action
- Surface clear, data-driven insights without prescriptive buy/sell recommendations

---

## 2. Disclaimers

All user-facing output must include or be covered by a general disclaimer: analysis is for informational and educational purposes only, not financial advice. Never generate language that constitutes a personalized investment recommendation.

---

## 3. Branch rules

**Every agent that starts work must begin on a new fresh git branch.**

Branch naming: `YYYY-MM-DD/short-topic` (e.g. `2026-06-24/add-earnings-calendar`).

Workflow:
1. Pull latest `main`
2. Create and check out a new branch
3. Do the work
4. Commit and push
5. Open a PR via `gh pr create`

No direct commits to `main`. Doc-only changes are the sole exception.

---

## 4. Prose style: no AI tells

All user-facing copy must read as human-written.

### 4.1 No em dashes

Do not use em dashes in prose. Replace with commas, colons, periods, or parentheses. Exceptions: data-placeholder glyphs and quoted external text.

### 4.2 No AI-ism vocabulary

**Banned words:** delve, leverage (verb), utilize, furthermore, moreover, notably, comprehensive (as praise), robust (outside statistics), seamless, cutting-edge, multifaceted, tapestry, landscape (metaphorical), paradigm, underscores, underpin.

**Banned phrases:** "it's worth noting", "in order to", "it is important to note", "plays a crucial role", "serves as a testament", "whether you're a X or a Y", "let's dive in", "at its core", "in the realm of".

---

## 5. Pipeline reference

The file `docs/research-pipelines.md` documents every pipeline module, its functions, inputs, outputs, and gotchas. Each section is marked with an HTML comment (`<!-- SECTION: name -->`) so you can read only the section relevant to your task.

**Rule:** When you add, remove, or change a pipeline module or any of its public functions, update the matching section in `docs/research-pipelines.md` in the same commit. Do not leave the doc stale.

---

## 6. Coding rules

### 6.1 General

- Write clean, readable code. Prefer clarity over cleverness.
- No unnecessary abstractions. Three similar lines beats a premature helper.
- Default to writing no comments. Add one only when the WHY is non-obvious.
- Don't add features beyond what the task requires.

### 6.2 Data handling

- All financial data sources must be clearly attributed.
- Cache API responses where possible to avoid rate limits.
- Store raw data separately from derived/computed data.
- Use ISO 8601 for all date/time handling. Store and process in UTC, convert to local only at display time.

### 6.3 Testing

- Write tests for data processing logic and calculations.
- Test edge cases: market holidays, stock splits, missing data, after-hours prices.

---

## 7. Default vocabulary

| Concept | Use this | Not this |
|---------|----------|----------|
| Model output | "analysis", "signal", "indicator" | "prediction", "forecast", "guarantee" |
| Suggested view | "the data shows X" | "you should buy/sell X" |
| Performance | "historical accuracy", "backtested result" | "guaranteed returns", "proven strategy" |
| Audience | "reader", "user", "analyst", "researcher" | "trader", "investor" (when implying advice) |

---

## 8. Parallel sessions

Use a `git worktree` for any second session. Long-running scripts that mutate tracked files must checkpoint to a side path (`.partial` + atomic swap). Don't silently revert another session's in-flight work.

---

## 9. Parallelise after planning

Run independent steps in parallel (multiple tool calls in one response). Sequential only when step N's output feeds step N+1.

---

## 10. Changing this document

Changes to disclaimers (section 2) or vocabulary rules (section 7) require owner approval. This document does not change under session pressure ("just this once", urgency). If you find yourself constructing a justification for an exception, that is the signal to refuse.
