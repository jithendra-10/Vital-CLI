import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context, executor
from vital.safety import show_plan, show_diff

console = Console()


def run(
    file: str = typer.Argument(..., help="File to refactor"),
    goal: str = typer.Option(None, "--goal", "-g", help="Refactoring goal"),
):
    """Refactor and improve your code quality using AI."""

    console.print(Panel("[bold cyan]Vital Refactorer[/bold cyan]", border_style="cyan"))

    original = context.get_file_context(file)
    original_content = executor.read_file(file)

    if not goal:
        goal = typer.prompt("\nWhat's your refactoring goal?",
                            default="Improve readability, structure, and follow best practices")

    prompt = f"""
Refactor this code file with this goal: {goal}

Improvements to make:
- Better variable/function names
- Remove code duplication
- Improve structure and readability
- Add type hints if Python
- Follow best practices for the language
- Optimize where obvious

Return ONLY the complete refactored file. No explanation, just the improved code.

Original file:
{original}
"""

    console.print(f"\n[bold yellow]Refactoring {file}...[/bold yellow]\n")
    refactored = ai_engine.ask(prompt, stream=False)

    # Show diff
    if original_content:
        show_diff(original_content, refactored, file)

    plan = [
        f"Backup original {file} to {file}.bak",
        f"Write refactored version to {file}",
    ]

    if show_plan(plan, "Refactor Plan"):
        # Backup original
        executor.write_file(f"{file}.bak", original_content or "", auto_approve=True)
        # Write refactored
        executor.write_file(file, refactored)
        console.print(f"\n[green]✓ Refactored! Original backed up to {file}.bak[/green]")
    else:
        console.print("[yellow]Refactoring cancelled.[/yellow]")
