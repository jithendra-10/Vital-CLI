"""refactor.py — Vital Refactorer"""

from rich.console import Console
from vital import ai_engine, context
from vital.executor import write_file, read_file
from vital.safety import show_plan, show_diff

console = Console()


def run(file: str = None, goal: str = None):
    """Refactor and improve code quality using AI."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Refactorer[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if not file:
        console.print("  [#ff6b6b]Usage: vital refactor <filename>[/]\n")
        return

    original = read_file(file)
    if not original:
        console.print(f"  [#ff6b6b]Could not read {file}[/]\n")
        return

    file_context = context.get_file_context(file)

    if not goal:
        try:
            goal = console.input(
                "  [#ffdd57]Refactoring goal[/] "
                "[#888888](Enter for default):[/] "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return
        if not goal:
            goal = "Improve readability, structure, and follow best practices"

    prompt = f"""Refactor this code file with this goal: {goal}

Improvements to make:
- Better variable and function names
- Remove code duplication (DRY principle)
- Improve structure and readability
- Add type hints if Python
- Follow language best practices
- Optimize where obviously beneficial
- Add brief docstrings to functions

Return ONLY the complete refactored file content.
No explanation, no markdown fences — just the improved code.

Original file ({file}):
{file_context}
"""

    console.print(f"  [#888888]Refactoring [#ffdd57]{file}[/]...[/]\n")

    try:
        refactored = ai_engine.ask(prompt, stream=False)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    # Show diff
    show_diff(original, refactored, file)

    if show_plan([
        f"Backup original → {file}.bak",
        f"Goal: {goal}",
        f"Write refactored version to {file}",
    ], title="Refactor Plan"):
        write_file(f"{file}.bak", original)
        write_file(file, refactored)
        console.print(
            f"\n  [bold #00ffcc]✓ Refactored![/] "
            f"[#888888]Original backed up to {file}.bak[/]\n"
        )
    else:
        console.print("  [#888888]Refactoring cancelled.[/]\n")