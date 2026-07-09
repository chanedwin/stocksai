"""Collector CLI. Run: python -m pipeline.collect.cli <command>"""

from pathlib import Path

import typer
from dotenv import load_dotenv

from pipeline.collect import state, symbols, trading_calendar

app = typer.Typer(help="Data-pipeline state and reference commands.")


@app.command()
def init() -> None:
    """Create the data/ layout and state DB."""
    load_dotenv()
    for sub in ["reference", "bronze", "silver", "gold", "state"]:
        Path("data", sub).mkdir(parents=True, exist_ok=True)
    state.connect().close()
    typer.echo("data/ layout and state DB ready")


@app.command()
def status() -> None:
    """Show watermarks and recent runs."""
    conn = state.connect()
    marks = conn.execute(
        "SELECT source, ticker, watermark, updated_at FROM watermarks ORDER BY source"
    ).fetchall()
    typer.echo(f"watermarks: {len(marks)}")
    for source, ticker, mark, updated in marks:
        typer.echo(f"  {source}[{ticker}] = {mark} (updated {updated})")
    runs = conn.execute(
        "SELECT source, started_at, status, rows FROM run_log ORDER BY id DESC LIMIT 10"
    ).fetchall()
    typer.echo(f"recent runs: {len(runs)}")
    for source, started, run_status, rows in runs:
        typer.echo(f"  {started} {source}: {run_status} ({rows} rows)")
    conn.close()


@app.command()
def universe(date: str = typer.Option(..., help="ISO date, e.g. 2026-07-09")) -> None:
    """Print S&P 500 membership as of a date."""
    members = sorted(symbols.members_at(date))
    typer.echo(f"{len(members)} members at {date}")
    typer.echo(",".join(members))


@app.command("verify-constituents")
def verify_constituents() -> None:
    """Run the constituents CSV sanity checks; exit 1 on problems."""
    problems = symbols.verify_constituents()
    if problems:
        for p in problems:
            typer.echo(f"PROBLEM: {p}")
        raise typer.Exit(code=1)
    typer.echo("constituents CSV passes all checks")


@app.command("trading-day")
def trading_day(date: str = typer.Option(..., help="ISO date")) -> None:
    """Report whether a date is an XNYS session and the last session at or before it."""
    typer.echo(f"is_trading_day({date}) = {trading_calendar.is_trading_day(date)}")
    typer.echo(f"last_trading_day({date}) = {trading_calendar.last_trading_day(date)}")


if __name__ == "__main__":
    app()
