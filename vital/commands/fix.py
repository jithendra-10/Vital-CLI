"""fix.py — Vital Fixer"""

import typer
from rich.console import Console
from vital import ai_engine, context
from vital.executor import write_file, read_file
from vital.safety import show_plan, show_diff

console = Console()


def run(file: str = None, issue: str = None):
    """Fix issues in a file using AI."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Fixer[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if not file:
        console.print("  [#ff6b6b]Usage: vital fix <filename>[/]\n")
        return

    original = read_file(file)
    if not original:
        console.print(f"  [#ff6b6b]Could not read {file}[/]\n")
        return

    file_context = context.get_file_context(file)

    if not issue:
        try:
            issue = console.input(
                "  [#ffdd57]What needs to be fixed?[/] "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return

    if not issue:
        console.print("  [#888888]No issue described.[/]\n")
        return

    prompt = f"""Fix the following issue in this code file.
Return ONLY the complete fixed file content.
No explanation, no markdown fences — just the raw fixed code.

Issue to fix: {issue}

File ({file}):
{file_context}
"""

    console.print(f"\n  [#888888]Generating fix for [#ffdd57]{file}[/]...[/]\n")

    try:
        fixed_code = ai_engine.ask(prompt, stream=False)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    # Show diff so user knows what changed
    show_diff(original, fixed_code, file)

    if show_plan([
        f"Backup {file} → {file}.bak",
        f"Fix: {issue}",
        f"Write fixed version to {file}",
    ], title="Apply Fix"):
        write_file(f"{file}.bak", original)
        write_file(file, fixed_code)
        console.print(
            "\n  [bold #00ffcc]✓ Fix applied![/] "
            f"[#888888]Original backed up to {file}.bak[/]\n"
        )
    else:
        console.print("  [#888888]Fix cancelled.[/]\n")