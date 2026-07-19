import asyncio
import logging
import sys
from datetime import datetime
from typing import Any

import click

from logshift.adapters.discord import DiscordAdapter
from logshift.adapters.github import GitHubAdapter
from logshift.adapters.sheets import SheetsAdapter
from logshift.adapters.slack import SlackAdapter
from logshift.adapters.telegram import TelegramAdapter
from logshift.core import LogFetcher, LogManager

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("logshift.cli")


def common_options(f: Any) -> Any:
    """Decorator sharing common Supabase configurations across subcommands."""
    f = click.option("--supabase-url", help="Supabase project URL.", required=True)(f)
    f = click.option("--supabase-key", help="Supabase API key / service role key.", required=True)(
        f
    )
    f = click.option(
        "--supabase-table", default="logs", help="Supabase logs table name.", show_default=True
    )(f)
    f = click.option(
        "--supabase-date-col",
        default="created_at",
        help="Database date column for filtering.",
        show_default=True,
    )(f)
    f = click.option(
        "--start-date", help="Filter logs starting from this ISO timestamp (greater than)."
    )(f)
    f = click.option("--end-date", help="Filter logs up to this ISO timestamp (less than).")(f)
    return f


@click.group()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Enable dry-run mode. Simulates routing without edits.",
)
@click.pass_context
def cli(ctx: click.Context, dry_run: bool) -> None:
    """Logshift CLI - Re-engineered Modular Archiving & Transport SDK."""
    ctx.ensure_object(dict)
    ctx.obj["DRY_RUN"] = dry_run


@cli.command()
@common_options
@click.option("--github-token", help="GitHub Personal Access Token.", required=True)
@click.option("--github-repo", help="Target GitHub repository (format: owner/repo).", required=True)
@click.option(
    "--github-path",
    default="logs/archive.json",
    help="Relative file path inside repository.",
    show_default=True,
)
@click.option("--github-branch", default="main", help="Target branch name.", show_default=True)
@click.pass_context
def github(
    ctx: click.Context,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    github_token: str,
    github_repo: str,
    github_path: str,
    github_branch: str,
) -> None:
    """Archive logs to a GitHub repository."""
    dry_run = ctx.obj["DRY_RUN"]
    asyncio.run(
        run_archive(
            dest="github",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            github_token=github_token,
            github_repo=github_repo,
            github_path=github_path,
            github_branch=github_branch,
        )
    )


@cli.command()
@common_options
@click.option(
    "--google-creds", help="Path to Google Service Account credentials file.", required=True
)
@click.option("--google-sheet-id", help="Google Spreadsheet ID key.", required=True)
@click.option(
    "--google-worksheet", default="Logs", help="Target worksheet name.", show_default=True
)
@click.pass_context
def sheets(
    ctx: click.Context,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    google_creds: str,
    google_sheet_id: str,
    google_worksheet: str,
) -> None:
    """Archive logs to a Google Spreadsheet."""
    dry_run = ctx.obj["DRY_RUN"]
    asyncio.run(
        run_archive(
            dest="sheets",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            google_creds=google_creds,
            google_sheet_id=google_sheet_id,
            google_worksheet=google_worksheet,
        )
    )


@cli.command()
@common_options
@click.option("--telegram-token", help="Telegram Bot Token.", required=True)
@click.option("--telegram-chat-id", help="Telegram Chat ID.", required=True)
@click.pass_context
def telegram(
    ctx: click.Context,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    telegram_token: str,
    telegram_chat_id: str,
) -> None:
    """Archive logs to a Telegram chat channel."""
    dry_run = ctx.obj["DRY_RUN"]
    asyncio.run(
        run_archive(
            dest="telegram",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
        )
    )


@cli.command()
@common_options
@click.option("--discord-webhook", help="Discord Webhook URL.", required=True)
@click.pass_context
def discord(
    ctx: click.Context,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    discord_webhook: str,
) -> None:
    """Archive logs to a Discord webhook channel."""
    dry_run = ctx.obj["DRY_RUN"]
    asyncio.run(
        run_archive(
            dest="discord",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            discord_webhook=discord_webhook,
        )
    )


@cli.command()
@common_options
@click.option("--slack-webhook", help="Slack Webhook URL.", required=True)
@click.pass_context
def slack(
    ctx: click.Context,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    slack_webhook: str,
) -> None:
    """Archive logs to a Slack webhook channel."""
    dry_run = ctx.obj["DRY_RUN"]
    asyncio.run(
        run_archive(
            dest="slack",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            supabase_table=supabase_table,
            supabase_date_col=supabase_date_col,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            slack_webhook=slack_webhook,
        )
    )


async def run_archive(
    dest: str,
    supabase_url: str,
    supabase_key: str,
    supabase_table: str,
    supabase_date_col: str,
    start_date: str | None,
    end_date: str | None,
    dry_run: bool,
    github_token: str | None = None,
    github_repo: str | None = None,
    github_path: str = "logs/archive.json",
    github_branch: str = "main",
    google_creds: str | None = None,
    google_sheet_id: str | None = None,
    google_worksheet: str = "Logs",
    telegram_token: str | None = None,
    telegram_chat_id: str | None = None,
    discord_webhook: str | None = None,
    slack_webhook: str | None = None,
) -> None:
    if dry_run:
        click.secho(
            "!!! DRY-RUN MODE ACTIVE: NO MODIFICATIONS WILL BE COMMITTED OR UPLOADED !!!",
            fg="yellow",
            bold=True,
        )

    # 1. Fetching & Shipping logs dynamically (Streaming)
    click.echo(click.style(f"Initializing pipeline for destination: {dest}...", fg="cyan"))

    # Initialize manager with dry-run and retry logic
    manager = LogManager(dry_run=dry_run)
    targets = {}

    # Setup GitHub Adapter if configured and requested
    if dest == "github" and github_token and github_repo:
        github_adapter = GitHubAdapter(token=github_token, name="github")
        manager.register_adapter(github_adapter)
        targets["github"] = github_repo

    # Setup Google Sheets Adapter if configured and requested
    elif dest == "sheets" and google_creds and google_sheet_id:
        sheets_adapter = SheetsAdapter(
            service_account_file=google_creds,
            spreadsheet_id=google_sheet_id,
            worksheet_name=google_worksheet,
            name="sheets",
        )
        manager.register_adapter(sheets_adapter)
        targets["sheets"] = google_sheet_id

    # Setup Telegram Adapter if configured and requested
    elif dest == "telegram" and telegram_token and telegram_chat_id:
        telegram_adapter = TelegramAdapter(
            bot_token=telegram_token, chat_id=telegram_chat_id, name="telegram"
        )
        manager.register_adapter(telegram_adapter)
        targets["telegram"] = telegram_chat_id

    # Setup Discord Adapter if configured and requested
    elif dest == "discord" and discord_webhook:
        discord_adapter = DiscordAdapter(webhook_url=discord_webhook, name="discord")
        manager.register_adapter(discord_adapter)
        targets["discord"] = discord_webhook

    # Setup Slack Adapter if configured and requested
    elif dest == "slack" and slack_webhook:
        slack_adapter = SlackAdapter(webhook_url=slack_webhook, name="slack")
        manager.register_adapter(slack_adapter)
        targets["slack"] = slack_webhook

    if not targets:
        click.secho("No active adapters configured for shipment.", fg="red", err=True)
        sys.exit(1)

    # Accumulate results across chunks
    aggregated_report = {name: True for name in targets}
    total_shipped = 0
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        # Determine log source stream
        if dry_run and supabase_url.startswith("https://dummy"):
            click.echo("[Dry-Run] Using mock Supabase records because URL is mock.")

            # Yield single mock chunk
            async def dummy_generator() -> Any:
                yield [
                    {
                        "timestamp": "2026-07-19T12:00:00Z",
                        "severity_text": "INFO",
                        "severity_number": 9,
                        "body": "Dummy log 1",
                        "attributes": {"id": 1},
                        "trace_id": "",
                        "span_id": "",
                    },
                    {
                        "timestamp": "2026-07-19T12:05:00Z",
                        "severity_text": "WARNING",
                        "severity_number": 13,
                        "body": "Dummy log 2",
                        "attributes": {"id": 2},
                        "trace_id": "",
                        "span_id": "",
                    },
                ]

            log_stream: Any = dummy_generator()
        else:
            fetcher = LogFetcher(supabase_url=supabase_url, supabase_key=supabase_key)
            log_stream = fetcher.fetch_logs_iter(
                table_name=supabase_table,
                start_date=start_date,
                end_date=end_date,
                date_column=supabase_date_col,
            )

        async for chunk in log_stream:
            if not chunk:
                continue

            click.echo(
                click.style(f"Streaming and shipping chunk of {len(chunk)} logs...", fg="cyan")
            )
            report = await manager.ship(
                logs=chunk,
                targets=targets,
                path=github_path,
                branch=github_branch,
                message=f"Archive logs: {today_str}",
            )
            for adapter, success in report.items():
                if not success:
                    aggregated_report[adapter] = False
            total_shipped += len(chunk)

        if total_shipped == 0:
            click.secho("No log records retrieved for the given filters.", fg="yellow")
            return

        click.secho(f"Successfully processed total of {total_shipped} logs.", fg="green", bold=True)

    except Exception as e:
        click.secho(f"Extraction/Shipping pipeline failed: {e}", fg="red", err=True)
        sys.exit(1)

    # Display report
    click.echo("\n--- Shipping Summary Report ---")
    all_success = True
    for adapter, status in aggregated_report.items():
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
