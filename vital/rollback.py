"""
rollback.py — Vital's Undo / Rollback System

Saves a checkpoint before every AI-driven file write.
Supports: `vital undo`, `/undo` in interactive mode.

Storage:
  ~/.vital/backups/<checkpoint-id>.bak   — raw file content
  ~/.vital/undo_stack.json               — ordered undo history
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

VITAL_DIR   = Path.home() / ".vital"
BACKUPS_DIR = VITAL_DIR / "backups"
UNDO_STACK  = VITAL_DIR / "undo_stack.json"
MAX_UNDO    = 50


def _ensure_dirs():
    VITAL_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)


# ── Public API ────────────────────────────────────────────────────────────────

def save_checkpoint(filepath: str, content: str, description: str = "") -> str:
    """
    Snapshot a file's content before modifying it.
    Returns the checkpoint ID.
    """
    _ensure_dirs()

    content_hash  = hashlib.sha256(content.encode()).hexdigest()[:12]
    checkpoint_id = f"{int(time.time())}_{content_hash}"

    backup_path = BACKUPS_DIR / f"{checkpoint_id}.bak"
    backup_path.write_text(content, encoding="utf-8")

    stack = _load_stack()
    stack.insert(0, {
        "id":          checkpoint_id,
        "filepath":    str(Path(filepath).resolve()),
        "description": description,
        "backup_path": str(backup_path),
        "timestamp":   datetime.now().isoformat(),
    })

    # Trim + clean old backups
    if len(stack) > MAX_UNDO:
        for old in stack[MAX_UNDO:]:
            try:
                Path(old["backup_path"]).unlink(missing_ok=True)
            except Exception:
                pass
        stack = stack[:MAX_UNDO]

    _save_stack(stack)
    return checkpoint_id


def restore_last(filepath: str = None) -> bool:
    """
    Restore the last-modified file (or a specific file) to its pre-change state.
    Returns True if restored successfully.
    """
    _ensure_dirs()
    stack = _load_stack()

    if not stack:
        console.print("\n  [#888888]Nothing to undo — undo stack is empty.[/]\n")
        return False

    # Find the relevant entry
    target_idx = None
    if filepath:
        abs_path = str(Path(filepath).resolve())
        for i, entry in enumerate(stack):
            if entry["filepath"] == abs_path:
                target_idx = i
                break
        if target_idx is None:
            console.print(
                f"\n  [#888888]No undo history for [#ffdd57]{filepath}[/].[/]\n"
            )
            return False
    else:
        target_idx = 0

    entry       = stack[target_idx]
    backup_path = Path(entry["backup_path"])

    if not backup_path.exists():
        console.print("  [#ff6b6b]Backup file missing — cannot undo.[/]\n")
        stack.pop(target_idx)
        _save_stack(stack)
        return False

    try:
        original = backup_path.read_text(encoding="utf-8")
        Path(entry["filepath"]).write_text(original, encoding="utf-8")
    except Exception as e:
        console.print(f"  [#ff6b6b]Restore failed: {e}[/]\n")
        return False

    # Remove from stack + clean up backup
    stack.pop(target_idx)
    _save_stack(stack)
    try:
        backup_path.unlink()
    except Exception:
        pass

    fname = Path(entry["filepath"]).name
    desc  = entry.get("description", "")
    ts    = entry.get("timestamp", "")[:16].replace("T", " ")

    console.print(
        f"\n  [bold #00ffcc]✓ Undone:[/] [#ffdd57]{fname}[/] "
        f"[#888888]restored to pre-change state[/]\n"
        + (f"  [#444444]Was: {desc}  ({ts})[/]\n" if desc else "")
    )
    return True


def list_undo_history(limit: int = 10):
    """Print the undo history table."""
    stack = _load_stack()

    if not stack:
        console.print("\n  [#888888]Undo history is empty.[/]\n")
        return

    console.print()
    console.print("  [bold #00ffcc]◈ Undo History[/]")
    console.print("  [#333355]" + "─" * 55 + "[/]\n")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold #00ffcc")
    table.add_column("#",           style="#444466", width=3)
    table.add_column("File",        style="#ffdd57", width=22)
    table.add_column("Description", style="#aaaaaa")
    table.add_column("When",        style="#888888", width=18)

    for i, entry in enumerate(stack[:limit], 1):
        fname = Path(entry["filepath"]).name
        desc  = entry.get("description", "")[:45]
        ts    = entry.get("timestamp", "")[:16].replace("T", " ")
        table.add_row(str(i), fname, desc, ts)

    console.print(table)
    console.print(
        "  [#444444]Use [bold]vital undo[/bold] or "
        "[bold]/undo[/bold] to restore the last change.[/]\n"
    )


def get_last_entry() -> dict | None:
    """Peek at the top of the undo stack without restoring."""
    stack = _load_stack()
    return stack[0] if stack else None


# ── Internal ──────────────────────────────────────────────────────────────────

def _load_stack() -> list:
    _ensure_dirs()
    if not UNDO_STACK.exists():
        return []
    try:
        return json.loads(UNDO_STACK.read_text())
    except Exception:
        return []


def _save_stack(stack: list):
    UNDO_STACK.write_text(json.dumps(stack, indent=2))
