"""
patch.py — Vital's Minimal Patch Engine

Computes and applies minimal diffs instead of full file rewrites.
Shows confidence + blast radius before the user commits to anything.
"""

import re
import difflib
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

console = Console()


@dataclass
class BlastRadius:
    lines_added:       int
    lines_removed:     int
    lines_changed:     int
    hunks:             int
    functions_touched: list[str] = field(default_factory=list)
    confidence:        str = "HIGH"       # HIGH / MEDIUM / LOW
    confidence_color:  str = "#00ff88"
    reason:            str = ""


def analyze_blast_radius(filepath: str, original: str, updated: str) -> BlastRadius:
    """Compute change scope and assign a confidence tier."""
    orig_lines = original.splitlines()
    new_lines  = updated.splitlines()

    diff = list(difflib.unified_diff(orig_lines, new_lines, lineterm=""))

    lines_added   = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    lines_removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    lines_changed = max(lines_added, lines_removed)
    hunks         = sum(1 for l in diff if l.startswith("@@"))

    # Detect functions/classes touched (Python only)
    functions_touched: list[str] = []
    if filepath.endswith(".py"):
        sm = difflib.SequenceMatcher(None, orig_lines, new_lines, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            # Walk backwards from the changed region to find enclosing def/class
            for i in range(min(i1, len(orig_lines) - 1), -1, -1):
                m = re.match(r"^(def |class |async def )(\w+)", orig_lines[i])
                if m:
                    name = m.group(2)
                    if name not in functions_touched:
                        functions_touched.append(name)
                    break

    # Confidence
    total = len(orig_lines) or 1
    pct   = lines_changed / total

    if lines_changed == 0:
        confidence, color = "HIGH",   "#00ff88"
        reason = "No changes"
    elif pct < 0.15 and lines_changed <= 30:
        confidence, color = "HIGH",   "#00ff88"
        reason = f"Local change ({lines_changed} lines, {pct:.0%} of file)"
    elif pct < 0.40 and lines_changed <= 80:
        confidence, color = "MEDIUM", "#ffdd57"
        reason = f"Moderate change ({lines_changed} lines, {pct:.0%} of file)"
    else:
        confidence, color = "LOW",    "#ff6b6b"
        reason = f"Large change ({lines_changed} lines, {pct:.0%} of file)"

    return BlastRadius(
        lines_added       = lines_added,
        lines_removed     = lines_removed,
        lines_changed     = lines_changed,
        hunks             = hunks,
        functions_touched = functions_touched,
        confidence        = confidence,
        confidence_color  = color,
        reason            = reason,
    )


def show_patch_preview(original: str, updated: str, filepath: str, blast: BlastRadius):
    """Render a coloured diff preview with confidence + blast-radius banner."""
    orig_lines = original.splitlines(keepends=True)
    new_lines  = updated.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        orig_lines, new_lines,
        fromfile=f"original/{filepath}",
        tofile=f"updated/{filepath}",
        n=3,
    ))

    if not diff:
        console.print("  [#888888]No changes detected.[/]\n")
        return

    MAX_LINES = 80
    display   = diff[:MAX_LINES]
    hidden    = len(diff) - len(display)

    diff_text = "".join(display)
    if hidden > 0:
        diff_text += f"\n... ({hidden} more diff lines not shown)"

    console.print()
    console.print(f"  [bold #ffdd57]◈ Patch Preview — {filepath}[/]")
    console.print("  [#333355]" + "─" * 55 + "[/]\n")

    try:
        console.print(Syntax(diff_text, "diff", theme="monokai", word_wrap=True))
    except Exception:
        console.print(f"  {diff_text}")

    console.print()

    # Stats
    console.print(
        f"  [bold #00ff88]+{blast.lines_added} added[/]   "
        f"[bold #ff6b6b]-{blast.lines_removed} removed[/]   "
        f"[#888888]~{blast.lines_changed} lines changed   "
        f"{blast.hunks} hunk{'s' if blast.hunks != 1 else ''}[/]"
    )

    # Confidence
    console.print(
        f"\n  Confidence:   [bold {blast.confidence_color}]{blast.confidence}[/]  "
        f"[#888888]{blast.reason}[/]"
    )

    # Blast radius
    radius_parts = ["1 file", f"{blast.lines_changed} lines"]
    if blast.functions_touched:
        fns = ", ".join(blast.functions_touched[:3])
        if len(blast.functions_touched) > 3:
            fns += f" (+{len(blast.functions_touched) - 3} more)"
        radius_parts.append(f"touches: {fns}")

    console.print(
        f"  Blast radius: [#444466]{', '.join(radius_parts)}[/]\n"
    )


def apply_patch(filepath: str, updated: str) -> bool:
    """Write the patched content to disk."""
    try:
        Path(filepath).write_text(updated, encoding="utf-8")
        return True
    except Exception as e:
        console.print(f"  [#ff6b6b]Error applying patch: {e}[/]")
        return False
