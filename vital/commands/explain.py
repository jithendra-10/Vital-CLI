"""explain.py — Vital Explainer"""

import os
from rich.console import Console
from vital import ai_engine, context

console = Console()


def run(path: str = ".", simple: bool = False):
    """Explain a file or entire codebase in plain English."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Explainer[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if os.path.isfile(path):
        ctx    = context.get_file_context(path)
        target = f"file '{os.path.basename(path)}'"
    else:
        console.print(f"  [#888888]Scanning {path}...[/]\n")
        ctx    = context.build_context(path)
        lang   = context.detect_language(path)
        target = f"project (language: {lang})"

    level = "a complete beginner with no coding experience" if simple else "an experienced developer"

    prompt = f"""Explain this {target} to {level}. Cover:
1. What this code does overall
2. How the main parts work together
3. Key functions/classes and their purpose
4. Any patterns or architecture used
5. What someone would need to know to modify it

{ctx[:5000]}
"""

    console.print(f"  [#888888]Explaining {target}...[/]\n")

    try:
        ai_engine.ask(prompt)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")