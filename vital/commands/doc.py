import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context, executor
from vital.safety import show_plan

console = Console()


def run(
    path: str = typer.Argument(".", help="File or folder to document"),
    output: str = typer.Option(None, "--output", "-o", help="Output file (default: README.md)"),
):
    """Auto-generate documentation for your code."""

    console.print(Panel("[bold cyan]Vital Documentation Generator[/bold cyan]", border_style="cyan"))

    import os
    if os.path.isfile(path):
        ctx = context.get_file_context(path)
        target = f"file '{path}'"
        default_output = path.replace(".py", "_docs.md")
    else:
        console.print(f"\n[dim]Scanning {path}...[/dim]")
        ctx = context.build_context(path)
        lang = context.detect_language(path)
        target = f"project (language: {lang})"
        default_output = "README.md"

    output_file = output or default_output

    prompt = f"""
Generate comprehensive documentation for this {target}. Include:

# Project/File Name

## Overview
What this does in plain English.

## Installation
How to install and set up.

## Usage
How to use it with examples.

## Functions/Classes Reference
Each function/class with parameters and return values.

## Examples
Real usage examples with code.

Code to document:
{ctx}
"""

    console.print(f"\n[bold yellow]Generating docs for {target}...[/bold yellow]\n")
    docs = ai_engine.ask(prompt, stream=True)

    plan = [
        f"Generate documentation for {target}",
        f"Write to {output_file}",
    ]

    if show_plan(plan, "Documentation Plan"):
        executor.write_file(output_file, docs)
        console.print(f"\n[green]✓ Documentation saved to {output_file}[/green]")
    else:
        console.print("[yellow]Documentation not saved.[/yellow]")
