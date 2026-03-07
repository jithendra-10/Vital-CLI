"""doc.py — Vital Documentation Generator"""

import os
from rich.console import Console
from vital import ai_engine, context
from vital.executor import write_file
from vital.safety import show_plan

console = Console()


def run(path: str = ".", output: str = None):
    """Auto-generate documentation for your code."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Doc Generator[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if os.path.isfile(path):
        ctx            = context.get_file_context(path)
        target         = f"file '{os.path.basename(path)}'"
        default_output = path.replace(".py", "_docs.md").replace(".js", "_docs.md")
    else:
        console.print(f"  [#888888]Scanning {path}...[/]\n")
        ctx            = context.build_context(path)
        lang           = context.detect_language(path)
        target         = f"project (language: {lang})"
        default_output = "README.md"

    output_file = output or default_output

    prompt = f"""Generate comprehensive, well-structured documentation for this {target}.

Use this format:

# Project/File Name

## Overview
What this does in plain English.

## Installation
How to install and set up (if applicable).

## Usage
How to use it with clear examples.

## API Reference / Functions
Each function/class with:
- Purpose
- Parameters and types
- Return value
- Example usage

## Examples
Real, runnable usage examples.

Code to document:
{ctx[:5000]}
"""

    console.print(f"  [#888888]Generating docs for {target}...[/]\n")

    try:
        docs = ai_engine.ask(prompt, stream=True)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    if show_plan([
        f"Generate documentation for {target}",
        f"Write to {output_file}",
    ], title="Save Documentation"):
        write_file(output_file, docs)
        console.print(
            f"\n  [bold #00ffcc]✓ Documentation saved to[/] "
            f"[#ffdd57]{output_file}[/]\n"
        )
    else:
        console.print("  [#888888]Documentation not saved.[/]\n")