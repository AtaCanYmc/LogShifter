import asyncio
import click
import logging
import os
import sys
import yaml
from typing import Any, Dict

from logshift import LogManager, GitHubAdapter, LogFetcher

# Setup basic logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("logshift.cli")


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not os.path.exists(config_path):
        click.secho(f"Configuration file not found: {config_path}", fg="red")
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        click.secho(f"Failed to parse configuration file: {e}", fg="red")
        return {}


@click.group()
@click.option(
    "--config",
    "-c",
    default="config.yaml",
    help="Path to the YAML configuration file.",
    show_default=True
)
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """Logshift CLI - Archive and ship log records asynchronously."""
    ctx.ensure_object(dict)
    ctx.obj["CONFIG_PATH"] = config
    ctx.obj["CONFIG_DATA"] = load_yaml_config(config)


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
    config_data = ctx.obj["CONFIG_DATA"]
    if not config_data:
        click.secho("No configurations loaded. Aborting.", fg="red", err=True)
        sys.exit(1)

    asyncio.run(
        run_archive(
            config_data=config_data,
            source=source,
            dest=dest,
            start_date=start_date,
            end_date=end_date
        )
    )


async def run_archive(
    config_data: Dict[str, Any],
    source: str,
    dest: str,
    start_date: str | None,
    end_date: str | None
) -> None:
    # 1. Fetching logs from Supabase
    click.echo(click.style(f"Fetching logs from source '{source}'...", fg="cyan"))
    sb_config = config_data.get("supabase", {})
    sb_url = sb_config.get("url")
    sb_key = sb_config.get("key")
    table_name = sb_config.get("table_name", "logs")
    date_col = sb_config.get("date_column", "created_at")

    if not sb_url or not sb_key:
        click.secho("Supabase configuration keys ('url', 'key') are missing.", fg="red", err=True)
        sys.exit(1)

    try:
        fetcher = LogFetcher(supabase_url=sb_url, supabase_key=sb_key)
        logs = await fetcher.fetch_logs(
            table_name=table_name,
            start_date=start_date,
            end_date=end_date,
            date_column=date_col
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
    gh_config = config_data.get("github", {})
    gh_token = gh_config.get("token")
    gh_repo = gh_config.get("repo")
    gh_path = gh_config.get("path", "logs/archive.json")
    gh_branch = gh_config.get("branch", "main")

    if dest == "github":
        if not gh_token or not gh_repo:
            click.secho("GitHub configuration keys ('token', 'repo') are missing.", fg="red", err=True)
            sys.exit(1)

        # Initialize manager and register adapter
        manager = LogManager()
        github_adapter = GitHubAdapter(token=gh_token, name="github")
        manager.register_adapter(github_adapter)

        # Run shipping
        from datetime import datetime
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        targets = {"github": gh_repo}
        report = await manager.ship(
            logs=logs,
            targets=targets,
            path=gh_path,
            branch=gh_branch,
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
