import asyncio
import click
import logging
import sys
from datetime import datetime
from pydantic import ValidationError

from logshift.config import LogshiftSettings
from logshift.core import LogManager, LogFetcher
from logshift.adapters.github import GitHubAdapter
from logshift.adapters.sheets import SheetsAdapter
from logshift.adapters.telegram import TelegramAdapter

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
    help="Enable dry-run simulation mode. Runs extraction and formatting without executing commits, uploads, or notifications."
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
    default="github",
    help="Log destination repository/storage (comma-separated, e.g. github,sheets,telegram).",
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
    """Extract logs from source database and archive them to the selected destination(s)."""
    dry_run = ctx.obj["DRY_RUN"]
    
    if "SETTINGS_ERROR" in ctx.obj and not dry_run:
        click.secho("Cannot execute archiving because of validation errors:", fg="red", err=True)
        click.echo(ctx.obj["SETTINGS_ERROR"], err=True)
        sys.exit(1)

    settings: LogshiftSettings = ctx.obj.get("SETTINGS") or LogshiftSettings.model_construct(
        supabase_url="https://dummy.supabase.co",
        supabase_key="dummy",
        logshift_github_token="dummy",
        logshift_github_repo="dummy/dummy",
        google_service_account_file="dummy.json",
        google_spreadsheet_id="dummy",
        telegram_bot_token="dummy",
        telegram_chat_id="dummy"
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

    # Parse destinations
    dest_list = [d.strip().lower() for d in dest.split(",")]

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
    click.echo(click.style(f"Shipping logs to destinations: {dest_list}...", fg="cyan"))

    # Initialize manager with dry-run and retry logic
    manager = LogManager(dry_run=dry_run)
    targets = {}

    # Setup GitHub Adapter if configured and requested
    if "github" in dest_list:
        if settings.logshift_github_token and settings.logshift_github_repo:
            github_adapter = GitHubAdapter(token=settings.logshift_github_token, name="github")
            manager.register_adapter(github_adapter)
            targets["github"] = settings.logshift_github_repo
        else:
            click.secho("GitHub adapter requested but configuration missing.", fg="yellow")

    # Setup Google Sheets Adapter if configured and requested
    if "sheets" in dest_list:
        if settings.google_service_account_file and settings.google_spreadsheet_id:
            sheets_adapter = SheetsAdapter(
                service_account_file=settings.google_service_account_file,
                spreadsheet_id=settings.google_spreadsheet_id,
                worksheet_name=settings.google_worksheet_name,
                name="sheets"
            )
            manager.register_adapter(sheets_adapter)
            targets["sheets"] = settings.google_spreadsheet_id
        else:
            click.secho("Sheets adapter requested but configuration missing.", fg="yellow")

    # Setup Telegram Adapter if configured and requested
    if "telegram" in dest_list:
        if settings.telegram_bot_token and settings.telegram_chat_id:
            telegram_adapter = TelegramAdapter(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
                name="telegram"
            )
            manager.register_adapter(telegram_adapter)
            targets["telegram"] = settings.telegram_chat_id
        else:
            click.secho("Telegram adapter requested but configuration missing.", fg="yellow")

    if not targets:
        click.secho("No active adapters configured for shipment.", fg="red", err=True)
        sys.exit(1)

    # Trigger shipment
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    report = await manager.ship(
        logs=logs,
        targets=targets,
        path=settings.logshift_github_path,
        branch=settings.logshift_github_branch,
        message=f"Archive logs: {today_str}"
    )

    # Display report
    click.echo("\n--- Shipping Summary Report ---")
    all_success = True
    for adapter, status in report.items():
        if status:
            click.echo(f"Adapter '{adapter}' -> " + click.style("SUCCESS", fg="green"))
        else:
            click.echo(f"Adapter '{adapter}' -> " + click.style("FAILED", fg="red"))
            all_success = False

    if all_success:
        click.secho("\nArchiving completed successfully to all targets!", fg="green", bold=True)
    else:
        click.secho("\nArchiving completed with some errors.", fg="yellow", bold=True)
        sys.exit(1)


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
