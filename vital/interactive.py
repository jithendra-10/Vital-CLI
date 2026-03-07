import os
import re
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from vital.config import get_api_key
from vital import ai_engine, context
from vital.session import Session, resume_session, show_sessions, cleanup_old_sessions
from vital.memory import load_memory, memory_show, memory_add, memory_edit, memory_refresh, memory_clear, init_project_memory
from vital.agent import VitalAgent, is_agent_request

console = Console()

# ── Thinking Spinner ──────────────────────────────────────────────────────────

class ThinkingSpinner:
    """
    Animated spinner that shows while AI is thinking.
    Runs in a background thread — stops the moment streaming starts.
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    MESSAGES = [
        "thinking",
        "analyzing",
        "processing",
        "generating",
        "reasoning",
    ]

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = None

    def start(self, provider: str = None):
        """Start the spinner in background."""
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._spin,
            args=(provider,),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """Stop the spinner and clear the line."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        # Clear the spinner line
        print("\r" + " " * 60 + "\r", end="", flush=True)

    def _spin(self, provider: str = None):
        provider_label = f" [{provider}]" if provider else ""
        msg_index = 0
        frame_index = 0

        while not self._stop.is_set():
            frame   = self.FRAMES[frame_index % len(self.FRAMES)]
            message = self.MESSAGES[msg_index % len(self.MESSAGES)]
            line    = f"\r  \033[36m{frame}\033[0m  \033[90m{message}{provider_label}...\033[0m"
            print(line, end="", flush=True)
            time.sleep(0.08)
            frame_index += 1
            # Change message every 15 frames (~1.2 seconds)
            if frame_index % 15 == 0:
                msg_index += 1


# Global spinner instance
spinner = ThinkingSpinner()

# ── Style ─────────────────────────────────────────────────────────────────────
STYLE = Style.from_dict({
    "prompt":         "#00ffcc bold",
    "bottom-toolbar": "bg:#1a1a2e #444466",
})

HISTORY_FILE  = Path.home() / ".vital_history"
WORKING_DIR   = Path.cwd()  # locked at launch
ALWAYS_ALLOW  = False        # session-wide auto-save toggle

# ── Multi-file keywords ───────────────────────────────────────────────────────
MULTI_FILE_KEYWORDS = [
    "create", "build", "make", "generate", "write", "app", "application",
    "project", "website", "web app", "html", "css", "js", "javascript",
    "flask", "django", "react", "todo", "calculator", "login", "form"
]

COMMANDS = {
    "/debug":    "Debug errors in your code",
    "/explain":  "Explain a file or project",
    "/fix":      "Fix issues in a file",
    "/doc":      "Generate documentation",
    "/commit":   "Auto git commit message",
    "/refactor": "Refactor a file",
    "/test":     "Generate unit tests",
    "/init":     "Create project boilerplate",
    "/clear":    "Clear the screen",
    "/context":  "Show current project context",
    "/model":    "Show current AI model",
    "/agent":    "Launch Agent Mode — build full projects autonomously",
    "/providers":"Manage AI providers — add, remove, switch",
    "/memory":   "Manage memory: show, add, edit, clear, refresh",
    "/history":  "Show current session history",
    "/resume":   "Resume a previous session",
    "/allowoff": "Turn off Always Allow mode",
    "/help":     "Show all commands",
    "/exit":     "Exit Vital",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_project_name() -> str:
    return WORKING_DIR.name


def get_git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2
        )
        branch = result.stdout.strip()
        return f" ⎇ {branch}" if branch else ""
    except Exception:
        return ""


def get_total_file_count() -> int:
    try:
        return context.count_all_files(str(WORKING_DIR))["total"]
    except Exception:
        return 0


def is_multi_file_request(user_input: str) -> bool:
    """Detect if user wants to create a multi-file project."""
    lower = user_input.lower()
    matched = sum(1 for kw in MULTI_FILE_KEYWORDS if kw in lower)
    return matched >= 2


# Casual conversational phrases — no code context needed
CASUAL_PHRASES = {
    "hi", "hello", "hey", "hii", "helo", "sup", "yo",
    "how are you", "how r u", "whats up", "what's up",
    "good morning", "good evening", "good afternoon", "good night",
    "thanks", "thank you", "thankyou", "thx", "ty",
    "bye", "goodbye", "see you", "cya",
    "ok", "okay", "cool", "nice", "great", "awesome",
    "who are you", "what are you", "what can you do",
}

# General knowledge topics — no project context needed
GENERAL_KNOWLEDGE_STARTERS = {
    "tell me about", "what is", "what are", "explain",
    "who is", "who are", "where is", "when did", "when was",
    "how does", "how do", "why is", "why did", "why does",
    "what happened", "history of", "definition of",
    "difference between", "compare", "summarize",
}

# Coding-specific keywords — these SHOULD use project context
CODE_KEYWORDS = {
    "file", "code", "error", "bug", "fix", "create", "build",
    "function", "class", "import", "debug", "run", "test",
    "refactor", "generate", "write", "make", "project",
    "variable", "method", "module", "script", "app",
    "this file", "my file", "this project", "my project",
    "my code", "this code", ".py", ".js", ".java", ".html",
}


def is_casual_message(user_input: str) -> bool:
    """
    Detect if the message is casual conversation or general knowledge.
    NEVER returns True if message contains coding/build keywords.
    """
    lower = user_input.lower().strip().rstrip("!?.,")

    # These ALWAYS mean it's a coding task — never casual
    ALWAYS_CODE = {
        "create", "build", "make", "generate", "write", "fix", "debug",
        "refactor", "test", "explain", "file", "code", "error", "bug",
        "function", "class", "import", "run", "project", "app", "application",
        "html", "css", "js", "javascript", "python", "java", "flask",
        "django", "react", "folder", "directory", "path", "script",
        ".py", ".js", ".java", ".html", ".css", "my code", "this code",
        "this file", "my file", "my project", "this project",
    }

    # If ANY coding keyword found — it's NOT casual
    if any(kw in lower for kw in ALWAYS_CODE):
        return False

    # Exact match for casual greetings
    if lower in CASUAL_PHRASES:
        return True

    # General knowledge starters WITHOUT coding keywords
    for starter in GENERAL_KNOWLEDGE_STARTERS:
        if lower.startswith(starter):
            return True

    # Very short messages (1-3 words) with no coding keywords
    if len(lower.split()) <= 3:
        return True

    return False


def detect_mentioned_file(user_input: str) -> str | None:
    """Detect if user mentioned a specific existing filename."""
    pattern = r'\b[\w\-]+\.[a-zA-Z]{1,6}\b'
    matches = re.findall(pattern, user_input)
    for match in matches:
        found = list(WORKING_DIR.rglob(match))
        if found:
            return str(found[0])
    return None


def extract_code_blocks(response: str) -> list[dict]:
    """Extract all code blocks from AI response with their filenames."""
    blocks = []

    # Try to find filename hints above code blocks
    # Pattern: optional filename comment, then ```lang\ncode```
    pattern = r'(?:(?:#{1,3}|//|<!--|/\*)\s*)?(?:File(?:name)?:\s*)?([`\'"]*[\w\-./]+\.\w+[`\'"]*\s*\n)?```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

    for match in matches:
        filename_hint = match[0].strip().strip("`'\"").strip()
        language      = match[1].strip() if match[1] else "text"
        code          = match[2].strip()

        if len(code.splitlines()) < 3:
            continue

        blocks.append({
            "filename": filename_hint or None,
            "language": language,
            "code":     code
        })

    return blocks


def guess_filename(language: str, index: int = 0) -> str:
    """Guess a filename from language."""
    ext_map = {
        "python":     ".py",
        "java":       ".java",
        "javascript": ".js",
        "js":         ".js",
        "typescript": ".ts",
        "html":       ".html",
        "css":        ".css",
        "go":         ".go",
        "rust":       ".rs",
        "cpp":        ".cpp",
        "c":          ".c",
        "ruby":       ".rb",
        "php":        ".php",
        "sql":        ".sql",
        "json":       ".json",
        "yaml":       ".yaml",
        "sh":         ".sh",
        "bash":       ".sh",
    }
    name_map = {
        "html": "index.html",
        "css":  "style.css",
        "js":   "script.js",
        "javascript": "script.js",
    }
    if language.lower() in name_map and index == 0:
        return name_map[language.lower()]

    ext = ext_map.get(language.lower(), ".txt")
    return f"file{index+1}{ext}"


def detect_folder_name(user_input: str) -> str | None:
    """
    Fix 4 — Smart folder detection from user request.
    Examples:
      'create a calculator app'       → 'calculator'
      'build a todo app named mytodo' → 'mytodo'
      'make a flask login project'    → 'flask-login'
      'create a weather app'          → 'weather'
    """
    lower = user_input.lower().strip()
    words = lower.split()

    # Explicit name keywords — highest priority
    # e.g. "named X", "called X", "name X", "folder X"
    for i, w in enumerate(words):
        if w in ("named", "called", "name", "folder", "as") and i + 1 < len(words):
            candidate = words[i + 1].strip(".,!?'\"/\\")
            if candidate and len(candidate) > 1:
                return candidate.replace(" ", "-")

    # App/project keyword patterns — extract subject
    # e.g. "create a calculator app" → "calculator"
    #      "build a todo list app"   → "todo-list"
    app_patterns = [
        r'(?:create|build|make|generate|write)\s+(?:a|an|the)?\s*([\w\s]+?)\s+(?:app|application|project|website|tool|program|game|system)',
        r'(?:create|build|make|generate|write)\s+(?:a|an|the)?\s*([\w\s]+?)\s+(?:with|using|in)\s+\w+',
        r'(?:a|an)\s+([\w\s]+?)\s+(?:app|application|project|website|tool|program)',
    ]

    import re as _re
    for pattern in app_patterns:
        match = _re.search(pattern, lower)
        if match:
            name = match.group(1).strip()
            # Clean up and slugify
            name = _re.sub(r'[^\w\s-]', '', name)
            name = name.strip().replace(' ', '-')
            if name and len(name) > 1 and name not in ('simple', 'basic', 'new', 'my'):
                return name

    return None


# ── Single file accept/reject ─────────────────────────────────────────────────

def offer_single_file(code: str, language: str, suggested_name: str):
    """Show one code block and ask accept/reject/always allow."""
    global ALWAYS_ALLOW

    # If always allow is on — just write silently
    if ALWAYS_ALLOW:
        console.print(
            f"\n  [#888888]Auto-saving[/] [#00ffcc]{suggested_name}[/] "
            f"[#444444](Always Allow is ON)[/]"
        )
        _write_file(suggested_name, code)
        return

    console.print()
    console.print(f"  [bold #ffdd57]◈ Code — {suggested_name}[/]")
    console.print("  [#333355]" + "─" * 50 + "[/]")

    try:
        syntax = Syntax(
            code, language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        console.print(syntax)
    except Exception:
        console.print(code)

    console.print()
    console.print(
        f"  Save as [bold #00ffcc]{suggested_name}[/] in "
        f"[#ffdd57]{WORKING_DIR}[/] ?"
    )
    console.print()
    console.print(
        "  [bold #00ffcc][A][/] Accept  "
        "[bold #ff6b6b][R][/] Reject  "
        "[bold #ffdd57][C][/] Custom name  "
        "[bold #00ff88][L][/] Always Allow"
    )
    console.print()

    try:
        choice = console.input("  Your choice (A/R/C/L): ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        return

    if choice == "R":
        console.print("  [#ff6b6b]✗ Skipped.[/]\n")
        return

    if choice == "C":
        try:
            suggested_name = console.input(
                "  Enter filename: "
            ).strip() or suggested_name
        except (KeyboardInterrupt, EOFError):
            pass

    if choice == "L":
        ALWAYS_ALLOW = True
        console.print(
            "  [bold #00ff88]✓ Always Allow ON[/] — "
            "[#888888]all future files will be saved automatically[/]\n"
        )

    if choice in ("A", "C", "L"):
        _write_file(suggested_name, code)


# ── Multi-file accept/reject ──────────────────────────────────────────────────

def offer_multi_file(blocks: list[dict], folder_name: str = None):
    """
    Show ALL files at once and ask ONE accept/reject for the whole project.
    """
    if not blocks:
        return

    console.print()
    console.print("  [bold #ffdd57]◈ Multi-File Project Detected[/]")
    console.print("  [#333355]" + "─" * 50 + "[/]")
    console.print()

    # Show summary table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold #00ffcc")
    table.add_column("File", style="#ffdd57")
    table.add_column("Language", style="#888888")
    table.add_column("Lines", style="#00ffcc")

    for block in blocks:
        lines = len(block["code"].splitlines())
        table.add_row(
            block["filename"],
            block["language"],
            str(lines)
        )

    console.print(table)

    if folder_name:
        console.print(
            f"  Will create folder: [bold #00ffcc]{folder_name}/[/] "
            f"in [#ffdd57]{WORKING_DIR}[/]"
        )
    else:
        console.print(
            f"  Will save all files in: [#ffdd57]{WORKING_DIR}[/]"
        )

    console.print()

    # Show each file's code
    for i, block in enumerate(blocks):
        console.print(
            f"\n  [bold #00ffcc]── {block['filename']} ──[/]"
        )
        try:
            syntax = Syntax(
                block["code"], block["language"],
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            console.print(syntax)
        except Exception:
            console.print(block["code"])

    console.print()
    console.print(
        "  [bold #00ffcc][A][/] Accept all  "
        "[bold #ff6b6b][R][/] Reject all  "
        "[bold #ffdd57][S][/] Select individually  "
        "[bold #00ff88][L][/] Always Allow"
    )
    console.print()

    try:
        choice = console.input("  Your choice (A/R/S/L): ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        return

    if choice == "R":
        console.print("  [#ff6b6b]✗ Project not saved.[/]\n")
        return

    if choice == "L":
        global ALWAYS_ALLOW
        ALWAYS_ALLOW = True
        console.print(
            "  [bold #00ff88]✓ Always Allow ON[/] — "
            "[#888888]saving all files now and auto-saving future files[/]\n"
        )
        choice = "A"  # fall through to save all

    if choice == "A":
        saved = 0
        for block in blocks:
            if folder_name:
                filepath = WORKING_DIR / folder_name / block["filename"]
            else:
                filepath = WORKING_DIR / block["filename"]
            _write_file_path(filepath, block["code"])
            saved += 1
        console.print(
            f"\n  [bold #00ffcc]✓ {saved} files saved "
            f"{'to ' + folder_name + '/' if folder_name else 'in current folder'}[/]\n"
        )

    elif choice == "S":
        # Let user accept/reject each file individually
        for block in blocks:
            console.print(
                f"\n  Save [bold #00ffcc]{block['filename']}[/]? "
                "[bold #00ffcc][Y][/] Yes  [bold #ff6b6b][N][/] No"
            )
            try:
                ans = console.input("  (Y/N): ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                continue

            if ans == "Y":
                if folder_name:
                    filepath = WORKING_DIR / folder_name / block["filename"]
                else:
                    filepath = WORKING_DIR / block["filename"]
                _write_file_path(filepath, block["code"])


# ── File writer ───────────────────────────────────────────────────────────────

def _write_file(filename: str, code: str):
    """Write a file to WORKING_DIR."""
    filepath = WORKING_DIR / Path(filename).name
    _write_file_path(filepath, code)


def _write_file_path(filepath: Path, code: str):
    """Write a file to an explicit path — warns if file already exists."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # ── Fix 5: Overwrite warning ──────────────────────────────────
        if filepath.exists():
            existing_size = filepath.stat().st_size
            console.print(
                f"\n  [bold #ffdd57]⚠ File already exists:[/] "
                f"[#aaaaaa]{filepath}[/] "
                f"[#444444]({existing_size} bytes)[/]"
            )
            console.print(
                "  [bold #00ffcc][O][/] Overwrite  "
                "[bold #ff6b6b][S][/] Skip  "
                "[bold #ffdd57][B][/] Backup and overwrite"
            )
            try:
                choice = console.input("  Your choice (O/S/B): ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                choice = "S"

            if choice == "S":
                console.print(f"  [#888888]Skipped {filepath.name}[/]")
                return

            if choice == "B":
                # Create .bak backup before overwriting
                backup = filepath.with_suffix(filepath.suffix + ".bak")
                filepath.rename(backup)
                console.print(
                    f"  [#888888]Backup saved:[/] [#444466]{backup.name}[/]"
                )

        filepath.write_text(code.strip(), encoding="utf-8")
        size = filepath.stat().st_size
        console.print(
            f"  [bold #00ffcc]✓[/] [#ffdd57]{filepath}[/] "
            f"[#888888]({size} bytes)[/]"
        )
    except Exception as e:
        console.print(f"  [#ff6b6b]✗ Error writing {filepath}: {e}[/]")


# ── Banner ────────────────────────────────────────────────────────────────────

def print_banner():
    console.print()
    console.print(
        "  ╔══════════════════════════════════════════════════════════╗",
        style="bold #00ffcc"
    )
    for line in [
        "  ║  ██╗   ██╗██╗████████╗ █████╗ ██╗                        ║",
        "  ║  ██║   ██║██║╚══██╔══╝██╔══██╗██║                        ║",
        "  ║  ██║   ██║██║   ██║   ███████║██║                        ║",
        "  ║  ╚██╗ ██╔╝██║   ██║   ██╔══██║██║                        ║",
        "  ║   ╚████╔╝ ██║   ██║   ██║  ██║███████╗                   ║",
        "  ║    ╚═══╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝                   ║",
    ]:
        console.print(line, style="bold #00ffcc")

    console.print(
        "  ║          AI-Powered Terminal Coding Assistant            ║",
        style="#ff6b6b"
    )
    console.print(
        "  ║          Powered by Groq · Built for Developers          ║",
        style="#888888"
    )
    console.print(
        "  ╚══════════════════════════════════════════════════════════╝",
        style="bold #00ffcc"
    )
    console.print()

    now     = datetime.now().strftime("%H:%M · %d %b %Y")
    project = get_project_name()
    branch  = get_git_branch()
    total   = get_total_file_count()
    lang    = context.detect_language(str(WORKING_DIR))

    console.print(
        f"  [#888888]Session[/]  [#00ffcc]{now}[/]   "
        f"[#888888]Project[/]  [#ffdd57]{project}{branch}[/]   "
        f"[#888888]Files[/]  [#ff6b6b]{total} total[/]   "
        f"[#888888]Lang[/]  [#00ffcc]{lang}[/]   "
        f"[#888888]Model[/]  [#00ffcc]llama-3.3-70b[/]"
    )
    console.print(
        f"  [#888888]Directory[/]  [#444466]{WORKING_DIR}[/]"
    )

    # Show memory status
    from vital.memory import discover_memory_files
    mem_files = discover_memory_files(str(WORKING_DIR))
    if mem_files:
        console.print(
            f"  [#888888]Memory[/]     [#00ff88]{len(mem_files)} VITAL.md file(s) loaded[/]"
        )
    else:
        console.print(
            "  [#888888]Memory[/]     [#444444]No VITAL.md found · "
            "run /memory add to create one[/]"
        )
    console.print()
    console.print(
        "  [#444444]Type a message · /help for commands · /exit to quit[/]"
    )
    console.print()


# ── Help ──────────────────────────────────────────────────────────────────────

def print_help():
    console.print()
    console.print("  [bold #00ffcc]VITAL COMMANDS[/]")
    console.print("  " + "─" * 50, style="#333355")
    console.print()
    for cmd, desc in COMMANDS.items():
        console.print(f"  [bold #ff6b6b]{cmd:<12}[/]  [#aaaaaa]{desc}[/]")
    console.print()
    console.print("  [#444444]Chat examples:[/]")
    console.print("  [#444444]  create a todo app with html css and js[/]")
    console.print("  [#444444]  build a flask login project named myapp[/]")
    console.print("  [#444444]  optimize my StudentDataCSV.java[/]")
    console.print("  [#444444]  explain this project[/]")
    console.print()
    console.print("  [#444444]Memory examples:[/]")
    console.print("  [#444444]  /memory init             create VITAL.md for this project[/]")
    console.print("  [#444444]  /memory add 'use TypeScript always'[/]")
    console.print("  [#444444]  /memory show             see what Vital remembers[/]")
    console.print()
    console.print("  [#444444]Session examples:[/]")
    console.print("  [#444444]  /history                 see this session's messages[/]")
    console.print("  [#444444]  /resume                  load a previous session[/]")
    console.print()


# ── Slash commands ────────────────────────────────────────────────────────────

def handle_slash_command(user_input: str):
    global current_session
    parts = user_input.strip().split()
    cmd   = parts[0].lower()
    args  = parts[1:] if len(parts) > 1 else []

    if cmd in ("/exit", "/quit"):
        console.print()
        console.print("  [#00ffcc]◈[/]  [#aaaaaa]Vital session ended. Happy coding![/]")
        console.print()
        sys.exit(0)

    elif cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()

    elif cmd == "/help":
        print_help()

    elif cmd == "/agent":
        request = " ".join(args) if args else None
        if not request:
            try:
                request = console.input(
                    "\n  [#ffdd57]What do you want me to build?[/] "
                ).strip()
            except (KeyboardInterrupt, EOFError):
                return
        if request:
            agent = VitalAgent(
                working_dir = WORKING_DIR,
                ai_ask_fn   = ai_engine.ask
            )
            agent.run(request)

    elif cmd == "/model":
        console.print(
            f"\n  [#888888]Model:[/] [bold #00ffcc]llama-3.3-70b-versatile[/] "
            f"[#888888]via Groq[/]\n"
        )

    elif cmd == "/providers":
        from vital.providers import _show_provider_status, edit_providers
        _show_provider_status()
        edit_providers()

    elif cmd == "/allowoff":
        global ALWAYS_ALLOW
        ALWAYS_ALLOW = False
        console.print(
            "\n  [bold #ff6b6b]✓ Always Allow OFF[/] — "
            "[#888888]Vital will ask before saving files again[/]\n"
        )

    elif cmd == "/history":
        if "current_session" in globals():
            current_session.show_history()
        else:
            console.print("\n  [#888888]No session active.[/]\n")

    elif cmd == "/resume":
        new_session = resume_session()
        if new_session:
            current_session = new_session

    elif cmd == "/memory":
        sub  = args[0].lower() if args else "show"
        rest = " ".join(args[1:]) if len(args) > 1 else ""

        if sub == "show":
            memory_show(str(WORKING_DIR))

        elif sub == "add":
            is_global = "--global" in args
            fact_args = [a for a in args[1:] if a != "--global"]
            fact      = " ".join(fact_args)
            if not fact:
                fact = console.input(
                    "  [#ffdd57]Enter fact/rule to remember:[/] "
                ).strip()
            if fact:
                memory_add(fact, global_mem=is_global, start_dir=str(WORKING_DIR))

        elif sub == "edit":
            is_global = "--global" in args
            memory_edit(global_mem=is_global, start_dir=str(WORKING_DIR))

        elif sub == "clear":
            is_global = "--global" in args
            memory_clear(global_mem=is_global, start_dir=str(WORKING_DIR))

        elif sub == "refresh":
            memory_refresh(str(WORKING_DIR))

        elif sub == "init":
            init_project_memory(str(WORKING_DIR))

        else:
            console.print(
                "\n  [bold #00ffcc]Memory commands:[/]\n"
                "  [#ffdd57]/memory show[/]              Show all loaded memory\n"
                "  [#ffdd57]/memory add <fact>[/]        Add to project memory\n"
                "  [#ffdd57]/memory add --global <fact>[/] Add to global memory\n"
                "  [#ffdd57]/memory edit[/]              Edit project VITAL.md\n"
                "  [#ffdd57]/memory edit --global[/]     Edit global VITAL.md\n"
                "  [#ffdd57]/memory refresh[/]           Reload memory files\n"
                "  [#ffdd57]/memory clear[/]             Clear project memory\n"
                "  [#ffdd57]/memory init[/]              Create VITAL.md for this project\n"
            )

    elif cmd == "/context":
        console.print("\n  [#888888]Scanning...[/]\n")
        stats = context.count_all_files(str(WORKING_DIR))
        lang  = context.detect_language(str(WORKING_DIR))
        console.print(
            f"  [#888888]Directory:[/]   [#ffdd57]{WORKING_DIR}[/]\n"
            f"  [#888888]Language:[/]    [#00ffcc]{lang}[/]\n"
            f"  [#888888]Total files:[/] [#ff6b6b]{stats['total']}[/]\n"
        )
        for ext, count in sorted(
            stats["by_type"].items(), key=lambda x: -x[1]
        )[:15]:
            bar = "█" * min(count, 25)
            console.print(
                f"  [#444466]{ext:<15}[/] [#00ffcc]{bar}[/] [#888888]{count}[/]"
            )
        console.print()

    elif cmd == "/debug":
        file_arg = args[0] if args else None
        console.print()
        if file_arg:
            from vital.commands.debug import run
            run(file=file_arg, command=None, error=None)
        else:
            error = console.input("  [#ffdd57]Paste your error:[/] ")
            from vital.commands.debug import run
            run(file=None, command=None, error=error)

    elif cmd == "/explain":
        from vital.commands.explain import run
        run(path=args[0] if args else ".", simple=False)

    elif cmd == "/fix":
        if not args:
            console.print("  [#ff6b6b]Usage: /fix <filename>[/]\n")
            return
        from vital.commands.fix import run
        run(file=args[0], issue=None)

    elif cmd == "/doc":
        from vital.commands.doc import run
        run(path=args[0] if args else ".", output=None)

    elif cmd == "/commit":
        from vital.commands.commit import run
        run(push=False)

    elif cmd == "/refactor":
        if not args:
            console.print("  [#ff6b6b]Usage: /refactor <filename>[/]\n")
            return
        from vital.commands.refactor import run
        run(file=args[0], goal=None)

    elif cmd == "/test":
        if not args:
            console.print("  [#ff6b6b]Usage: /test <filename>[/]\n")
            return
        from vital.commands.test import run
        run(file=args[0], output=None, framework="pytest")

    elif cmd == "/init":
        if not args:
            console.print("  [#ff6b6b]Usage: /init <project-type>[/]\n")
            return
        from vital.commands.init import run
        run(project=" ".join(args), name=None)

    else:
        console.print(
            f"  [#ff6b6b]Unknown:[/] [#aaaaaa]{cmd}[/]  "
            f"[#444444]→ /help to see all commands[/]\n"
        )


# ── Prompt ────────────────────────────────────────────────────────────────────

def get_prompt_text():
    project = get_project_name()
    branch  = get_git_branch()
    return HTML(
        f'<ansi-bright-black> {project}{branch} </ansi-bright-black>'
        f'<ansicyan><b> ◈ vital</b></ansicyan>'
        f'<ansi-bright-black> › </ansi-bright-black> '
    )


def get_toolbar():
    status = (
        " · <b style='color:#00ff88'>Always Allow ON</b>"
        if ALWAYS_ALLOW else ""
    )
    return HTML(
        '  <b>/help</b> commands · '
        '<b>/context</b> project info · '
        '<b>/clear</b> screen · '
        '<b>/exit</b> quit'
        + status
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_interactive(resume: bool = False):
    global current_session
    if not get_api_key():
        console.print(
            "\n  [#ff6b6b]✗[/]  No API key. Run [bold]vital setup[/bold] first.\n"
        )
        sys.exit(1)

    # ── Cleanup old sessions on startup ──────────────────────────────
    cleanup_old_sessions()

    # ── Session setup ─────────────────────────────────────────────────
    if resume:
        current_session = resume_session()
        if not current_session:
            current_session = Session(working_dir=str(WORKING_DIR))
    else:
        current_session = Session(working_dir=str(WORKING_DIR))

    # ── Fix 7: Lazy memory load — fast startup, load only when needed ─
    # Memory is loaded once here and reused — not re-scanned every message
    project_memory = load_memory(str(WORKING_DIR))

    # Project context is NOT scanned at startup — only when first needed
    _project_context_cache = {"value": None, "loaded": False}

    def get_project_context() -> str:
        """Lazy load project context — scanned only on first coding request."""
        if not _project_context_cache["loaded"]:
            try:
                _project_context_cache["value"]  = context.build_context(str(WORKING_DIR))
                _project_context_cache["loaded"] = True
            except Exception:
                _project_context_cache["value"]  = f"Directory: {WORKING_DIR}"
                _project_context_cache["loaded"] = True
        return _project_context_cache["value"] or ""

    os.system("cls" if os.name == "nt" else "clear")
    print_banner()

    session = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        style=STYLE,
        bottom_toolbar=get_toolbar,
        mouse_support=False,
    )

    while True:
        try:
            user_input = session.prompt(get_prompt_text).strip()
            if not user_input:
                continue

            # Slash commands
            if user_input.startswith("/"):
                handle_slash_command(user_input)
                continue

            # ── Chat ─────────────────────────────────────────────────────
            console.print()
            console.print("  [bold #00ffcc]◈ Vital[/]\n")

            # Save user message to session
            current_session.add("user", user_input)

            # ── Agent Mode — full autonomous project building ─────────────
            if is_agent_request(user_input):
                agent = VitalAgent(
                    working_dir = WORKING_DIR,
                    ai_ask_fn   = ai_engine.ask
                )
                agent.run(user_input)
                current_session.add("assistant", f"[Agent built: {user_input}]")
                console.print()
                console.print("  " + "·" * 55, style="#222244")
                console.print()
                continue

            mentioned_file  = detect_mentioned_file(user_input)
            multi_file_mode = is_multi_file_request(user_input)
            casual          = is_casual_message(user_input)

            # Build project context — lazy loaded, skip for casual chat
            try:
                if casual:
                    proj_ctx = None
                elif mentioned_file:
                    console.print(f"  [dim]Reading {mentioned_file}...[/dim]\n")
                    file_ctx = context.get_file_context(mentioned_file)
                    proj_ctx = f"Working directory: {WORKING_DIR}\n\n{file_ctx}"
                else:
                    proj_ctx = get_project_context()
            except Exception:
                proj_ctx = None

            # Build conversation history (sliding window)
            history_window = current_session.get_window()
            if history_window and history_window[-1]["role"] == "user":
                history_window = history_window[:-1]
            history_text = ""
            if history_window:
                lines = []
                for m in history_window[-8:]:
                    role = "User" if m["role"] == "user" else "Vital"
                    lines.append(f"{role}: {m['content'][:300]}")
                history_text = "\n".join(lines)

            # Memory block — injected into every prompt
            mem_block = (
                f"Project Memory (follow these rules strictly):\n{project_memory}\n"
                if project_memory else ""
            )
            # History block
            hist_block = (
                f"Recent conversation:\n{history_text}\n"
                if history_text else ""
            )

            # Build prompt
            if casual:
                prompt = f"""You are Vital, an AI assistant focused on coding, education and knowledge.
Answer naturally. For political/conflict topics politely redirect to coding or education.
{hist_block}
User: {user_input}
"""
            elif multi_file_mode:
                prompt = f"""You are Vital, an expert AI coding assistant.
When creating multiple files: put each in its own code block with filename on the line before it.
Always create complete, working, production-quality code.

{mem_block}{hist_block}Working directory: {WORKING_DIR}
Project context:
{(proj_ctx or '')[:3000]}

Developer request: {user_input}
"""
            else:
                prompt = f"""You are Vital, an expert AI coding assistant.
Be concise and practical. For political/conflict topics politely redirect.

{mem_block}{hist_block}Working directory: {WORKING_DIR}
Project context:
{(proj_ctx or '')[:3000]}

Developer request: {user_input}
"""
            # ── Get current provider name for spinner ─────────────────────
            try:
                from vital.providers import load_config, get_default_provider, PROVIDER_INFO
                cfg      = load_config()
                prov_id  = get_default_provider()
                prov_name = PROVIDER_INFO.get(prov_id, {}).get("name", prov_id) if prov_id else None
            except Exception:
                prov_name = None

            # ── Start spinner → ask AI → stop spinner ─────────────────────
            spinner.start(provider=prov_name)
            try:
                response = ai_engine.ask(prompt)
            finally:
                spinner.stop()

            # Save AI response to session
            current_session.add("assistant", response)

            # ── File handling ─────────────────────────────────────────────

            # Always extract blocks first — never skip this
            blocks = extract_code_blocks(response)

            # For casual/general messages — skip file saving
            if casual:
                console.print()
                console.print("  " + "·" * 55, style="#222244")
                console.print()
                continue

            # Filter out bash/shell/tiny blocks
            saveable = []
            for i, block in enumerate(blocks):
                lang = block["language"].lower()
                code = block["code"].strip()
                if lang in ("bash", "shell", "sh", "cmd", "text", ""):
                    continue
                if len(code.splitlines()) < 3:
                    continue
                # Assign filename if missing
                if not block["filename"]:
                    block["filename"] = guess_filename(lang, i)
                saveable.append(block)

            if len(saveable) > 1:
                # ── Fix 4: Smart folder detection ────────────────────────
                folder = detect_folder_name(user_input)
                if folder:
                    console.print(
                        f"\n  [#888888]Detected project folder:[/] "
                        f"[bold #00ffcc]{folder}/[/]"
                    )
                offer_multi_file(saveable, folder_name=folder)

            elif len(saveable) == 1:
                block = saveable[0]
                offer_single_file(
                    block["code"],
                    block["language"],
                    block["filename"]
                )

            console.print()
            console.print("  " + "·" * 55, style="#222244")
            console.print()

        except KeyboardInterrupt:
            console.print("\n  [#444466]Use /exit to quit[/]\n")
            continue

        except EOFError:
            console.print("\n  [#00ffcc]◈[/]  [#aaaaaa]Session ended.[/]\n")
            break

        except Exception as e:
            # Fix 9: Friendly error messages
            try:
                from vital.main import friendly_error
                msg = friendly_error(e)
            except Exception:
                msg = str(e)
            if msg:
                console.print(f"\n  [bold #ff6b6b]✗[/]  {msg}\n")
                console.print(
                    "  [#444444]If this keeps happening, try /providers to switch AI or "
                    "run vital setup to reconfigure.[/]\n"
                )
            continue