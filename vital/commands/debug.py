import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context, executor
from vital.safety import show_plan

console = Console()


def run(
    file: str = typer.Option(None, "--file", "-f", help="File to debug"),
    command: str = typer.Option(None, "--run", "-r", help="Command to run and capture errors"),
    error: str = typer.Option(None, "--error", "-e", help="Paste error message directly"),
):
    """Debug your code using AI. Analyzes errors and suggests fixes."""

    console.print(Panel("[bold cyan]Vital Debugger[/bold cyan]", border_style="cyan"))

    error_output = ""
    file_context = ""

    # Get error from running a command
    if command:
        console.print(f"\n[dim]Running:[/dim] {command}")
        error_output = executor.capture_error(command)
        console.print(f"[red]{error_output}[/red]")

    # Get error from direct paste
    elif error:
        error_output = error

    # No error provided
    else:
        error_output = typer.prompt("\nPaste your error message")

    # Get file context
    if file:
        file_context = context.get_file_context(file)
    else:
        console.print("\n[dim]Scanning project for context...[/dim]")
        file_context = context.build_context(".")

    # Build AI prompt
    prompt = f"""
You are an expert debugger. Analyze this error and provide:
1. What caused the error (in simple terms)
2. Exact fix with code
3. How to prevent it in future

Error:
{error_output}

Code Context:
{file_context}
"""

    console.print("\n[bold yellow]Analyzing error...[/bold yellow]\n")
    response = ai_engine.ask(prompt, system="You are an expert software debugger. Be concise and practical.")

    # If a file was provided, offer to apply the fix
    if file:
        console.print()
        apply = typer.confirm("\nWould you like me to apply the fix to your file?")
        if apply:
            fix_prompt = f"""
Based on this error and your analysis, provide ONLY the complete fixed version of the file.
No explanation, just the fixed code.

Error: {error_output}
Original file: {file_context}
"""
            fixed_code = ai_engine.ask(fix_prompt, stream=False)

            plan = [
                f"Read current {file}",
                "Apply AI-generated fix",
                f"Write fixed version to {file}",
            ]

            if show_plan(plan, title="Fix Plan"):
                executor.write_file(file, fixed_code)
                console.print("\n[green]✓ Fix applied! Run your code to verify.[/green]")
            else:
                console.print("[yellow]Fix not applied.[/yellow]")
