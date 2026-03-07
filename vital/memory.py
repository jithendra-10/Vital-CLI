"""
memory.py — Vital's Persistent Memory Manager
Discovers and manages VITAL.md files hierarchically.
Global memory: ~/.vital/VITAL.md
Project memory: <project_root>/VITAL.md
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.syntax import Syntax
from rich.prompt import Confirm

console = Console()

# ── Paths ─────────────────────────────────────────────────────────────────────
VITAL_DIR     = Path.home() / ".vital"
GLOBAL_MEMORY = VITAL_DIR / "VITAL.md"
MEMORY_FILE   = "VITAL.md"


def _ensure_dirs():
    VITAL_DIR.mkdir(exist_ok=True)


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover_memory_files(start_dir: str = ".") -> list[Path]:
    """
    Walk UP from start_dir looking for VITAL.md files.
    Returns list of found files from global → project order.
    (Global loaded first, project-specific overrides last)
    """
    found   = []
    current = Path(start_dir).resolve()
    home    = Path.home()

    # Walk up directory tree
    while True:
        candidate = current / MEMORY_FILE
        if candidate.exists():
            found.append(candidate)

        # Stop at home directory
        if current == home or current == current.parent:
            break
        current = current.parent

    # Reverse so global comes first, project-specific last
    found.reverse()

    # Always include global memory if it exists
    if GLOBAL_MEMORY.exists() and GLOBAL_MEMORY not in found:
        found.insert(0, GLOBAL_MEMORY)

    return found


def load_memory(start_dir: str = ".") -> str:
    """
    Load and concatenate all VITAL.md files found.
    Returns combined memory string to inject into AI prompts.
    """
    _ensure_dirs()
    files = discover_memory_files(start_dir)

    if not files:
        return ""

    parts = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8").strip()
            if content:
                label = "Global Memory" if f == GLOBAL_MEMORY else f"Project Memory ({f.parent.name})"
                parts.append(f"### {label}\n{content}")
        except Exception:
            continue

    return "\n\n".join(parts)


def get_project_memory_path(start_dir: str = ".") -> Path:
    """Get path where project VITAL.md should be created."""
    return Path(start_dir).resolve() / MEMORY_FILE


# ── Memory commands ────────────────────────────────────────────────────────────

def memory_show(start_dir: str = "."):
    """Show all loaded memory files and their content."""
    files = discover_memory_files(start_dir)

    if not files:
        console.print(
            "\n  [#888888]No VITAL.md memory files found.[/]\n"
            "  [#444444]Create one with: /memory add \"your rule\"[/]\n"
        )
        return

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Memory[/]")
    console.print("  [#333355]" + "─" * 50 + "[/]\n")

    for f in files:
        label = "🌐 Global" if f == GLOBAL_MEMORY else f"📁 Project ({f.parent.name})"
        console.print(f"  [bold #ffdd57]{label}[/]  [#444444]{f}[/]\n")

        try:
            content = f.read_text(encoding="utf-8").strip()
            if content:
                syntax = Syntax(
                    content, "markdown",
                    theme="monokai",
                    word_wrap=True
                )
                console.print(syntax)
            else:
                console.print("  [#444444](empty)[/]")
        except Exception as e:
            console.print(f"  [#ff6b6b]Could not read: {e}[/]")
        console.print()


def memory_add(fact: str, global_mem: bool = False, start_dir: str = "."):
    """
    Add a fact/rule to memory.
    global_mem=True  → saves to ~/.vital/VITAL.md
    global_mem=False → saves to project VITAL.md
    """
    _ensure_dirs()

    if global_mem:
        filepath = GLOBAL_MEMORY
        label    = "global memory"
    else:
        filepath = get_project_memory_path(start_dir)
        label    = f"project memory ({filepath.parent.name})"

    # Create file if it doesn't exist
    if not filepath.exists():
        filepath.write_text(
            f"# Vital Memory\n"
            f"# Created: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"# This file is automatically loaded by Vital as context.\n\n"
        )

    # Append the fact under ## Vital Added Memories section
    current = filepath.read_text(encoding="utf-8")

    section = "## Vital Added Memories"
    entry   = f"- {fact}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if section in current:
        # Append to existing section
        current += f"\n{entry}  <!-- {timestamp} -->"
    else:
        # Create new section
        current += f"\n\n{section}\n{entry}  <!-- {timestamp} -->"

    filepath.write_text(current, encoding="utf-8")
    console.print(
        f"\n  [bold #00ffcc]✓ Added to {label}:[/] [#ffdd57]{fact}[/]\n"
    )


def memory_refresh(start_dir: str = ".") -> str:
    """Reload all memory files — use after manual edits."""
    memory = load_memory(start_dir)
    files  = discover_memory_files(start_dir)
    console.print(
        f"\n  [bold #00ffcc]✓ Memory refreshed[/] — "
        f"[#888888]{len(files)} file(s) loaded[/]\n"
    )
    return memory


def memory_edit(global_mem: bool = False, start_dir: str = "."):
    """Open memory file in nano for manual editing."""
    if global_mem:
        filepath = GLOBAL_MEMORY
    else:
        filepath = get_project_memory_path(start_dir)

    # Create if doesn't exist
    if not filepath.exists():
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            f"# Vital Project Memory\n"
            f"# Add your project rules, preferences, and context here.\n"
            f"# This file is automatically loaded by Vital.\n\n"
            f"## Project Info\n"
            f"# Example: This is a Flask REST API project.\n\n"
            f"## Coding Rules\n"
            f"# Example: Always use type hints in Python.\n\n"
        )

    console.print(
        f"\n  [#888888]Opening:[/] [#ffdd57]{filepath}[/]\n"
    )
    os.system(f"nano {filepath}")


def memory_clear(global_mem: bool = False, start_dir: str = "."):
    """Clear a memory file after confirmation."""
    if global_mem:
        filepath = GLOBAL_MEMORY
        label    = "global memory"
    else:
        filepath = get_project_memory_path(start_dir)
        label    = "project memory"

    if not filepath.exists():
        console.print(f"\n  [#888888]No {label} file found.[/]\n")
        return

    if Confirm.ask(f"\n  [#ff6b6b]Clear {label}?[/]", default=False):
        filepath.write_text(
            f"# Vital Memory\n# Cleared: {datetime.now().strftime('%Y-%m-%d')}\n"
        )
        console.print(f"  [#00ffcc]✓ {label.capitalize()} cleared.[/]\n")


def init_project_memory(start_dir: str = "."):
    """
    Create a VITAL.md in the current project directory
    with smart defaults based on detected language.
    """
    filepath = get_project_memory_path(start_dir)

    if filepath.exists():
        console.print(
            f"\n  [#ffdd57]VITAL.md already exists in this project.[/]\n"
            f"  Use [bold]/memory edit[/bold] to modify it.\n"
        )
        return

    # Try to detect project type
    cwd = Path(start_dir).resolve()
    project_type = "unknown"
    stack_hints  = []

    if (cwd / "package.json").exists():
        project_type = "JavaScript/Node.js"
        stack_hints  = ["Use modern ES6+ syntax", "Prefer async/await over callbacks"]
    elif (cwd / "requirements.txt").exists() or (cwd / "pyproject.toml").exists():
        project_type = "Python"
        stack_hints  = ["Use type hints", "Follow PEP 8 style guide"]
    elif (cwd / "pom.xml").exists() or list(cwd.glob("*.java")):
        project_type = "Java"
        stack_hints  = ["Follow Java naming conventions", "Use JavaDoc for documentation"]
    elif (cwd / "go.mod").exists():
        project_type = "Go"
        stack_hints  = ["Follow Go idioms", "Use error wrapping"]

    hints_text = "\n".join(f"- {h}" for h in stack_hints)

    content = f"""# Vital Project Memory
# Project: {cwd.name}
# Created: {datetime.now().strftime('%Y-%m-%d')}
# This file is automatically loaded by Vital in every session.

## Project Info
- Project type: {project_type}
- Directory: {cwd}

## Coding Rules
{hints_text if hints_text else "- Add your coding preferences here"}

## Tech Stack
- Add your frameworks, libraries, versions here

## Notes
- Add any important project context here
"""

    filepath.write_text(content, encoding="utf-8")
    console.print(
        f"\n  [bold #00ffcc]✓ Created VITAL.md[/] in [#ffdd57]{cwd}[/]\n"
        f"  [#888888]Edit it with: /memory edit[/]\n"
    )
