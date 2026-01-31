"""Command-line interface for ZoteroSync."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zoterosync.config import ZoteroSyncConfig

app = typer.Typer(
    name="zoterosync",
    help="Zotero library synchronization tool.",
    add_completion=False,
)
console = Console()


def _require_config() -> ZoteroSyncConfig:
    config = ZoteroSyncConfig()
    if not config.zotero_api_key or not config.zotero_library_id:
        console.print(
            "[red]Error: ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set "
            "in environment or .env file.[/red]"
        )
        raise typer.Exit(1)
    return config


def _make_log_callback(verbose: bool):
    """Create a log callback that prints progress when verbose is True."""
    if not verbose:
        return None

    def _on_log(stage: str, msg: str):
        console.print(f"  [dim][{stage}][/dim] {msg}")

    return _on_log


@app.command()
def clone(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed progress"),
):
    """Clone entire Zotero library to local database."""
    from zoterosync.sync import full_clone

    config = _require_config()

    if verbose:
        console.print("[bold blue]Cloning Zotero library...[/bold blue]")
        result = full_clone(config, on_log=_make_log_callback(True))
    else:
        with console.status("[bold blue]Cloning Zotero library..."):
            result = full_clone(config)

    console.print(
        f"[green]Clone complete:[/green] {result['items']} items, "
        f"{result['collections']} collections (version {result['library_version']})"
    )


@app.command()
def sync(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed progress"),
):
    """Incremental sync of Zotero library changes."""
    from zoterosync.sync import incremental_sync

    config = _require_config()

    if verbose:
        console.print("[bold blue]Syncing Zotero library...[/bold blue]")
        result = incremental_sync(config, on_log=_make_log_callback(True))
    else:
        with console.status("[bold blue]Syncing Zotero library..."):
            result = incremental_sync(config)

    if "updated_items" in result:
        console.print(
            f"[green]Sync complete:[/green] {result['updated_items']} updated items, "
            f"{result['deleted_items']} deleted items (version {result['library_version']})"
        )
    else:
        console.print(f"[green]Full clone performed:[/green] {result['items']} items")


@app.command()
def export(
    output_dir: Path = typer.Option(
        "data/zotero/export", "--output", "-o", help="Output directory"
    ),
):
    """Export local Zotero database to JSON files."""
    from zoterosync.export import export_to_json

    config = ZoteroSyncConfig()
    db_path = config.db_path

    if not db_path.exists():
        console.print(
            "[red]Error: No local database found. Run 'zoterosync clone' first.[/red]"
        )
        raise typer.Exit(1)

    result = export_to_json(db_path, Path(output_dir))
    console.print(
        f"[green]Exported:[/green] {result['items']} items, "
        f"{result['collections']} collections to {output_dir}/"
    )


@app.command()
def status():
    """Show sync status of local Zotero database."""
    from zoterosync.db import ZoteroDB

    config = ZoteroSyncConfig()

    if not config.db_path.exists():
        console.print(
            "[yellow]No local database found. Run 'zoterosync clone' first.[/yellow]"
        )
        raise typer.Exit(0)

    with ZoteroDB(config.db_path) as db:
        sync_state = db.get_sync_state(config.zotero_library_id)
        item_count = db.get_item_count()
        collection_count = db.get_collection_count()

    table = Table(title="Zotero Sync Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Database", str(config.db_path))
    table.add_row("Items", str(item_count))
    table.add_row("Collections", str(collection_count))
    if sync_state:
        table.add_row("Last Version", str(sync_state["last_version"]))
        table.add_row("Last Synced", sync_state["last_synced_at"])
    console.print(table)


if __name__ == "__main__":
    app()
