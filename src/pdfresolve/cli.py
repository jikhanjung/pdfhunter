"""Command-line interface for PDFResolve."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pdfresolve import __version__
from pdfresolve.core.config import Config
from pdfresolve.core.document import Document
from pdfresolve.core.pipeline import Pipeline
from pdfresolve.extraction.page_selector import PageSelector
from pdfresolve.export import export_csl_json, export_ris, export_bibtex, export_zotero_json
from pdfresolve.export.csl_json import export_csl_json_string
from pdfresolve.export.ris import export_ris_string
from pdfresolve.export.bibtex import export_bibtex_string
from pdfresolve.export.zotero_json import export_zotero_json_string
from pdfresolve.models.bibliography import RecordStatus
from pdfresolve.utils.logging import setup_logging

app = typer.Typer(
    name="pdfresolve",
    help="Automatic bibliographic metadata extraction from PDF documents.",
    add_completion=False,
)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """PDFResolve: Extract bibliographic metadata from PDFs."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@app.command()
def version():
    """Show version information."""
    console.print(f"PDFResolve version {__version__}")


@app.command()
def info(
    file_path: Path = typer.Argument(..., help="Path to PDF or image file"),
):
    """Show document information."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    try:
        doc = Document(file_path)
        metadata = doc.metadata

        # Create info table
        table = Table(title=f"Document: {metadata.filename}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Type", metadata.document_type.value)
        table.add_row("Pages", str(metadata.page_count))
        table.add_row("Has Text Layer", "Yes" if metadata.has_text_layer else "No")
        table.add_row("File Size", f"{metadata.file_size_bytes:,} bytes")

        if metadata.title:
            table.add_row("PDF Title", metadata.title)
        if metadata.author:
            table.add_row("PDF Author", metadata.author)

        console.print(table)

        # Show page selection
        selector = PageSelector(doc)
        pages = selector.select_default_pages()

        console.print("\n[bold]Pages to process:[/bold]")
        for page in pages:
            console.print(f"  - Page {page.page_number}: {page.role.value}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def extract(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., help="Path to PDF or image file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("csl-json", "--format", "-f", help="Output format: csl-json, ris, bibtex, zotero"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider: openai, anthropic"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model: gpt-4o-mini, gpt-5.1, gpt-5.2, etc."),
    mock_llm: bool = typer.Option(False, "--mock-llm", help="Use mock LLM for testing"),
    no_web_search: bool = typer.Option(False, "--no-web-search", help="Disable web search enrichment"),
):
    """Extract bibliographic metadata from a document."""
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)

    # Validate format
    valid_formats = ["csl-json", "ris", "bibtex", "zotero"]
    if format not in valid_formats:
        console.print(f"[red]Error: Invalid format '{format}'. Choose from: {', '.join(valid_formats)}[/red]")
        raise typer.Exit(1)

    try:
        # Load document
        with console.status("[bold blue]Loading document..."):
            doc = Document(file_path)

        console.print(f"[dim]Document: {doc.metadata.filename}[/dim]")
        console.print(f"[dim]Type: {doc.document_type.value}, Pages: {doc.page_count}[/dim]")

        # Run pipeline
        with console.status("[bold blue]Running extraction pipeline..."):
            # Override provider/model if specified
            config = Config.load()
            if provider:
                config.llm.provider = provider
            if model:
                config.llm.model = model
            pipeline = Pipeline(config=config, use_mock_llm=mock_llm, verbose=verbose)
            record = pipeline.run(doc)

        # Display verbose debug info if requested
        if verbose and pipeline.debug_info:
            _display_debug_info(pipeline.debug_info)

        # Display results
        _display_record(record)

        # Export
        if output:
            _export_record(record, output, format)
            console.print(f"\n[green]Saved to: {output}[/green]")
        else:
            # Print to stdout
            console.print("\n[bold]Output:[/bold]")
            output_str = _format_record(record, format)
            console.print(output_str)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _display_debug_info(debug_info):
    """Display debug information from the extraction pipeline."""
    from rich.panel import Panel
    from rich.json import JSON

    console.print("\n[bold yellow]═══ Debug Information ═══[/bold yellow]\n")

    # PDF metadata
    if debug_info.pdf_metadata:
        console.print("[bold cyan]PDF Metadata:[/bold cyan]")
        for field, value in debug_info.pdf_metadata.items():
            if value:
                console.print(f"  {field}: {value}")
        console.print()

    # Rule-based results summary
    if debug_info.rule_based_results:
        console.print("[bold cyan]Rule-based Extraction:[/bold cyan]")
        for i, result in enumerate(debug_info.rule_based_results):
            if result:
                fields = {k: v for k, v in result.items() if v and k not in ["matches", "source_text"]}
                if fields:
                    console.print(f"  Page {i+1}: {fields}")

    # LLM text extraction
    if debug_info.llm_text_result:
        console.print("\n[bold cyan]LLM Text Extraction:[/bold cyan]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="dim")
        table.add_column("Value")
        for field, value in debug_info.llm_text_result.items():
            if value:
                table.add_row(field, str(value)[:80])
        console.print(table)

    # LLM vision extraction
    if debug_info.llm_vision_result:
        console.print("\n[bold cyan]LLM Vision Extraction:[/bold cyan]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="dim")
        table.add_column("Value")
        for field, value in debug_info.llm_vision_result.items():
            if value:
                table.add_row(field, str(value)[:80])
        console.print(table)

    # Conflicts
    if debug_info.conflicts:
        console.print("\n[bold red]Conflicts Detected:[/bold red]")
        for conflict in debug_info.conflicts:
            console.print(
                f"  [yellow]{conflict['field']}[/yellow]: "
                f"text='{conflict['text_value']}' vs vision='{conflict['vision_value']}' "
                f"[dim](using vision)[/dim]"
            )

    console.print("\n[dim]─" * 50 + "[/dim]\n")


def _display_record(record):
    """Display extracted record in a formatted table."""
    status_color = {
        RecordStatus.CONFIRMED: "green",
        RecordStatus.NEEDS_REVIEW: "yellow",
        RecordStatus.FAILED: "red",
    }
    color = status_color.get(record.status, "white")

    table = Table(title="Extracted Metadata", show_header=True)
    table.add_column("Field", style="cyan", width=20)
    table.add_column("Value", style="white")

    # Core fields
    if record.title:
        table.add_row("Title", record.title)
    if record.author:
        authors = ", ".join(
            a.literal or f"{a.family}, {a.given}" if a.given else a.family
            for a in record.author
        )
        table.add_row("Authors", authors)
    if record.issued and record.issued.year:
        table.add_row("Year", str(record.issued.year))
    if record.container_title:
        table.add_row("Container", record.container_title)
    if record.volume:
        table.add_row("Volume", record.volume)
    if record.issue:
        table.add_row("Issue", record.issue)
    if record.page:
        table.add_row("Pages", record.page)
    if record.publisher:
        table.add_row("Publisher", record.publisher)
    if record.publisher_place:
        table.add_row("Place", record.publisher_place)
    if record.doi:
        table.add_row("DOI", record.doi)
    if record.issn:
        table.add_row("ISSN", record.issn)
    if record.isbn:
        table.add_row("ISBN", record.isbn)

    # Status
    table.add_row("Status", f"[{color}]{record.status.value}[/{color}]")
    table.add_row("Confidence", f"{record.confidence:.1%}")
    table.add_row("Type", record.type)

    console.print(table)


def _format_record(record, format: str) -> str:
    """Format record as string in specified format."""
    if format == "csl-json":
        return export_csl_json_string(record, indent=2)
    elif format == "ris":
        return export_ris_string(record)
    elif format == "bibtex":
        return export_bibtex_string(record)
    elif format == "zotero":
        return export_zotero_json_string(record, indent=2)
    return ""


def _export_record(record, output_path: Path, format: str) -> None:
    """Export record to file in specified format."""
    if format == "csl-json":
        export_csl_json(record, output_path)
    elif format == "ris":
        export_ris(record, output_path)
    elif format == "bibtex":
        export_bibtex(record, output_path)
    elif format == "zotero":
        export_zotero_json(record, output_path)


if __name__ == "__main__":
    app()
