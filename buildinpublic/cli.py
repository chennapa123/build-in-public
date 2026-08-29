from pathlib import Path
from typing import Optional
import signal
import sys
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from buildinpublic.config import get_config
from buildinpublic.git_monitor import GitMonitor
from buildinpublic.storage import StorageManager
from buildinpublic.generator import ContentGenerator
from buildinpublic.publishers.console import ConsolePublisher
from buildinpublic.watcher import BackgroundWatcher
from buildinpublic.logger import logger

app = typer.Typer(
    name="buildinpublic",
    help="Automated Content Creator for Build in Public technical updates",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()

@app.callback()
def callback():
    """
    Automated Content Creator for Build in Public technical updates.
    """
    pass

@app.command(name="scan")
def scan(
    repo_path: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Path to Git repository (defaults to GIT_REPO_PATH in .env or current directory)",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        "-l",
        help="Maximum number of recent commits to display",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all recent commits including already processed ones",
    )
) -> None:
    """
    Scan the Git repository and display commit activity (filtering out processed ones by default).
    """
    config = get_config()
    target_path = repo_path or config.git_repo_path

    console.print(Panel.fit(f"[bold blue]Build in Public[/bold blue] - Scanning repository: [yellow]{target_path}[/yellow]"))

    git_mon = GitMonitor(target_path)
    storage = StorageManager()

    if not git_mon.is_valid_repo():
        console.print(f"[bold red]Error:[/bold red] '{target_path}' is not a valid Git repository.")
        raise typer.Exit(code=1)

    try:
        commits = git_mon.get_recent_commits(max_count=limit * 2 if not show_all else limit)
    except Exception as e:
        console.print(f"[bold red]Failed to scan commits:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not commits:
        console.print("[yellow]No commits found in repository.[/yellow]")
        return

    # Filter out already processed commits unless --all flag is passed
    if not show_all:
        unprocessed_commits = [c for c in commits if not storage.is_processed(c.sha)]
        display_commits = unprocessed_commits[:limit]
    else:
        display_commits = commits[:limit]

    if not display_commits:
        console.print("[green]All recent commits have already been processed.[/green] (Use --all to view all commits)")
        return

    title = f"Unprocessed Commits ({len(display_commits)})" if not show_all else f"Recent Commits ({len(display_commits)})"
    table = Table(title=title, show_header=True, header_style="bold magenta")
    table.add_column("SHA", style="dim", width=9)
    table.add_column("Status", style="bold", width=12)
    table.add_column("Author", style="cyan", width=15)
    table.add_column("Timestamp", style="green", width=19)
    table.add_column("Message", style="white")
    table.add_column("Stats (+/-)", style="yellow", width=14)

    for c in display_commits:
        is_proc = storage.is_processed(c.sha)
        status_str = "[green]Processed[/green]" if is_proc else "[bold yellow]Pending[/bold yellow]"
        table.add_row(
            c.short_sha,
            status_str,
            c.author,
            c.timestamp.strftime("%Y-%m-%d %H:%M"),
            c.message.split("\n")[0][:50],
            f"+{c.stats.insertions}/-{c.stats.deletions}",
        )

    console.print(table)


@app.command(name="generate")
def generate(
    repo_path: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Path to Git repository",
    ),
    commit_sha: Optional[str] = typer.Option(
        None,
        "--commit",
        "-c",
        help="Specific commit SHA to process (defaults to latest unprocessed commit)",
    ),
    mark_done: bool = typer.Option(
        False,
        "--mark-processed",
        "-m",
        help="Mark the commit as processed after displaying drafts",
    )
) -> None:
    """
    Generate X (Twitter) and LinkedIn content drafts from unprocessed Git commits using LLM.
    """
    config = get_config()
    target_path = repo_path or config.git_repo_path

    if not config.gemini_api_key or config.gemini_api_key.startswith("your_gemini"):
        console.print(
            Panel(
                "[bold red]Configuration Error:[/bold red] GEMINI_API_KEY is missing or invalid in your .env file.\n\n"
                "To fix this:\n"
                "1. Get an API key from Google AI Studio (https://aistudio.google.com/)\n"
                "2. Add it to your .env file: [yellow]GEMINI_API_KEY=your_actual_key[/yellow]",
                title="Gemini API Key Required",
            )
        )
        raise typer.Exit(code=1)

    git_mon = GitMonitor(target_path)
    storage = StorageManager()

    if not git_mon.is_valid_repo():
        console.print(f"[bold red]Error:[/bold red] '{target_path}' is not a valid Git repository.")
        raise typer.Exit(code=1)

    try:
        commits = git_mon.get_recent_commits(max_count=20)
    except Exception as e:
        console.print(f"[bold red]Failed to fetch commits:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not commits:
        console.print("[yellow]No commits found in repository.[/yellow]")
        return

    target_commit = None
    if commit_sha:
        for c in commits:
            if c.sha.startswith(commit_sha):
                target_commit = c
                break
        if not target_commit:
            console.print(f"[bold red]Error:[/bold red] Commit matching '{commit_sha}' was not found in recent history.")
            raise typer.Exit(code=1)
    else:
        for c in commits:
            if not storage.is_processed(c.sha):
                target_commit = c
                break

    if not target_commit:
        console.print("[bold green]No unprocessed commits found![/bold green] All recent commits have already generated content.")
        return

    console.print(Panel(f"Generating technical posts for commit: [cyan]{target_commit.short_sha}[/cyan] - {target_commit.message.split('\n')[0]}"))

    generator = ContentGenerator()
    publisher = ConsolePublisher()

    try:
        posts = generator.generate_posts(target_commit)
        publisher.publish(posts, dry_run=True)
    except Exception as err:
        console.print(f"[bold red]Content Generation Failed:[/bold red] {err}")
        console.print("[yellow]Note: Commit remains unprocessed and can be retried later.[/yellow]")
        raise typer.Exit(code=1)

    if mark_done:
        storage.mark_processed(
            sha=target_commit.sha,
            generated_content=posts.model_dump(mode="json"),
        )
        console.print(f"[green]✓ Marked commit {target_commit.short_sha} as processed.[/green]")
    else:
        console.print("[dim]Dry-run mode: Commit was NOT marked as processed in history. (Use --mark-processed to mark it)[/dim]")


@app.command(name="start")
def start(
    repo_path: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Path to Git repository",
    ),
    interval: Optional[int] = typer.Option(
        None,
        "--interval",
        "-i",
        help="Polling interval in seconds (defaults to POLL_INTERVAL_SECONDS in .env)",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Run in dry-run mode (ConsolePublisher) or live publishing",
    )
) -> None:
    """
    Start the background watcher loop to monitor Git activity and generate posts.
    """
    watcher = BackgroundWatcher(repo_path=repo_path, poll_interval=interval, dry_run=dry_run)

    def handle_signal(sig, frame):
        console.print("\n[yellow]Shutdown signal received. Stopping background watcher...[/yellow]")
        watcher.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    console.print(
        Panel.fit(
            f"[bold green]Build in Public Watcher Started[/bold green]\n"
            f"• Repo Path: [yellow]{watcher.repo_path}[/yellow]\n"
            f"• Poll Interval: [cyan]{watcher.poll_interval}s[/cyan]\n"
            f"• Mode: [magenta]{'Dry-Run (Console)' if dry_run else 'Live Publishing'}[/magenta]\n\n"
            f"Press [bold red]Ctrl+C[/bold red] to stop.",
            title="Background Watcher",
        )
    )

    watcher.run()


@app.command(name="history")
def history(
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum history records to display",
    )
) -> None:
    """
    Display previously processed commits history.
    """
    storage = StorageManager()
    records = storage.get_processed_commits()

    if not records:
        console.print(Panel("[yellow]No commit history recorded yet.[/yellow]\nRun content generation to process commits.", title="History"))
        return

    table = Table(title=f"Processed Commit History ({len(records)})", show_header=True, header_style="bold cyan")
    table.add_column("SHA", style="dim", width=9)
    table.add_column("Processed At", style="green", width=19)
    table.add_column("Content Generated", style="yellow")

    for rec in records[:limit]:
        content_preview = "None"
        if rec.generated_content:
            keys = ", ".join(rec.generated_content.keys())
            content_preview = f"Generated ({keys})"

        table.add_row(
            rec.sha[:7],
            rec.processed_at.strftime("%Y-%m-%d %H:%M"),
            content_preview,
        )

    console.print(table)


def main():
    app()

if __name__ == "__main__":
    main()
