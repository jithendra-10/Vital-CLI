import sys
import typer
from rich.console import Console
from rich.panel import Panel

# ── Fix 8: Version pulled from __init__.py ────────────────────────────────────
from vital import __version__

app = typer.Typer(
    name="vital",
    help="🧠 Vital - AI-Powered Terminal Coding Assistant",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)

console = Console()


# ── Fix 9: Global friendly error handler ─────────────────────────────────────

FRIENDLY_ERRORS = {
    "AuthenticationError":      "Invalid API key. Run [bold]vital setup[/bold] to update it.",
    "RateLimitError":           "Rate limit hit. Wait a moment and try again.",
    "APIConnectionError":       "Can't connect to AI provider. Check your internet connection.",
    "APITimeoutError":          "Request timed out. Try again or switch providers with /providers.",
    "InternalServerError":      "AI provider is having issues. Try again or switch providers.",
    "NotFoundError":            "Model not found. Run [bold]vital setup[/bold] to choose a different model.",
    "PermissionDeniedError":    "API key doesn't have permission. Check your account at the provider.",
    "JSONDecodeError":          "Unexpected response from AI. Try again.",
    "ConnectionRefusedError":   "Connection refused. Check your internet connection.",
    "FileNotFoundError":        "File not found. Check the path and try again.",
    "PermissionError":          "Permission denied. Check file permissions.",
    "KeyboardInterrupt":        "",  # silent — handled in interactive loop
}


def friendly_error(e: Exception) -> str:
    """Convert a raw exception into a friendly user message."""
    etype = type(e).__name__
    msg   = str(e)

    # Check known error types
    if etype in FRIENDLY_ERRORS:
        friendly = FRIENDLY_ERRORS[etype]
        return friendly if friendly else ""

    # Check for common error patterns in message
    msg_lower = msg.lower()
    if "api key" in msg_lower or "apikey" in msg_lower or "unauthorized" in msg_lower:
        return "Invalid or missing API key. Run [bold]vital setup[/bold] to configure it."
    if "rate limit" in msg_lower:
        return "Rate limit reached. Wait a moment and try again."
    if "timeout" in msg_lower:
        return "Request timed out. Try again in a moment."
    if "connection" in msg_lower or "network" in msg_lower:
        return "Network error. Check your internet connection."
    if "token" in msg_lower and "limit" in msg_lower:
        return "Response too long for this model. Try a more specific question."
    if "model" in msg_lower and ("not found" in msg_lower or "does not exist" in msg_lower):
        return "Model not found. Run [bold]vital setup[/bold] to choose a different model."

    # Generic fallback — show the error but cleaned up
    return f"Something went wrong: {etype}: {msg}"


# ── Fix 7: Lazy startup — don't scan files until needed ──────────────────────

@app.callback()
def default(
    ctx:    typer.Context,
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume last session"),
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """Launch Vital interactive mode when no command is given."""
    if version:
        # Fix 8: Version command
        console.print(
            f"\n  [bold #00ffcc]Vital[/] [#ffdd57]v{__version__}[/]  "
            f"[#888888]AI-Powered Terminal Coding Assistant[/]\n"
        )
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        try:
            from vital.interactive import run_interactive
            run_interactive(resume=resume)
        except KeyboardInterrupt:
            console.print("\n  [#888888]Goodbye![/]\n")
        except Exception as e:
            msg = friendly_error(e)
            if msg:
                console.print(f"\n  [bold #ff6b6b]✗[/] {msg}\n")
            sys.exit(1)


# ─── Agent ────────────────────────────────────────────────────────────────────

@app.command()
def agent(
    request: list[str] = typer.Argument(..., help="What to build e.g. 'a flask todo app'"),
):
    """Agent Mode — autonomously plan, build and run complete projects."""
    try:
        from vital.agent import VitalAgent
        from vital import ai_engine
        from pathlib import Path

        req = " ".join(request)
        a   = VitalAgent(working_dir=Path.cwd(), ai_ask_fn=ai_engine.ask)
        a.run(req)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Setup ────────────────────────────────────────────────────────────────────

@app.command()
def setup():
    """Configure your AI providers and API keys."""
    try:
        from vital.config import setup as run_setup
        run_setup()
    except KeyboardInterrupt:
        console.print("\n  [#888888]Setup cancelled.[/]\n")
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Providers ────────────────────────────────────────────────────────────────

@app.command()
def providers():
    """Manage AI providers — add, remove, edit, change default."""
    try:
        from vital.providers import edit_providers, _show_provider_status
        _show_provider_status()
        edit_providers()
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


@app.command()
def status():
    """Show all configured AI providers and their status."""
    try:
        from vital.providers import _show_provider_status
        _show_provider_status()
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Chat ─────────────────────────────────────────────────────────────────────

@app.command()
def chat(
    message: list[str] = typer.Argument(..., help="Message to send to AI"),
):
    """Chat directly with AI from your terminal."""
    try:
        from vital import ai_engine
        full_message = " ".join(message)
        console.print("\n  [bold #00ffcc]◈ Vital[/]\n")
        ai_engine.ask(full_message)
        console.print()
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Debug ────────────────────────────────────────────────────────────────────

@app.command()
def debug(
    file:    str = typer.Option(None, "--file",  "-f", help="File to debug"),
    command: str = typer.Option(None, "--run",   "-r", help="Command to run and capture errors"),
    error:   str = typer.Option(None, "--error", "-e", help="Paste error message directly"),
):
    """Debug your code — analyzes errors and suggests fixes."""
    try:
        from vital.commands.debug import run
        run(file=file, command=command, error=error)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Explain ──────────────────────────────────────────────────────────────────

@app.command()
def explain(
    path:   str  = typer.Argument(".", help="File or folder to explain"),
    simple: bool = typer.Option(False, "--simple", "-s", help="Explain for beginners"),
):
    """Explain what your code does in plain English."""
    try:
        from vital.commands.explain import run
        run(path=path, simple=simple)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Fix ──────────────────────────────────────────────────────────────────────

@app.command()
def fix(
    file:  str = typer.Argument(..., help="File to fix"),
    issue: str = typer.Option(None, "--issue", "-i", help="Describe the issue"),
):
    """Fix issues in your code using AI."""
    try:
        from vital.commands.fix import run
        run(file=file, issue=issue)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Document ─────────────────────────────────────────────────────────────────

@app.command()
def doc(
    path:   str = typer.Argument(".", help="File or folder to document"),
    output: str = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Auto-generate documentation for your code."""
    try:
        from vital.commands.doc import run
        run(path=path, output=output)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Commit ───────────────────────────────────────────────────────────────────

@app.command()
def commit(
    push: bool = typer.Option(False, "--push", "-p", help="Push after committing"),
):
    """Auto-generate a git commit message from your changes."""
    try:
        from vital.commands.commit import run
        run(push=push)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Refactor ─────────────────────────────────────────────────────────────────

@app.command()
def refactor(
    file: str = typer.Argument(..., help="File to refactor"),
    goal: str = typer.Option(None, "--goal", "-g", help="Refactoring goal"),
):
    """Refactor and improve your code quality."""
    try:
        from vital.commands.refactor import run
        run(file=file, goal=goal)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Test ─────────────────────────────────────────────────────────────────────

@app.command()
def test(
    file:      str = typer.Argument(..., help="File to generate tests for"),
    output:    str = typer.Option(None,    "--output",    "-o", help="Output test file"),
    framework: str = typer.Option("pytest","--framework", "-f", help="Test framework"),
):
    """Generate unit tests for your code."""
    try:
        from vital.commands.test import run
        run(file=file, output=output, framework=framework)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Init ─────────────────────────────────────────────────────────────────────

@app.command()
def init(
    project: str = typer.Argument(..., help="Project type e.g. 'flask-api'"),
    name:    str = typer.Option(None, "--name", "-n", help="Project name"),
):
    """Generate a project boilerplate from scratch."""
    try:
        from vital.commands.init import run
        run(project=project, name=name)
    except Exception as e:
        console.print(f"\n  [bold #ff6b6b]✗[/] {friendly_error(e)}\n")


# ─── Version ──────────────────────────────────────────────────────────────────

@app.command(name="version")
def version_cmd():
    """Show Vital version."""
    console.print(
        f"\n  [bold #00ffcc]Vital[/] [#ffdd57]v{__version__}[/]  "
        f"[#888888]AI-Powered Terminal Coding Assistant[/]\n"
    )


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()