"""test.py — Vital Test Generator"""

import os
from rich.console import Console
from vital import ai_engine, context
from vital.executor import write_file
from vital.safety import show_plan

console = Console()


def run(file: str = None, output: str = None, framework: str = "pytest"):
    """Generate unit tests for your code using AI."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Test Generator[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if not file:
        console.print("  [#ff6b6b]Usage: vital test <filename>[/]\n")
        return

    file_context = context.get_file_context(file)
    if not file_context:
        console.print(f"  [#ff6b6b]Could not read {file}[/]\n")
        return

    basename    = os.path.basename(file).replace(".py", "").replace(".js", "")
    output_file = output or f"test_{basename}.py"

    prompt = f"""Generate comprehensive {framework} unit tests for this code.

Requirements:
- Test ALL public functions and methods
- Include normal cases, edge cases, and error cases
- Use clear, descriptive test names (test_function_does_what_when_condition)
- Add brief docstrings explaining what each test verifies
- Mock external dependencies (files, APIs, databases)
- Aim for high code coverage

Return ONLY the complete test file content.
No explanation, no markdown fences — just the test code.

Code to test ({file}):
{file_context}
"""

    console.print(
        f"  [#888888]Generating [#ffdd57]{framework}[/] tests for "
        f"[#ffdd57]{file}[/]...[/]\n"
    )

    try:
        tests = ai_engine.ask(prompt, stream=True)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    if show_plan([
        f"Generate {framework} tests for {file}",
        f"Write tests to {output_file}",
    ], title="Save Tests"):
        write_file(output_file, tests)
        console.print(
            f"\n  [bold #00ffcc]✓ Tests saved to[/] [#ffdd57]{output_file}[/]\n"
            f"  [#888888]Run with:[/] [#444466]pytest {output_file}[/]\n"
        )
    else:
        console.print("  [#888888]Test generation cancelled.[/]\n")