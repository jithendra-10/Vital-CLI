"""refactor.py — Vital Refactorer (patch mode)"""

import re
from rich.console import Console
from vital import ai_engine, context
from vital.executor import read_file
from vital.patch import analyze_blast_radius, show_patch_preview, apply_patch
from vital.rollback import save_checkpoint, restore_last
from vital.verify import verify_code, show_verify_error

console = Console()


def run(file: str = None, goal: str = None):
    """Refactor code — shows minimal diff with confidence before applying."""

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

    # Strip accidental code fences
    refactored = re.sub(r'^```\w*\n?', '', refactored.strip())
    refactored = re.sub(r'\n?```$', '', refactored.strip())

    if refactored.strip() == original.strip():
        console.print("  [#888888]AI found nothing to change.[/]\n")
        return

    # ── Verify syntax before touching disk ───────────────────────────
    result = verify_code(file, refactored)
    if not result.passed:
        show_verify_error(result)
        return

    # ── Patch preview with confidence + blast radius ──────────────────
    blast = analyze_blast_radius(file, original, refactored)
    show_patch_preview(original, refactored, file, blast)

    console.print(
        "  [bold #00ffcc][A][/] Apply patch  "
        "[bold #ff6b6b][R][/] Reject  "
        "[bold #ffdd57][U][/] Undo last change"
    )
    console.print()

    try:
        choice = console.input("  Your choice (A/R/U): ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        return

    if choice == "U":
        restore_last(file)
        return

    if choice == "R":
        console.print("  [#ff6b6b]✗ Refactoring rejected.[/]\n")
        return

    if choice == "A":
        save_checkpoint(file, original, description=f"refactor: {goal[:60]}")
        if apply_patch(file, refactored):
            console.print(
                f"\n  [bold #00ffcc]✓ Refactoring applied![/] "
                f"[#888888]({blast.lines_changed} lines changed · "
                f"undo with: vital undo)[/]\n"
            )
        else:
            console.print("  [#ff6b6b]✗ Failed to write patch.[/]\n")