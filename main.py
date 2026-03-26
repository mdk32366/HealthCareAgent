#!/usr/bin/env python3
"""
Healthcare RAG Agent — CLI entry point.

Usage:
    python main.py ask "What are the treatment options for Type 2 diabetes?"
    python main.py ask "hemophilia factor replacement therapy" --verbose
    python main.py notes --topic diabetes
    python main.py ingest /path/to/document.txt --topic cancer
"""
from __future__ import annotations
import logging, sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

app     = typer.Typer(help="Healthcare RAG Agent", add_completion=False)
console = Console()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def _get_agent():
    """Lazy import so CLI starts fast even if deps are partially installed."""
    from agent.orchestrator import HealthcareRAGAgent
    return HealthcareRAGAgent()


# ── ask ───────────────────────────────────────────────────────────────────────
@app.command()
def ask(
    question: str = typer.Argument(..., help="Your health-related question"),
    verbose:  bool = typer.Option(False, "--verbose", "-v", help="Show debug logs"),
    json_out: bool = typer.Option(False, "--json",           help="Output raw JSON"),
):
    """Ask a health question. Returns a fully-cited, multi-dimensional answer."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    agent = _get_agent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        transient=True,
        console=console,
    ) as prog:
        prog.add_task("Researching your question…", total=None)
        response = agent.ask(question, verbose=verbose)

    if json_out:
        import json, dataclasses
        rprint(json.dumps(dataclasses.asdict(response), indent=2, default=str))
        return

    # ── Pretty output ──────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold]{question}[/bold]",
        title="[cyan]Healthcare RAG Agent[/cyan]",
        subtitle=f"[dim]Topic: {response.topic.value}[/dim]",
        border_style="cyan",
    ))

    console.print(Markdown(response.answer))

    if response.youtube_links:
        console.print("\n[bold yellow]🎬 Video Resources[/bold yellow]")
        for link in response.youtube_links:
            console.print(f"  • [link={link}]{link}[/link]")

    if response.citations:
        console.print("\n[bold green]📚 Sources & Citations[/bold green]")
        tbl = Table(show_header=False, box=None, padding=(0, 1))
        tbl.add_column("n", style="dim", width=4)
        tbl.add_column("citation", style="white")
        for i, c in enumerate(response.citations, 1):
            tbl.add_row(f"[{i}]", c)
        console.print(tbl)

    console.print(
        f"\n[dim yellow]⚠️  {response.safety_disclaimer}[/dim yellow]"
    )
    console.print(
        f"\n[dim]⏱  {response.elapsed_seconds:.1f}s  |  "
        f"💾 {response.memory_note}[/dim]"
    )


# ── notes ─────────────────────────────────────────────────────────────────────
@app.command()
def notes(
    topic: Optional[str] = typer.Option(None, "--topic", "-t",
        help="Filter by topic: vaccines|cancer|hemophilia|'weight control'|diabetes"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List saved Obsidian notes."""
    from memory.memory_manager import ObsidianMemory
    from agent.models import HealthTopic
    mem = ObsidianMemory()

    topic_enum = None
    if topic:
        try:
            topic_enum = HealthTopic(topic.lower())
        except ValueError:
            console.print(f"[red]Unknown topic: {topic}[/red]")
            raise typer.Exit(1)

    all_notes = mem.list_notes(topic_enum)[:limit]
    if not all_notes:
        console.print("[dim]No notes found.[/dim]")
        return

    tbl = Table(title="Saved Notes", show_lines=True)
    tbl.add_column("#",     style="dim", width=4)
    tbl.add_column("Date",  width=19)
    tbl.add_column("Topic", width=14)
    tbl.add_column("File",  style="cyan")

    for i, p in enumerate(all_notes, 1):
        parts = p.stem.split("_", 2)
        date  = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]}" if len(parts[0]) == 8 else "-"
        tbl.add_row(str(i), f"{date} {parts[1] if len(parts) > 1 else ''}", p.parent.name, p.name)

    console.print(tbl)


# ── ingest ────────────────────────────────────────────────────────────────────
@app.command()
def ingest(
    filepath: Path = typer.Argument(..., help="Path to .txt or .md file to ingest"),
    topic:    str  = typer.Option("general", "--topic", "-t"),
    url:      str  = typer.Option("", "--url",  help="Source URL for citation"),
    title:    str  = typer.Option("", "--title"),
):
    """Ingest a local document into the vector store."""
    from memory.memory_manager import VectorMemory
    from agent.models import SourceDocument
    from retrieval.web_search import _chunk_text

    if not filepath.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        raise typer.Exit(1)

    text   = filepath.read_text(encoding="utf-8")
    chunks = _chunk_text(text, size=settings_chunk_size(), overlap=120)
    vm     = VectorMemory()
    docs   = [
        SourceDocument(
            content=chunk, url=url or str(filepath),
            title=title or filepath.stem, source_type="local",
            topic=topic, chunk_id=f"local_{i}",
        )
        for i, chunk in enumerate(chunks)
    ]
    n = vm.upsert(docs)
    console.print(f"[green]✓ Ingested {n} chunks from {filepath.name}[/green]")


def settings_chunk_size():
    from config.settings import settings
    return settings.chunk_size


# ── stats ─────────────────────────────────────────────────────────────────────
@app.command()
def stats():
    """Show memory statistics."""
    from memory.memory_manager import VectorMemory, ObsidianMemory
    vm  = VectorMemory()
    obs = ObsidianMemory()

    tbl = Table(title="Agent Memory Stats", show_header=False)
    tbl.add_column("key",   style="dim",   width=28)
    tbl.add_column("value", style="green")
    tbl.add_row("ChromaDB chunks",       str(vm.count()))
    tbl.add_row("Obsidian notes (total)", str(len(obs.list_notes())))
    console.print(tbl)


if __name__ == "__main__":
    app()
