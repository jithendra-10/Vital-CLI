import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, executor
from vital.safety import show_plan

console = Console()


def run(
    push: bool = typer.Option(False, "--push", "-p", help="Push after committing"),
):
    """Auto-generate a git commit message based on your changes."""

    console.print(Panel("[bold cyan]Vital Git Commit[/bold cyan]", border_style="cyan"))

    # Get git diff
    stdout, stderr, code = executor.run_silent("git diff --staged")

    if not stdout:
        # Try unstaged changes
        stdout, stderr, code = executor.run_silent("git diff")

    if not stdout:
        console.print("[yellow]No changes detected. Stage your files with 'git add' first.[/yellow]")
        raise typer.Exit()

    prompt = f"""
Generate a clear, concise git commit message for these changes.
Follow conventional commits format: type(scope): description

Types: feat, fix, docs, style, refactor, test, chore

Return ONLY the commit message, nothing else.

Git diff:
{stdout[:5000]}
"""

    console.print("\n[bold yellow]Generating commit message...[/bold yellow]\n")
    commit_msg = ai_engine.ask(prompt, stream=False)
    commit_msg = commit_msg.strip().strip('"').strip("'")

    console.print(f"\n[bold green]Suggested commit:[/bold green]")
    console.print(f"[cyan]{commit_msg}[/cyan]")

    edit = typer.confirm("\nEdit the message?", default=False)
    if edit:
        commit_msg = typer.prompt("Enter commit message", default=commit_msg)

    plan = ["git add -A (if not already staged)", f'git commit -m "{commit_msg}"']
    if push:
        plan.append("git push")

    if show_plan(plan, "Commit Plan"):
        executor.run_command("git add -A", auto_approve=True)
        executor.run_command(f'git commit -m "{commit_msg}"', auto_approve=True)
        if push:
            executor.run_command("git push", auto_approve=True)
        console.print("\n[green]✓ Committed![/green]")
    else:
        console.print("[yellow]Commit cancelled.[/yellow]")
