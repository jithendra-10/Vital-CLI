import typer
from rich.console import Console
from rich.panel import Panel
from vital import ai_engine, executor
from vital.safety import show_plan

console = Console()


def run(
    project: str = typer.Argument(..., help="Project type e.g. 'flask-api', 'react-app', 'cli-tool'"),
    name: str = typer.Option(None, "--name", "-n", help="Project name"),
):
    """Generate a project boilerplate from scratch using AI."""

    console.print(Panel("[bold cyan]Vital Project Initializer[/bold cyan]", border_style="cyan"))

    project_name = name or project.replace(" ", "-").lower()

    prompt = f"""
Generate a complete project boilerplate for: {project}
Project name: {project_name}

Return a JSON object with this structure:
{{
  "files": {{
    "filename.ext": "file content here",
    "folder/filename.ext": "file content here"
  }},
  "setup_commands": ["command1", "command2"],
  "description": "What this project does"
}}

Include all essential files: main file, config, requirements/package.json, .gitignore, README.md.
Make it production-ready and follow best practices.
"""

    console.print(f"\n[bold yellow]Generating {project} boilerplate...[/bold yellow]\n")

    import json
    response = ai_engine.ask(prompt, stream=False)

    # Try to parse JSON response
    try:
        # Strip markdown code blocks if present
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean)
    except Exception:
        console.print("[red]Could not parse project structure. Showing raw output:[/red]")
        console.print(response)
        return

    files = data.get("files", {})
    commands = data.get("setup_commands", [])
    description = data.get("description", "")

    console.print(f"\n[bold]{description}[/bold]")

    plan = [f"Create {project_name}/ folder"] + \
           [f"Create {f}" for f in files.keys()] + \
           [f"Run: {cmd}" for cmd in commands]

    if show_plan(plan, f"Initialize {project_name}"):
        import os
        os.makedirs(project_name, exist_ok=True)

        for filepath, content in files.items():
            full_path = f"{project_name}/{filepath}"
            executor.write_file(full_path, content, auto_approve=True)

        for cmd in commands:
            run_cmd = typer.confirm(f"\nRun '{cmd}'?", default=True)
            if run_cmd:
                executor.run_command(f"cd {project_name} && {cmd}", auto_approve=True)

        console.print(f"\n[green]✓ Project '{project_name}' created![/green]")
        console.print(f"[dim]cd {project_name} to get started[/dim]")
    else:
        console.print("[yellow]Project creation cancelled.[/yellow]")
