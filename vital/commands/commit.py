"""commit.py — Vital Git Commit"""

import typer
from rich.console import Console
from vital import ai_engine
from vital.executor import run_silent, run_command
from vital.safety import show_plan

console = Console()


def run(push: bool = False):
    """Auto-generate a git commit message based on your changes."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Git Commit[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    # Check if inside a git repo
    _, _, code = run_silent("git rev-parse --is-inside-work-tree")
    if code != 0:
        console.print(
            "  [#ff6b6b]Not a git repository.[/] "
            "[#888888]Run 'git init' first.[/]\n"
        )
        return

    # Get staged diff first
    stdout, _, _ = run_silent("git diff --staged")

    if not stdout:
        # Try unstaged changes
        stdout, _, _ = run_silent("git diff")

    if not stdout:
        # Check for untracked files
        untracked, _, _ = run_silent("git status --short")
        if untracked:
            console.print(
                "  [#ffdd57]You have untracked files.[/] "
                "[#888888]Run 'git add .' first then try again.[/]\n"
            )
            console.print(f"  [#444444]{untracked}[/]\n")
        else:
            console.print(
                "  [#888888]No changes detected. "
                "Nothing to commit.[/]\n"
            )
        return

    prompt = f"""Generate a clear, concise git commit message for these changes.
Follow conventional commits format: type(scope): short description

Types: feat, fix, docs, style, refactor, test, chore, perf

Rules:
- First line max 72 characters
- Use imperative mood ("add feature" not "added feature")
- Be specific about what changed

Return ONLY the commit message — no quotes, no explanation.

Git diff:
{stdout[:5000]}
"""

    console.print("  [#888888]Analyzing changes...[/]\n")

    try:
        commit_msg = ai_engine.ask(prompt, stream=False)
        commit_msg = commit_msg.strip().strip('"').strip("'").splitlines()[0]
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    console.print(
        f"  [bold #ffdd57]Suggested commit:[/]\n"
        f"  [bold #00ffcc]{commit_msg}[/]\n"
    )

    try:
        edit = typer.confirm("  Edit the message?", default=False)
        if edit:
            commit_msg = typer.prompt(
                "  Enter commit message", default=commit_msg
            )
    except (KeyboardInterrupt, EOFError):
        console.print("  [#888888]Cancelled.[/]\n")
        return

    plan = [
        "git add -A  (stage all changes)",
        f'git commit -m "{commit_msg}"',
    ]
    if push:
        plan.append("git push")

    if show_plan(plan, title="Commit Plan"):
        run_command("git add -A", auto_approve=True)
        run_command(f'git commit -m "{commit_msg}"', auto_approve=True)
        if push:
            console.print("\n  [#888888]Pushing...[/]\n")
            run_command("git push", auto_approve=True)
        console.print("\n  [bold #00ffcc]✓ Committed![/]\n")
    else:
        console.print("  [#888888]Commit cancelled.[/]\n")