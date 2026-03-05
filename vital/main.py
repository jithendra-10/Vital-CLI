import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="vital",
    help="🧠 Vital - AI-powered coding assistant for your terminal",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,  # allows running `vital` with no args
)

console = Console()


@app.callback()
def default(ctx: typer.Context):
    """Launch Vital interactive mode when no command is given."""
    if ctx.invoked_subcommand is None:
        from vital.interactive import run_interactive
        run_interactive()


# ─── Setup ────────────────────────────────────────────────────────────────────

@app.command()
def setup():
    """First-time setup: configure your AI providers and API keys."""
    from vital.config import setup as run_setup
    run_setup()


# ─── Providers ────────────────────────────────────────────────────────────────

@app.command()
def providers():
    """Manage your AI providers — add, remove, edit, change default."""
    from vital.providers import edit_providers, _show_provider_status
    _show_provider_status()
    edit_providers()


@app.command()
def status():
    """Show all configured AI providers and their status."""
    from vital.providers import _show_provider_status
    _show_provider_status()


# ─── Chat ─────────────────────────────────────────────────────────────────────

@app.command()
def chat(
    message: list[str] = typer.Argument(..., help="Message to send to AI"),
):
    """Chat directly with AI in your terminal."""
    from vital import ai_engine
    full_message = " ".join(message)
    console.print("\n[bold cyan]Vital[/bold cyan]\n")
    ai_engine.ask(full_message)


# ─── Debug ────────────────────────────────────────────────────────────────────

@app.command()
def debug(
    file: str = typer.Option(None, "--file", "-f", help="File to debug"),
    command: str = typer.Option(None, "--run", "-r", help="Command to run and capture errors"),
    error: str = typer.Option(None, "--error", "-e", help="Paste error message directly"),
):
    """🐛 Debug your code - analyzes errors and suggests fixes."""
    from vital.commands.debug import run
    run(file=file, command=command, error=error)


# ─── Explain ──────────────────────────────────────────────────────────────────

@app.command()
def explain(
    path: str = typer.Argument(".", help="File or folder to explain"),
    simple: bool = typer.Option(False, "--simple", "-s", help="Explain for beginners"),
):
    """📖 Explain what your code does in plain English."""
    from vital.commands.explain import run
    run(path=path, simple=simple)


# ─── Fix ──────────────────────────────────────────────────────────────────────

@app.command()
def fix(
    file: str = typer.Argument(..., help="File to fix"),
    issue: str = typer.Option(None, "--issue", "-i", help="Describe the issue"),
):
    """🔧 Fix issues in your code using AI."""
    from vital.commands.fix import run
    run(file=file, issue=issue)


# ─── Document ─────────────────────────────────────────────────────────────────

@app.command()
def doc(
    path: str = typer.Argument(".", help="File or folder to document"),
    output: str = typer.Option(None, "--output", "-o", help="Output file"),
):
    """📝 Auto-generate documentation for your code."""
    from vital.commands.doc import run
    run(path=path, output=output)


# ─── Commit ───────────────────────────────────────────────────────────────────

@app.command()
def commit(
    push: bool = typer.Option(False, "--push", "-p", help="Push after committing"),
):
    """💾 Auto-generate a git commit message from your changes."""
    from vital.commands.commit import run
    run(push=push)


# ─── Refactor ─────────────────────────────────────────────────────────────────

@app.command()
def refactor(
    file: str = typer.Argument(..., help="File to refactor"),
    goal: str = typer.Option(None, "--goal", "-g", help="Refactoring goal"),
):
    """♻️  Refactor and improve your code quality."""
    from vital.commands.refactor import run
    run(file=file, goal=goal)


# ─── Test ─────────────────────────────────────────────────────────────────────

@app.command()
def test(
    file: str = typer.Argument(..., help="File to generate tests for"),
    output: str = typer.Option(None, "--output", "-o", help="Output test file"),
    framework: str = typer.Option("pytest", "--framework", "-f", help="Test framework"),
):
    """🧪 Generate unit tests for your code."""
    from vital.commands.test import run
    run(file=file, output=output, framework=framework)


# ─── Init ─────────────────────────────────────────────────────────────────────

@app.command()
def init(
    project: str = typer.Argument(..., help="Project type e.g. 'flask-api'"),
    name: str = typer.Option(None, "--name", "-n", help="Project name"),
):
    """🚀 Generate a project boilerplate from scratch."""
    from vital.commands.init import run
    run(project=project, name=name)


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
