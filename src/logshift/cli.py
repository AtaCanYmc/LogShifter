import asyncio
import click
import logging
import sys
from datetime import datetime
from pydantic import ValidationError

from logshift.config import LogshiftSettings
from logshift.core import LogManager, LogFetcher
from logshift.adapters.github import GitHubAdapter

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("logshift.cli")


@click.group()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Enable dry-run simulation mode. Runs extraction and formatting without executing commits, uploads, or modifications."
)
@click.pass_context
def cli(ctx: click.Context, dry_run: bool) -> None:
    """Logshift CLI - Re-engineered Modular Archiving & Transport SDK."""
    ctx.ensure_object(dict)
    ctx.obj["DRY_RUN"] = dry_run

    # Load configuration settings via Pydantic
    try:
        settings = LogshiftSettings()
        ctx.obj["SETTINGS"] = settings
    except ValidationError as e:
        click.secho("Configuration validation failed. Ensure required environment variables or .env parameters are set.", fg="yellow", err=True)
        # Display validation errors but don't exit here since help commands should still work
        ctx.obj["SETTINGS_ERROR"] = e


@cli.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["supabase"]),
    default="supabase",
    help="Log source database.",
    show_default=True
)
@click.option(
    "--dest",
    "-d",
    type=click.Choice(["github"]),
    default="github",
    help="Log destination repository/storage.",
    show_default=True
)
@click.option(
    "--start-date",
    help="Filter logs starting from this ISO timestamp (greater than).",
    default=None
)
@click.option(
    "--end-date",
    help="Filter logs up to this ISO timestamp (less than).",
    default=None
)
@click.pass_context
def archive(
    ctx: click.Context,
    source: str,
    dest: str,
    start_date: str | None,
    end_date: str | None
) -> None:
    """Extract logs from source database and archive them to the selected destination."""
    dry_run = ctx.obj["DRY_RUN"]
    
    if "SETTINGS_ERROR" in ctx.obj and not dry_run:
        click.secho("Cannot execute archiving because of validation errors:", fg="red", err=True)
        click.echo(ctx.obj["SETTINGS_ERROR"], err=True)
        sys.exit(1)

    settings: LogshiftSettings = ctx.obj.get("SETTINGS") or LogshiftSettings.model_construct(
        supabase_url="https://dummy.supabase.co",
        supabase_key="dummy",
        logshift_github_token="dummy",
        logshift_github_repo="dummy/dummy"
    )

    asyncio.run(
        run_archive(
            settings=settings,
            source=source,
            dest=dest,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run
        )
    )


async def run_archive(
    settings: LogshiftSettings,
    source: str,
    dest: str,
    start_date: str | None,
    end_date: str | None,
    dry_run: bool
) -> None:
    if dry_run:
        click.secho("!!! DRY-RUN MODE ACTIVE: NO MODIFICATIONS WILL BE COMMITTED OR UPLOADED !!!", fg="yellow", bold=True)

    # 1. Fetching logs from Supabase
    click.echo(click.style(f"Fetching logs from source '{source}'...", fg="cyan"))
    
    try:
        if dry_run and settings.supabase_url.startswith("https://dummy"):
            click.echo("[Dry-Run] Using mock Supabase records because URL is mock.")
            logs = [
                {"id": 1, "created_at": "2026-07-19T12:00:00Z", "level": "INFO", "message": "Dummy log 1"},
                {"id": 2, "created_at": "2026-07-19T12:05:00Z", "level": "WARNING", "message": "Dummy log 2"}
            ]
        else:
            fetcher = LogFetcher(supabase_url=settings.supabase_url, supabase_key=settings.supabase_key)
            logs = await fetcher.fetch_logs(
                table_name=settings.supabase_table_name,
                start_date=start_date,
                end_date=end_date,
                date_column=settings.supabase_date_column
            )
        
        if not logs:
            click.secho("No log records retrieved for the given filters.", fg="yellow")
            return

        click.secho(f"Successfully retrieved {len(logs)} logs from Supabase.", fg="green")

    except Exception as e:
        click.secho(f"Extraction failed: {e}", fg="red", err=True)
        sys.exit(1)

    # 2. Shipping logs
    click.echo(click.style(f"Shipping logs to destination '{dest}'...", fg="cyan"))

    if dest == "github":
        # Initialize manager with dry-run settings
        manager = LogManager(dry_run=dry_run)
        
        github_adapter = GitHubAdapter(token=settings.logshift_github_token, name="github")
        manager.register_adapter(github_adapter)

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        targets = {"github": settings.logshift_github_repo}
        report = await manager.ship(
            logs=logs,
            targets=targets,
            path=settings.logshift_github_path,
            branch=settings.logshift_github_branch,
            message=f"Archive logs: {today_str}"
        )

        success = report.get("github", False)
        if success:
            click.secho("Archiving completed successfully!", fg="green", bold=True)
        else:
            click.secho("Archiving failed to push to GitHub.", fg="red", err=True)
            sys.exit(1)


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
