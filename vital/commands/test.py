import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, context, executor
from vital.safety import show_plan

console = Console()


def run(
    file: str = typer.Argument(..., help="File to generate tests for"),
    output: str = typer.Option(None, "--output", "-o", help="Output test file"),
    framework: str = typer.Option("pytest", "--framework", "-f", help="Test framework (pytest/unittest)"),
):
    """Generate unit tests for your code using AI."""

    console.print(Panel("[bold cyan]Vital Test Generator[/bold cyan]", border_style="cyan"))

    file_context = context.get_file_context(file)

    # Default output file name
    import os
    basename = os.path.basename(file).replace(".py", "")
    output_file = output or f"test_{basename}.py"

    prompt = f"""
Generate comprehensive {framework} unit tests for this code.

Requirements:
- Test all public functions and methods
- Include edge cases and error cases
- Use descriptive test names
- Add docstrings explaining what each test checks
- Mock external dependencies
- Aim for high coverage

Return ONLY the test file content. No explanation.

Code to test:
{file_context}
"""

    console.print(f"\n[bold yellow]Generating {framework} tests for {file}...[/bold yellow]\n")
    tests = ai_engine.ask(prompt, stream=True)

    plan = [
        f"Generate {framework} tests for {file}",
        f"Write tests to {output_file}",
    ]

    if show_plan(plan, "Test Generation Plan"):
        executor.write_file(output_file, tests)
        console.print(f"\n[green]✓ Tests written to {output_file}[/green]")
        console.print(f"[dim]Run with: pytest {output_file}[/dim]")
    else:
        console.print("[yellow]Test generation cancelled.[/yellow]")
