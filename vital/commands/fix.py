import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context, executor
from vital.safety import show_plan

console = Console()


def run(
    file: str = typer.Argument(..., help="File to fix"),
    issue: str = typer.Option(None, "--issue", "-i", help="Describe what needs fixing"),
):
    """Fix issues in a file using AI."""

    console.print(Panel("[bold cyan]Vital Fixer[/bold cyan]", border_style="cyan"))

    file_context = context.get_file_context(file)

    if not issue:
        issue = typer.prompt("\nWhat needs to be fixed?")

    prompt = f"""
Fix the following issue in this code file.
Return ONLY the complete fixed file content. No explanation, no markdown, just the code.

Issue to fix: {issue}

File: {file_context}
"""

    console.print(f"\n[bold yellow]Generating fix for {file}...[/bold yellow]\n")
    fixed_code = ai_engine.ask(prompt, stream=True)

    plan = [
        f"Read current {file}",
        f"Fix: {issue}",
        f"Write fixed version to {file}",
    ]

    if show_plan(plan, "Fix Plan"):
        executor.write_file(file, fixed_code)
        console.print("\n[green]✓ Fix applied![/green]")
    else:
        console.print("[yellow]Fix cancelled.[/yellow]")
