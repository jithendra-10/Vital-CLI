"""init.py — Vital Project Initializer"""

import os
import re
import json
from rich.console import Console
from vital import ai_engine
from vital.executor import write_file, run_command
from vital.safety import show_plan

console = Console()


def run(project: str = None, name: str = None):
    """Generate a complete project boilerplate from scratch."""

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Project Init[/]")
    console.print("  [#333355]" + "─" * 45 + "[/]\n")

    if not project:
        console.print("  [#ff6b6b]Usage: vital init <project-type>[/]\n")
        console.print(
            "  [#888888]Examples:[/]\n"
            "  [#444466]  vital init flask-api\n"
            "  [#444466]  vital init react-app --name myproject\n"
            "  [#444466]  vital init python-cli\n"
            "  [#444466]  vital init java-spring\n"
        )
        return

    project_name = name or project.replace(" ", "-").lower()

    prompt = f"""Generate a complete, production-ready project boilerplate for: {project}
Project name: {project_name}

Return ONLY a JSON object with this exact structure (no markdown, no extra text):
{{
  "description": "one line description of this project",
  "files": {{
    "filename.ext": "complete file content here",
    "subfolder/filename.ext": "complete file content here"
  }},
  "setup_commands": ["command1", "command2"],
  "run_command": "how to run/start the project"
}}

Rules:
- Include ALL essential files: main file, config, requirements/package.json, .gitignore, README.md
- Write COMPLETE file contents — not placeholders
- Follow best practices for {project}
- Make it immediately runnable
"""

    console.print(
        f"  [#888888]Generating [#ffdd57]{project}[/] boilerplate...[/]\n"
    )

    try:
        response = ai_engine.ask(prompt, stream=False)
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error: {e}[/]\n")
        return

    # Parse JSON response
    try:
        clean = re.sub(r'```json|```', '', response).strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            clean = match.group(0)
        data = json.loads(clean)
    except Exception:
        console.print(
            "  [#ff6b6b]Could not parse project structure.[/] "
            "[#888888]Try again or be more specific.[/]\n"
        )
        return

    files       = data.get("files", {})
    commands    = data.get("setup_commands", [])
    run_cmd     = data.get("run_command", "")
    description = data.get("description", "")

    console.print(f"  [#aaaaaa]{description}[/]\n")

    # Build plan
    plan = (
        [f"Create {project_name}/ folder"] +
        [f"Create {f}" for f in files.keys()] +
        ([f"Run: {cmd}" for cmd in commands] if commands else [])
    )

    if not show_plan(plan, title=f"Init {project_name}"):
        console.print("  [#888888]Cancelled.[/]\n")
        return

    # Create project folder
    os.makedirs(project_name, exist_ok=True)
    console.print(
        f"\n  [bold #00ffcc]◈ Creating files...[/]\n"
    )

    # Write all files
    for filepath, file_content in files.items():
        full_path = os.path.join(project_name, filepath)
        write_file(full_path, file_content)

    # Run setup commands
    if commands:
        console.print(
            f"\n  [bold #ffdd57]Setup commands:[/]\n"
        )
        for cmd in commands:
            try:
                confirm = console.input(
                    f"  Run [#444466]{cmd}[/]? "
                    "[bold #00ffcc][Y][/][bold #ff6b6b]/N[/]: "
                ).strip().upper()
            except (KeyboardInterrupt, EOFError):
                break
            if confirm == "Y":
                run_command(
                    f"cd {project_name} && {cmd}",
                    auto_approve=True
                )

    console.print(
        f"\n  [bold #00ffcc]✓ Project '{project_name}' created![/]\n"
        f"  [#888888]Navigate:[/]  [#444466]cd {project_name}[/]\n"
        + (f"  [#888888]Run:[/]       [#444466]{run_cmd}[/]\n" if run_cmd else "")
    )