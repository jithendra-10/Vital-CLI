"""debug.py — Vital Debugger"""

import typer
from rich.console import Console
from vital import ai_engine, context
from vital.executor import capture_error, write_file, read_file
from vital.safety import show_plan

console = Console()


def run(file: str = None, command: str = None, error: str = None):
    """Debug your code — analyzes errors and suggests fixes."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Debugger[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    error_output = ""

    # Get error from running a command
    if command:
        console.print(f"  [#888888]Running:[/] [#444466]{command}[/]\n")
        error_output = capture_error(command)
        console.print(f"  [#ff6b6b]{error_output}[/]\n")

    # Get error from direct paste
    elif error:
        error_output = error

    # Ask for error
    else:
        try:
            error_output = console.input(
                "  [#ffdd57]Paste your error message:[/] "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            return

    if not error_output:
        console.print("  [#888888]No error provided.[/]\n")
        return

    # Get file context
    if file:
        file_context = context.get_file_context(file)
    else:
        console.print("  [#888888]Scanning project...[/]\n")
        file_context = context.build_context(".")

    prompt = f"""You are an expert debugger. Analyze this error and provide:
1. What caused the error (in simple terms)
2. The exact fix with code
3. How to prevent it in the future

Error:
{error_output}

Code Context:
{file_context[:4000]}
"""

    console.print("  [#888888]Analyzing error...[/]\n")

    try:
        response = ai_engine.ask(prompt)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ AI error: {e}[/]\n")
        return

    # Offer to apply fix if a file was provided
    if file:
        console.print()
        try:
            apply = typer.confirm("  Apply the fix to your file?", default=False)
        except Exception:
            return

        if apply:
            fix_prompt = f"""Based on this error, provide ONLY the complete fixed file content.
No explanation, no markdown fences — just the raw fixed code.

Error: {error_output}
Original file:
{file_context}
"""
            console.print("\n  [#888888]Generating fix...[/]\n")
            fixed_code = ai_engine.ask(fix_prompt, stream=False)

            if show_plan([
                f"Backup {file} → {file}.bak",
                f"Write fixed version to {file}",
            ], title="Apply Fix"):
                original = read_file(file)
                if original:
                    write_file(f"{file}.bak", original)
                write_file(file, fixed_code)
                console.print(
                    "\n  [bold #00ffcc]✓ Fix applied![/] "
                    "[#888888]Run your code to verify.[/]\n"
                )
            else:
                console.print("  [#888888]Fix not applied.[/]\n")