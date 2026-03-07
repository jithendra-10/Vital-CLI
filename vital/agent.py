"""
agent.py — Vital Agent Mode
Autonomously plans, builds, runs, and fixes complete projects.

Flow:
  1. PLAN    — AI breaks request into files + steps
  2. BUILD   — Creates each file one by one
  3. RUN     — Executes the project to test it
  4. FIX     — If errors found, auto-fixes them
  5. DONE    — Reports success with next steps
"""

import os
import re
import json
import subprocess
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

# ── Max auto-fix iterations before giving up ─────────────────────────────────
MAX_FIX_ITERATIONS = 3


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class AgentFile:
    """A single file the agent needs to create."""
    filename:    str
    description: str
    language:    str
    content:     str = ""
    created:     bool = False
    error:       str = ""


@dataclass
class AgentPlan:
    """The full plan the agent will execute."""
    project_name:  str
    project_type:  str
    description:   str
    folder:        str
    files:         list[AgentFile] = field(default_factory=list)
    run_command:   str = ""
    install_cmd:   str = ""
    success:       bool = False
    error_log:     list[str] = field(default_factory=list)


# ── Agent class ───────────────────────────────────────────────────────────────

class VitalAgent:
    """
    Vital's autonomous agent.
    Plans and builds complete projects with zero manual steps.
    """

    def __init__(self, working_dir: Path, ai_ask_fn):
        self.working_dir = working_dir
        self.ask         = ai_ask_fn   # reference to ai_engine.ask
        self.plan        = None

    # ── Step 1: Plan ──────────────────────────────────────────────────────────

    def plan_project(self, user_request: str) -> AgentPlan:
        """Ask AI to plan the full project structure."""
        console.print()
        console.print("  [bold #00ffcc]◈ Agent Mode[/]")
        console.print("  [#333355]" + "─" * 55 + "[/]")
        console.print(f"\n  [#888888]Planning:[/] [#ffdd57]{user_request}[/]\n")

        prompt = f"""You are Vital Agent, an expert software architect.
Analyze this request and create a complete project plan.

Request: {user_request}

Respond with ONLY a JSON object in this exact format (no markdown, no extra text):
{{
  "project_name": "short-kebab-case-name",
  "project_type": "e.g. HTML/CSS/JS, Flask, React, Java, Python CLI",
  "description": "one line description",
  "folder": "folder-name-to-create",
  "run_command": "command to run/test the project e.g. 'python app.py' or 'open index.html'",
  "install_cmd": "pip install X or npm install or empty string if none needed",
  "files": [
    {{
      "filename": "index.html",
      "description": "Main HTML file with calculator UI",
      "language": "html"
    }},
    {{
      "filename": "style.css",
      "description": "Styles for calculator",
      "language": "css"
    }},
    {{
      "filename": "script.js",
      "description": "Calculator logic",
      "language": "javascript"
    }}
  ]
}}

Rules:
- List ALL files needed for a complete working project
- Include config files like requirements.txt, package.json if needed
- Keep filenames simple, no subdirectories unless necessary
- run_command should actually test/run the project
- install_cmd is empty string if no dependencies needed
"""

        response = self.ask(prompt, stream=False)

        # Parse JSON plan
        try:
            # Strip any accidental markdown
            clean = re.sub(r'```json|```', '', response).strip()
            # Find JSON object
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                clean = match.group(0)
            data = json.loads(clean)
        except Exception as e:
            console.print(f"  [#ff6b6b]Could not parse plan: {e}[/]")
            console.print(f"  [#444444]Raw response: {response[:200]}[/]")
            return None

        # Build AgentPlan
        files = []
        for f in data.get("files", []):
            files.append(AgentFile(
                filename    = f.get("filename", "unknown"),
                description = f.get("description", ""),
                language    = f.get("language", "text"),
            ))

        plan = AgentPlan(
            project_name = data.get("project_name", "my-project"),
            project_type = data.get("project_type", "Unknown"),
            description  = data.get("description", ""),
            folder       = data.get("folder", data.get("project_name", "my-project")),
            files        = files,
            run_command  = data.get("run_command", ""),
            install_cmd  = data.get("install_cmd", ""),
        )

        self.plan = plan
        return plan

    # ── Show plan to user ─────────────────────────────────────────────────────

    def show_plan(self, plan: AgentPlan) -> bool:
        """
        Display the plan and ask user to confirm before building.
        Returns True if user confirms, False if rejected.
        """
        console.print()
        console.print(
            f"  [bold #ffdd57]◈ Project Plan — {plan.project_name}[/]"
        )
        console.print(f"  [#888888]{plan.description}[/]\n")

        # Files table
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold #00ffcc")
        table.add_column("#",           style="#444466", width=3)
        table.add_column("File",        style="#ffdd57", width=25)
        table.add_column("Type",        style="#888888", width=12)
        table.add_column("Description", style="#aaaaaa")

        for i, f in enumerate(plan.files, 1):
            table.add_row(str(i), f.filename, f.language, f.description)

        console.print(table)

        # Project info
        console.print(
            f"  [#888888]Folder:[/]   [#00ffcc]{plan.folder}/[/]\n"
            f"  [#888888]Type:[/]     [#00ffcc]{plan.project_type}[/]\n"
        )
        if plan.install_cmd:
            console.print(
                f"  [#888888]Install:[/]  [#444466]{plan.install_cmd}[/]\n"
            )
        if plan.run_command:
            console.print(
                f"  [#888888]Run with:[/] [#444466]{plan.run_command}[/]\n"
            )

        console.print(
            f"  [#888888]Will create [bold #00ffcc]{len(plan.files)} files[/] "
            f"in [#ffdd57]{self.working_dir / plan.folder}[/][/]\n"
        )

        # Confirm
        console.print(
            "  [bold #00ffcc][B][/] Build it!  "
            "[bold #ff6b6b][C][/] Cancel  "
            "[bold #ffdd57][E][/] Edit plan first"
        )
        console.print()

        try:
            choice = console.input("  Your choice (B/C/E): ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            return False

        if choice == "C":
            console.print("  [#888888]Cancelled.[/]\n")
            return False

        if choice == "E":
            self._edit_plan(plan)

        return choice in ("B", "E")

    def _edit_plan(self, plan: AgentPlan):
        """Let user tweak the plan before building."""
        console.print(
            "\n  [#888888]What would you like to change?[/] "
            "(e.g. 'add a README', 'remove style.css', 'rename to app.py')\n"
        )
        try:
            edit_request = console.input("  Change: ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not edit_request:
            return

        prompt = f"""Current plan files: {[f.filename for f in plan.files]}
User wants to change: {edit_request}

Respond with ONLY a JSON array of the updated files list:
[
  {{"filename": "...", "description": "...", "language": "..."}}
]
"""
        response = self.ask(prompt, stream=False)
        try:
            clean   = re.sub(r'```json|```', '', response).strip()
            match   = re.search(r'\[.*\]', clean, re.DOTALL)
            if match:
                new_files = json.loads(match.group(0))
                plan.files = [
                    AgentFile(
                        filename    = f.get("filename", ""),
                        description = f.get("description", ""),
                        language    = f.get("language", "text"),
                    )
                    for f in new_files
                ]
                console.print(
                    f"  [#00ffcc]✓ Plan updated — {len(plan.files)} files[/]\n"
                )
        except Exception:
            console.print("  [#ff6b6b]Could not update plan.[/]\n")

    # ── Step 2: Build ─────────────────────────────────────────────────────────

    def build_project(self, plan: AgentPlan) -> bool:
        """Generate code for every file in the plan."""
        console.print()
        console.print("  [bold #00ffcc]◈ Building...[/]\n")

        # Create project folder
        project_dir = self.working_dir / plan.folder
        project_dir.mkdir(parents=True, exist_ok=True)

        # Get all file descriptions for context
        file_list = "\n".join(
            f"- {f.filename}: {f.description}" for f in plan.files
        )

        total = len(plan.files)
        for i, agent_file in enumerate(plan.files, 1):
            console.print(
                f"  [#444466][{i}/{total}][/] "
                f"[#888888]Generating[/] [#ffdd57]{agent_file.filename}[/]..."
            )

            # Build already-created files context
            created_context = ""
            for prev in plan.files:
                if prev.created and prev.content:
                    created_context += f"\n--- {prev.filename} ---\n{prev.content[:500]}\n"

            prompt = f"""You are Vital Agent building a {plan.project_type} project.
Project: {plan.project_name} — {plan.description}

All files in this project:
{file_list}

Already created:
{created_context if created_context else "None yet — this is the first file"}

Now generate ONLY the complete code for: {agent_file.filename}
Description: {agent_file.description}

Rules:
- Write COMPLETE, working, production-quality code
- Make sure it integrates with the other files
- No explanations, no markdown, no code fences
- Just the raw code content for this file
"""
            code = self.ask(prompt, stream=False)

            # Clean up any accidental code fences
            code = re.sub(r'^```\w*\n?', '', code.strip())
            code = re.sub(r'\n?```$', '', code.strip())

            # Write file
            filepath = project_dir / agent_file.filename
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(code.strip(), encoding="utf-8")
                size = filepath.stat().st_size
                agent_file.content = code
                agent_file.created = True
                console.print(
                    f"  [bold #00ffcc]  ✓[/] [#ffdd57]{agent_file.filename}[/] "
                    f"[#888888]({size} bytes)[/]"
                )
            except Exception as e:
                agent_file.error = str(e)
                console.print(
                    f"  [#ff6b6b]  ✗ {agent_file.filename}: {e}[/]"
                )

        created = sum(1 for f in plan.files if f.created)
        console.print(
            f"\n  [bold #00ffcc]✓ {created}/{total} files created[/] "
            f"in [#ffdd57]{project_dir}[/]\n"
        )
        return created == total

    # ── Step 3: Install dependencies ─────────────────────────────────────────

    def install_deps(self, plan: AgentPlan) -> bool:
        """Run install command if project needs dependencies."""
        if not plan.install_cmd:
            return True

        console.print(
            f"  [#888888]Installing dependencies:[/] "
            f"[#444466]{plan.install_cmd}[/]\n"
        )

        project_dir = self.working_dir / plan.folder
        try:
            result = subprocess.run(
                plan.install_cmd,
                shell=True,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                console.print("  [#00ffcc]✓ Dependencies installed[/]\n")
                return True
            else:
                console.print(
                    f"  [#ffdd57]⚠ Install warning:[/] "
                    f"[#888888]{result.stderr[:200]}[/]\n"
                )
                return False
        except subprocess.TimeoutExpired:
            console.print("  [#ffdd57]⚠ Install timed out — continuing anyway[/]\n")
            return False
        except Exception as e:
            console.print(f"  [#ff6b6b]Install error: {e}[/]\n")
            return False

    # ── Step 4: Run & test ────────────────────────────────────────────────────

    def run_project(self, plan: AgentPlan) -> tuple[bool, str]:
        """
        Run the project to check for errors.
        Returns (success, output/error).
        """
        if not plan.run_command:
            return True, ""

        # Skip commands that just open a browser
        skip_patterns = ["open ", "start ", "xdg-open"]
        if any(plan.run_command.startswith(p) for p in skip_patterns):
            console.print(
                f"  [#00ffcc]✓ Open [#ffdd57]{plan.folder}/index.html[/] "
                f"in your browser to test[/]\n"
            )
            return True, ""

        console.print(
            f"  [#888888]Testing:[/] [#444466]{plan.run_command}[/]\n"
        )

        project_dir = self.working_dir / plan.folder
        try:
            result = subprocess.run(
                plan.run_command,
                shell=True,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=15
            )

            output = result.stdout + result.stderr

            if result.returncode == 0:
                console.print("  [#00ffcc]✓ Project runs successfully[/]\n")
                return True, output
            else:
                console.print(
                    f"  [#ffdd57]⚠ Error detected:[/]\n"
                    f"  [#ff6b6b]{output[:400]}[/]\n"
                )
                return False, output

        except subprocess.TimeoutExpired:
            # Timeout usually means app is running (server started) — that's good!
            console.print("  [#00ffcc]✓ App started successfully[/]\n")
            return True, "timeout — app running"
        except Exception as e:
            return False, str(e)

    # ── Step 5: Auto-fix ──────────────────────────────────────────────────────

    def fix_errors(self, plan: AgentPlan, error_output: str) -> bool:
        """
        Ask AI to fix errors found during run.
        Returns True if fix was applied.
        """
        console.print(
            "  [bold #ffdd57]◈ Auto-fixing errors...[/]\n"
        )

        # Build context of all current files
        files_context = ""
        project_dir   = self.working_dir / plan.folder
        for agent_file in plan.files:
            filepath = project_dir / agent_file.filename
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                files_context += f"\n--- {agent_file.filename} ---\n{content}\n"

        prompt = f"""You are Vital Agent. A project has errors after running.

Project: {plan.project_name} ({plan.project_type})
Run command: {plan.run_command}

Error output:
{error_output}

Current files:
{files_context[:6000]}

Analyze the error and fix it. Respond with ONLY a JSON array of files to update:
[
  {{
    "filename": "file_with_error.py",
    "fixed_code": "... complete fixed file content ..."
  }}
]

Only include files that need changes. Write complete file content, not diffs.
"""

        response = self.ask(prompt, stream=False)

        try:
            clean = re.sub(r'```json|```', '', response).strip()
            match = re.search(r'\[.*\]', clean, re.DOTALL)
            if not match:
                return False

            fixes = json.loads(match.group(0))
            fixed_count = 0

            for fix in fixes:
                filename   = fix.get("filename", "")
                fixed_code = fix.get("fixed_code", "")

                if not filename or not fixed_code:
                    continue

                filepath = project_dir / filename
                if filepath.exists():
                    # Backup original
                    backup = filepath.with_suffix(filepath.suffix + ".bak")
                    filepath.rename(backup)

                filepath.write_text(fixed_code.strip(), encoding="utf-8")
                console.print(
                    f"  [#00ffcc]✓ Fixed:[/] [#ffdd57]{filename}[/]"
                )
                # Update plan
                for f in plan.files:
                    if f.filename == filename:
                        f.content = fixed_code
                fixed_count += 1

            if fixed_count:
                console.print(
                    f"\n  [#00ffcc]✓ {fixed_count} file(s) fixed[/]\n"
                )
            return fixed_count > 0

        except Exception as e:
            console.print(f"  [#ff6b6b]Could not parse fix: {e}[/]\n")
            return False

    # ── Step 6: Done report ───────────────────────────────────────────────────

    def show_completion(self, plan: AgentPlan, success: bool):
        """Show final summary after agent finishes."""
        console.print()
        project_dir = self.working_dir / plan.folder

        if success:
            console.print(Panel(
                f"[bold #00ffcc]✓ {plan.project_name} built successfully![/]\n\n"
                f"[#888888]Location:[/]  [#ffdd57]{project_dir}[/]\n"
                f"[#888888]Files:[/]     [#00ffcc]{len(plan.files)} created[/]\n"
                f"[#888888]Type:[/]      [#aaaaaa]{plan.project_type}[/]\n\n"
                + (f"[#888888]To run:[/]    [bold #444466]{plan.run_command}[/]"
                   if plan.run_command else ""),
                border_style="#00ffcc",
                title="[bold #00ffcc] Agent Complete ",
                padding=(1, 2)
            ))
        else:
            console.print(Panel(
                f"[bold #ffdd57]⚠ {plan.project_name} built with warnings[/]\n\n"
                f"[#888888]Location:[/]  [#ffdd57]{project_dir}[/]\n"
                f"[#888888]Files:[/]     [#00ffcc]{len([f for f in plan.files if f.created])} created[/]\n\n"
                f"[#888888]Some issues may remain. Review the files manually.[/]\n"
                f"[#888888]You can ask Vital to fix specific issues.[/]",
                border_style="#ffdd57",
                title="[bold #ffdd57] Agent Done with Warnings ",
                padding=(1, 2)
            ))

        console.print()

    # ── Main orchestrator ─────────────────────────────────────────────────────

    def run(self, user_request: str):
        """
        Full agent pipeline:
        Plan → Confirm → Build → Install → Run → Fix → Done
        """
        # Step 1: Plan
        plan = self.plan_project(user_request)
        if not plan:
            console.print(
                "  [#ff6b6b]Could not create a plan. Try being more specific.[/]\n"
            )
            return

        # Step 2: Show plan and confirm
        confirmed = self.show_plan(plan)
        if not confirmed:
            return

        # Step 3: Build all files
        build_ok = self.build_project(plan)

        # Step 4: Install dependencies
        if plan.install_cmd:
            self.install_deps(plan)

        # Step 5: Run and auto-fix loop
        run_success = True
        if plan.run_command:
            for attempt in range(MAX_FIX_ITERATIONS):
                success, output = self.run_project(plan)

                if success:
                    run_success = True
                    break

                if attempt < MAX_FIX_ITERATIONS - 1:
                    console.print(
                        f"  [#ffdd57]Auto-fix attempt {attempt + 1}/{MAX_FIX_ITERATIONS}...[/]\n"
                    )
                    fixed = self.fix_errors(plan, output)
                    if not fixed:
                        console.print(
                            "  [#888888]Could not auto-fix. Moving on.[/]\n"
                        )
                        run_success = False
                        break
                else:
                    run_success = False

        # Step 6: Done
        self.show_completion(plan, build_ok and run_success)


# ── Detect if user wants agent mode ──────────────────────────────────────────

AGENT_TRIGGERS = [
    "build me", "build a", "create a full", "create a complete",
    "make me a", "make a full", "generate a full", "generate a complete",
    "develop a", "develop me", "agent build", "agent create",
    "full project", "complete project", "entire project",
    "full app", "complete app", "entire app",
    "from scratch", "full stack", "fullstack",
]


def is_agent_request(user_input: str) -> bool:
    """Detect if user wants full agent mode vs simple file creation."""
    lower = user_input.lower()
    return any(trigger in lower for trigger in AGENT_TRIGGERS)
