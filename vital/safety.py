from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def show_plan(steps: list[str], title: str = "Action Plan") -> bool:
    """
    Show a plan to the user and ask for approval.
    Returns True if approved, False if rejected.
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Action", style="white")

    for i, step in enumerate(steps, 1):
        table.add_row(f"[{i}]", step)

    console.print()
    console.print(Panel(table, title=f"[bold yellow]{title}[/bold yellow]", border_style="yellow"))

    return Confirm.ask("\n[yellow]Approve and execute?[/yellow]", default=False)


def show_diff(original: str, modified: str, filepath: str):
    """Show a before/after diff of file changes."""
    console.print(f"\n[bold]Changes to:[/bold] [cyan]{filepath}[/cyan]")

    console.print("\n[red]--- Before ---[/red]")
    syntax = Syntax(original[:2000], "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    console.print("\n[green]+++ After ---[/green]")
    syntax = Syntax(modified[:2000], "python", theme="monokai", line_numbers=True)
    console.print(syntax)


def confirm_file_write(filepath: str, content: str) -> bool:
    """Ask user before writing to a file."""
    console.print(f"\n[yellow]About to write to:[/yellow] [cyan]{filepath}[/cyan]")
    console.print(f"[dim]({len(content)} characters)[/dim]")
    return Confirm.ask("[yellow]Confirm?[/yellow]", default=False)


def confirm_command(command: str) -> bool:
    """Ask user before running a shell command."""
    console.print(f"\n[yellow]About to run:[/yellow] [bold red]{command}[/bold red]")
    return Confirm.ask("[yellow]Confirm?[/yellow]", default=False)
