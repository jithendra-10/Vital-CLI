"""debug.py — Vital Debugger"""

import typer
from rich.console import Console
from vital import ai_engine, context
from vital.executor import capture_error, read_file

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
            import re as _re
            fixed_code = ai_engine.ask(fix_prompt, stream=False)
            fixed_code = _re.sub(r'^```\w*\n?', '', fixed_code.strip())
            fixed_code = _re.sub(r'\n?```$', '', fixed_code.strip())

            original = read_file(file)
            if not original:
                console.print(f"  [#ff6b6b]Could not read {file}[/]\n")
                return

            from vital.verify import verify_code, show_verify_error
            result = verify_code(file, fixed_code)
            if not result.passed:
                show_verify_error(result)
                return

            from vital.patch import analyze_blast_radius, show_patch_preview, apply_patch
            from vital.rollback import save_checkpoint
            blast = analyze_blast_radius(file, original, fixed_code)
            show_patch_preview(original, fixed_code, file, blast)

            console.print(
                "  [bold #00ffcc][A][/] Apply patch  "
                "[bold #ff6b6b][R][/] Reject"
            )
            console.print()
            try:
                choice = console.input("  Your choice (A/R): ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                return

            if choice == "A":
                save_checkpoint(file, original, description=f"debug fix: {error_output[:50]}")
                if apply_patch(file, fixed_code):
                    console.print(
                        f"\n  [bold #00ffcc]✓ Fix applied![/] "
                        f"[#888888]({blast.lines_changed} lines changed · "
                        f"undo with: vital undo)[/]\n"
                    )
            else:
                console.print("  [#888888]Fix not applied.[/]\n")