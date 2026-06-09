"""AgentScope CLI — capture, list, show, compare agent runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.tree import Tree

from agentscope.core.models import EventType
from agentscope.core.store import AgentStore, get_default_storage_dir

console = Console()


@click.group()
@click.option(
    "--storage",
    type=click.Path(),
    default=None,
    help="Custom storage directory for traces.",
)
@click.version_option(version="0.1.0", prog_name="agentscope")
@click.pass_context
def cli(ctx: click.Context, storage: Optional[str]) -> None:
    """AgentScope — DevTools for coding agents.

    Replay, debug, and compare AI agent runs.
    """
    ctx.ensure_object(dict)
    ctx.obj["store"] = AgentStore(
        storage_dir=Path(storage) if storage else None
    )


@cli.command()
@click.argument("run_id")
@click.pass_context
def show(ctx: click.Context, run_id: str) -> None:
    """Show details of a captured run."""
    store: AgentStore = ctx.obj["store"]
    run = store.load_run(run_id)

    if not run:
        console.print(f"[red]Run '{run_id}' not found.[/red]")
        sys.exit(1)

    # Header
    status_color = {
        "completed": "green",
        "failed": "red",
        "running": "yellow",
        "cancelled": "dim",
    }.get(run.status, "white")

    console.print(Panel(
        f"[bold]{run.title or 'Untitled Run'}[/bold]\n"
        f"ID: [dim]{run.id}[/dim]\n"
        f"Agent: [cyan]{run.agent_type}[/cyan] | "
        f"Model: [cyan]{run.model}[/cyan] | "
        f"Status: [{status_color}]{run.status}[/{status_color}]\n"
        f"Created: {run.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Working dir: [dim]{run.working_directory}[/dim]",
        title="AgentScope Run",
        border_style="blue",
    ))

    # Summary
    s = run.summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value")
    summary_table.add_row("Events", str(s.total_events))
    summary_table.add_row("Tool calls", str(s.total_tool_calls))
    summary_table.add_row("File changes", str(s.total_file_changes))
    summary_table.add_row(
        "Tests", f"{s.tests_passed}/{s.total_tests} passed"
        + (f" [red]({s.tests_failed} failed)[/red]" if s.tests_failed else "")
    )
    summary_table.add_row("Tokens", f"{s.total_tokens:,}")
    summary_table.add_row("Cost", f"${s.total_cost_usd:.4f}")
    summary_table.add_row("Duration", f"{s.total_duration_ms:.0f}ms")
    summary_table.add_row("Errors", str(s.errors_count))
    console.print(summary_table)

    # Events timeline
    if run.events:
        console.print("\n[bold]Event Timeline:[/bold]")
        tree = Tree(f"[bold]Run: {run.title or run.id[:8]}[/bold]")
        for event in run.events:
            icon = {
                EventType.RUN_START: "▶",
                EventType.RUN_END: "■",
                EventType.LLM_RESPONSE: "💬",
                EventType.TOOL_CALL: "🔧",
                EventType.FILE_DIFF: "📝",
                EventType.TEST_RESULT: "🧪",
                EventType.GIT_STATE: "🔀",
                EventType.SHELL_COMMAND: "⚡",
                EventType.APPROVAL_REQUEST: "✅",
                EventType.ERROR: "❌",
            }.get(event.event_type, "•")

            color = "red" if event.event_type == EventType.ERROR else "dim"
            label = f"[{color}]{icon} {event.event_type.value}[/{color}]"

            if event.tool_call:
                label += f" → [cyan]{event.tool_call.tool_name}[/cyan]"
            if event.file_diff:
                label += f" → [cyan]{event.file_diff.file_path}[/cyan]"
            if event.test_result:
                result = "✓" if event.test_result.passed else "✗"
                label += f" → [cyan]{event.test_result.test_name}[/cyan] [{result}]"
            if event.error:
                label += f" [red]{event.error[:60]}[/red]"

            tree.add(label)
        console.print(tree)


@cli.command()
@click.option("--agent-type", "-a", default=None, help="Filter by agent type.")
@click.option("--status", "-s", default=None, help="Filter by status.")
@click.option("--limit", "-n", default=20, help="Max runs to show.")
@click.option("--json-output", is_flag=True, help="Output as JSON.")
@click.pass_context
def list(
    ctx: click.Context,
    agent_type: Optional[str],
    status: Optional[str],
    limit: int,
    json_output: bool,
) -> None:
    """List captured runs."""
    store: AgentStore = ctx.obj["store"]
    runs = store.list_runs(
        agent_type=agent_type, status=status, limit=limit
    )

    if json_output:
        console.print(json.dumps(
            [r.model_dump(mode="json") for r in runs], indent=2, default=str
        ))
        return

    if not runs:
        console.print("[dim]No runs captured yet.[/dim]")
        console.print("Start capturing with: [bold]agentscope record[/bold]")
        return

    table = Table(title="AgentScope Runs")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Title", max_width=30)
    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Events", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Created")

    for run in runs:
        status_color = {
            "completed": "green",
            "failed": "red",
            "running": "yellow",
        }.get(run.status, "white")

        table.add_row(
            run.id[:8],
            run.title or "Untitled",
            run.agent_type,
            f"[{status_color}]{run.status}[/{status_color}]",
            str(run.summary.total_events),
            f"{run.summary.total_duration_ms:.0f}ms",
            run.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@cli.command()
@click.argument("run_id")
@click.pass_context
def export(ctx: click.Context, run_id: str) -> None:
    """Export a run as JSON."""
    store: AgentStore = ctx.obj["store"]
    run = store.load_run(run_id)

    if not run:
        console.print(f"[red]Run '{run_id}' not found.[/red]")
        sys.exit(1)

    console.print(run.model_dump_json(indent=2, default=str))


@cli.command()
@click.argument("run_id_1")
@click.argument("run_id_2")
@click.pass_context
def compare(ctx: click.Context, run_id_1: str, run_id_2: str) -> None:
    """Compare two runs side by side."""
    store: AgentStore = ctx.obj["store"]
    run1 = store.load_run(run_id_1)
    run2 = store.load_run(run_id_2)

    if not run1 or not run2:
        console.print("[red]One or both runs not found.[/red]")
        sys.exit(1)

    table = Table(title=f"Compare: {run1.title or run1.id[:8]} vs {run2.title or run2.id[:8]}")
    table.add_column("Metric", style="bold")
    table.add_column(f"Run 1: {run1.id[:8]}", style="cyan")
    table.add_column(f"Run 2: {run2.id[:8]}", style="magenta")

    s1, s2 = run1.summary, run2.summary
    table.add_row("Status", run1.status, run2.status)
    table.add_row("Events", str(s1.total_events), str(s2.total_events))
    table.add_row("Tool calls", str(s1.total_tool_calls), str(s2.total_tool_calls))
    table.add_row("File changes", str(s1.total_file_changes), str(s2.total_file_changes))
    table.add_row(
        "Tests",
        f"{s1.tests_passed}/{s1.total_tests}",
        f"{s2.tests_passed}/{s2.total_tests}",
    )
    table.add_row("Tokens", f"{s1.total_tokens:,}", f"{s2.total_tokens:,}")
    table.add_row("Cost", f"${s1.total_cost_usd:.4f}", f"${s2.total_cost_usd:.4f}")
    table.add_row("Duration", f"{s1.total_duration_ms:.0f}ms", f"{s2.total_duration_ms:.0f}ms")
    table.add_row("Errors", str(s1.errors_count), str(s2.errors_count))

    console.print(table)


@cli.command()
@click.argument("run_id")
@click.confirmation_option(prompt="Delete this run?")
@click.pass_context
def delete(ctx: click.Context, run_id: str) -> None:
    """Delete a captured run."""
    store: AgentStore = ctx.obj["store"]
    if store.delete_run(run_id):
        console.print(f"[green]Deleted run {run_id}[/green]")
    else:
        console.print(f"[red]Run '{run_id}' not found.[/red]")
        sys.exit(1)


@cli.command()
@click.option("--days", default=30, help="Delete runs older than N days.")
@click.option("--keep", default=5, help="Minimum runs to keep.")
@click.pass_context
def prune(ctx: click.Context, days: int, keep: int) -> None:
    """Prune old runs."""
    store: AgentStore = ctx.obj["store"]
    deleted = store.prune_old_runs(max_age_days=days, keep_min=keep)
    console.print(f"[green]Deleted {deleted} old runs[/green]")


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show storage info."""
    store: AgentStore = ctx.obj["store"]
    runs = store.list_runs(limit=10000)

    total_events = sum(r.summary.total_events for r in runs)
    total_cost = sum(r.summary.total_cost_usd for r in runs)

    console.print(Panel(
        f"Storage: [cyan]{store.storage_dir}[/cyan]\n"
        f"Runs: [bold]{len(runs)}[/bold]\n"
        f"Total events: [bold]{total_events:,}[/bold]\n"
        f"Total tracked cost: [bold]${total_cost:.4f}[/bold]",
        title="AgentScope Storage",
        border_style="blue",
    ))


def main() -> None:
    cli()
