import asyncio
import click
import logging
import sys
from datetime import datetime

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
# Supabase Parameters
@click.option("--supabase-url", help="Supabase project URL.", required=True)
@click.option("--supabase-key", help="Supabase API key / service role key.", required=True)
@click.option("--supabase-table", default="logs", help="Supabase logs table name.", show_default=True)
@click.option("--supabase-date-col", default="created_at", help="Database date column for filtering.", show_default=True)
# GitHub Parameters
@click.option("--github-token", help="GitHub Personal Access Token.")
@click.option("--github-repo", help="Target GitHub repository (format: owner/repo).")
@click.option("--github-path", default="logs/archive.json", help="Relative file path inside repository.", show_default=True)
@click.option("--github-branch", default="main", help="Target branch name.", show_default=True)
# Google Sheets Parameters
@click.option("--google-creds", help="Path to Google Service Account credentials.json file.")
@click.option("--google-sheet-id", help="Google Spreadsheet ID key.")
@click.option("--google-worksheet", default="Logs", help="Target worksheet name.", show_default=True)
# Telegram Parameters
@click.option("--telegram-token", help="Telegram Bot Token.")
@click.option("--telegram-chat-id", help="Telegram Chat ID.")
# Discord Parameters
@click.option("--discord-webhook", help="Discord Webhook URL.")
# Slack Parameters
@click.option("--slack-webhook", help="Slack Webhook URL.")
# Date Filters
@click.option("--start-date", help="Filter logs starting from this ISO timestamp (greater than).")
@click.option("--end-date", help="Filter logs up to this ISO timestamp (less than).")
@click.pass_context
def archive(
    ctx: click.Context,
    source: str,
    dest: str,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    github_token: str | None,
    github_repo: str | None,
    github_path: str,
    github_branch: str,
    google_creds: str | None,
    google_sheet_id: str | None,
    google_worksheet: str,
    telegram_token: str | None,
    telegram_chat_id: str | None,
    discord_webhook: str | None,
    slack_webhook: str | None,
    start_date: str | None,
    end_date: str | None
) -> None:
    """Extract logs from source database and archive them to the selected destination(s)."""
    dry_run = ctx.obj["DRY_RUN"]

    asyncio.run(
        run_archive(
            source=source,
            dest=dest,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            github_token=github_token,
            github_repo=github_repo,
            github_path=github_path,
            github_branch=github_branch,
            google_creds=google_creds,
            google_sheet_id=google_sheet_id,
            google_worksheet=google_worksheet,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            discord_webhook=discord_webhook,
            slack_webhook=slack_webhook,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run
        )
    )


async def run_archive(
    source: str,
    dest: str,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    github_token: str | None,
    github_repo: str | None,
    github_path: str,
    github_branch: str,
    google_creds: str | None,
    google_sheet_id: str | None,
    google_worksheet: str,
    telegram_token: str | None,
    telegram_chat_id: str | None,
    discord_webhook: str | None,
    slack_webhook: str | None,
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
        if dry_run and supabase_url.startswith("https://dummy"):
            click.echo("[Dry-Run] Using mock Supabase records because URL is mock.")
            logs = [
                {"id": 1, "created_at": "2026-07-19T12:00:00Z", "level": "INFO", "message": "Dummy log 1"},
                {"id": 2, "created_at": "2026-07-19T12:05:00Z", "level": "WARNING", "message": "Dummy log 2"}
            ]
        else:
            fetcher = LogFetcher(supabase_url=supabase_url, supabase_key=supabase_key)
            logs = await fetcher.fetch_logs(
                table_name=supabase_table,
                start_date=start_date,
                end_date=end_date,
                date_column=supabase_date_col
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
        if github_token and github_repo:
            github_adapter = GitHubAdapter(token=github_token, name="github")
            manager.register_adapter(github_adapter)
            targets["github"] = github_repo
        else:
            click.secho("GitHub adapter requested but configuration parameters (--github-token, --github-repo) missing.", fg="yellow")

    # Setup Google Sheets Adapter if configured and requested
    if "sheets" in dest_list:
        if google_creds and google_sheet_id:
            sheets_adapter = SheetsAdapter(
                service_account_file=google_creds,
                spreadsheet_id=google_sheet_id,
                worksheet_name=google_worksheet,
                name="sheets"
            )
            manager.register_adapter(sheets_adapter)
            targets["sheets"] = google_sheet_id
        else:
            click.secho("Sheets adapter requested but configuration parameters (--google-creds, --google-sheet-id) missing.", fg="yellow")

    # Setup Telegram Adapter if configured and requested
    if "telegram" in dest_list:
        if telegram_token and telegram_chat_id:
            telegram_adapter = TelegramAdapter(
                bot_token=telegram_token,
                chat_id=telegram_chat_id,
                name="telegram"
            )
            manager.register_adapter(telegram_adapter)
            targets["telegram"] = telegram_chat_id
        else:
            click.secho("Telegram adapter requested but configuration parameters (--telegram-token, --telegram-chat-id) missing.", fg="yellow")
    # Setup Discord Adapter if configured and requested
    if "discord" in dest_list:
        if discord_webhook:
            discord_adapter = DiscordAdapter(
                webhook_url=discord_webhook,
                name="discord"
            )
            manager.register_adapter(discord_adapter)
            targets["discord"] = discord_webhook
        else:
            click.secho("Discord adapter requested but configuration parameter (--discord-webhook) missing.", fg="yellow")

    # Setup Slack Adapter if configured and requested
    if "slack" in dest_list:
        if slack_webhook:
            slack_adapter = SlackAdapter(
                webhook_url=slack_webhook,
                name="slack"
            )
            manager.register_adapter(slack_adapter)
            targets["slack"] = slack_webhook
        else:
            click.secho("Slack adapter requested but configuration parameter (--slack-webhook) missing.", fg="yellow")

    if not targets:
        click.secho("No active adapters configured for shipment.", fg="red", err=True)
        sys.exit(1)

    # Trigger shipment
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    report = await manager.ship(
        logs=logs,
        targets=targets,
        path=github_path,
        branch=github_branch,
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
