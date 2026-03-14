"""fix.py — Vital Fixer (patch mode)"""

import re
from rich.console import Console
from vital import ai_engine, context
from vital.executor import read_file
from vital.patch import analyze_blast_radius, show_patch_preview, apply_patch
from vital.rollback import save_checkpoint, restore_last
from vital.verify import verify_code, show_verify_error

console = Console()


def run(file: str = None, issue: str = None):
    """Fix issues in a file — shows minimal diff with confidence before applying."""

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

    # Strip accidental code fences
    fixed_code = re.sub(r'^```\w*\n?', '', fixed_code.strip())
    fixed_code = re.sub(r'\n?```$', '', fixed_code.strip())

    if fixed_code.strip() == original.strip():
        console.print("  [#888888]AI found nothing to change.[/]\n")
        return

    # ── Verify syntax before touching disk ───────────────────────────
    result = verify_code(file, fixed_code)
    if not result.passed:
        show_verify_error(result)
        return

    # ── Patch preview with confidence + blast radius ──────────────────
    blast = analyze_blast_radius(file, original, fixed_code)
    show_patch_preview(original, fixed_code, file, blast)

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
        console.print("  [#ff6b6b]✗ Patch rejected.[/]\n")
        return

    if choice == "A":
        save_checkpoint(file, original, description=f"fix: {issue[:60]}")
        if apply_patch(file, fixed_code):
            console.print(
                f"\n  [bold #00ffcc]✓ Patch applied![/] "
                f"[#888888]({blast.lines_changed} lines changed · "
                f"undo with: vital undo)[/]\n"
            )
        else:
            console.print("  [#ff6b6b]✗ Failed to write patch.[/]\n")