import subprocess
from pathlib import Path
from rich.console import Console
from vital.safety import confirm_file_write, confirm_command

console = Console()


def run_command(command: str, auto_approve: bool = False) -> tuple[str, str, int]:
    """
    Run a shell command safely.
    Returns (stdout, stderr, returncode).
    """
    if not auto_approve:
        if not confirm_command(command):
            console.print("[yellow]Command cancelled.[/yellow]")
            return "", "", -1

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 60 seconds.[/red]")
        return "", "timeout", -1
    except Exception as e:
        console.print(f"[red]Error running command: {e}[/red]")
        return "", str(e), -1


def run_silent(command: str) -> tuple[str, str, int]:
    """Run command without asking for approval (for read-only ops)."""
    return run_command(command, auto_approve=True)


def write_file(filepath: str, content: str, auto_approve: bool = False) -> bool:
    """
    Write content to a file safely.
    Returns True if written, False if cancelled.
    """
    if not auto_approve:
        if not confirm_file_write(filepath, content):
            console.print("[yellow]File write cancelled.[/yellow]")
            return False

    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ Written:[/green] {filepath}")
        return True
    except Exception as e:
        console.print(f"[red]Error writing file: {e}[/red]")
        return False


def read_file(filepath: str) -> str | None:
    """Read a file and return its content."""
    try:
        return Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return None


def capture_error(command: str) -> str:
    """Run a command and capture any errors (for debug command)."""
    stdout, stderr, code = run_silent(command)

    output = ""
    if stdout:
        output += f"STDOUT:\n{stdout}\n"
    if stderr:
        output += f"STDERR:\n{stderr}\n"
    output += f"Exit code: {code}"

    return output
