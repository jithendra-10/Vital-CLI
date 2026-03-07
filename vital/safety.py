"""
safety.py — Vital's Safety & Confirmation Utilities
Provides confirmation prompts, plan display, and diff viewing.

Used by:
  - executor.py  → confirm_file_write, confirm_command
  - commands/*   → show_plan, show_diff
"""

import difflib
from rich.console import Console
from rich.syntax import Syntax

console = Console()


# ── Used by executor.py ───────────────────────────────────────────────────────

def confirm_command(command: str) -> bool:
    """
    Ask user to confirm before running a shell command.
    Returns True if confirmed, False if cancelled.
    """
    console.print(
        f"\n  [bold #ffdd57]⚠ Run command:[/] [#444466]{command}[/]"
    )
    try:
        choice = console.input(
            "  [bold #00ffcc][Y][/] Run  [bold #ff6b6b][N][/] Cancel: "
        ).strip().upper()
        return choice == "Y"
    except (KeyboardInterrupt, EOFError):
        return False


def confirm_file_write(filepath: str, content: str) -> bool:
    """
    Ask user to confirm before writing a file.
    Shows filename and size before asking.
    Returns True if confirmed, False if cancelled.
    """
    size = len(content.encode("utf-8"))
    console.print(
        f"\n  [bold #ffdd57]⚠ Write file:[/] [#ffdd57]{filepath}[/] "
        f"[#888888]({size} bytes)[/]"
    )
    try:
        choice = console.input(
            "  [bold #00ffcc][Y][/] Write  [bold #ff6b6b][N][/] Cancel: "
        ).strip().upper()
        return choice == "Y"
    except (KeyboardInterrupt, EOFError):
        return False


# ── Used by commands/*.py ─────────────────────────────────────────────────────

def show_plan(steps: list[str], title: str = "Plan") -> bool:
    """
    Show a list of planned steps and ask user to confirm.
    Returns True if confirmed, False if cancelled.
    """
    console.print()
    console.print(f"  [bold #ffdd57]◈ {title}[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    for i, step in enumerate(steps, 1):
        console.print(f"  [#444466][{i}][/] [#aaaaaa]{step}[/]")

    console.print()
    console.print(
        "  [bold #00ffcc][Y][/] Proceed  "
        "[bold #ff6b6b][N][/] Cancel"
    )
    console.print()

    try:
        choice = console.input("  Your choice (Y/N): ").strip().upper()
        return choice == "Y"
    except (KeyboardInterrupt, EOFError):
        return False


def show_diff(original: str, updated: str, filename: str = "file"):
    """
    Show a colored unified diff between original and updated content.
    """
    original_lines = original.splitlines(keepends=True)
    updated_lines  = updated.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        updated_lines,
        fromfile=f"original/{filename}",
        tofile=f"updated/{filename}",
        n=3
    ))

    if not diff:
        console.print("  [#888888]No changes detected.[/]\n")
        return

    added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

    console.print()
    console.print(
        f"  [bold #ffdd57]◈ Changes in {filename}[/]  "
        f"[bold #00ff88]+{added} lines added[/]  "
        f"[bold #ff6b6b]-{removed} lines removed[/]\n"
    )

    diff_text = "".join(diff[:60])
    if len(diff) > 60:
        diff_text += f"\n... ({len(diff) - 60} more lines)"

    try:
        syntax = Syntax(diff_text, "diff", theme="monokai", word_wrap=True)
        console.print(syntax)
    except Exception:
        console.print(f"  [#888888]{diff_text}[/]")
    console.print()