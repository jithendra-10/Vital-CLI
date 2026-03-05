import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context

console = Console()


def run(
    path: str = typer.Argument(".", help="File or folder to explain"),
    simple: bool = typer.Option(False, "--simple", "-s", help="Explain in simple terms for beginners"),
):
    """Explain a file or entire codebase in plain English."""

    console.print(Panel("[bold cyan]Vital Explainer[/bold cyan]", border_style="cyan"))

    import os
    if os.path.isfile(path):
        ctx = context.get_file_context(path)
        target = f"file '{path}'"
    else:
        console.print(f"\n[dim]Scanning {path}...[/dim]")
        ctx = context.build_context(path)
        lang = context.detect_language(path)
        target = f"project (main language: {lang})"

    level = "a complete beginner" if simple else "an experienced developer"

    prompt = f"""
Explain this {target} to {level}. Cover:
1. What this code does overall
2. How the main parts work together
3. Key functions/classes and their purpose
4. Any patterns or architecture used

{ctx}
"""

    console.print(f"\n[bold yellow]Explaining {target}...[/bold yellow]\n")
    ai_engine.ask(prompt, system="You are a patient senior developer explaining code clearly.")
