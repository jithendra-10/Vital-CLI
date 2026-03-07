"""
session.py — Vital's Session Memory Manager
Saves conversation history to ~/.vital/sessions/<session-id>.json
Supports resume, history view, and auto-cleanup of old sessions.
"""

import json
import uuid
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# ── Paths ─────────────────────────────────────────────────────────────────────
VITAL_DIR      = Path.home() / ".vital"
SESSIONS_DIR   = VITAL_DIR / "sessions"
LAST_FILE      = VITAL_DIR / "last_session.txt"

# ── Config ────────────────────────────────────────────────────────────────────
MAX_HISTORY    = 15    # messages kept in sliding window sent to AI
KEEP_DAYS      = 30    # auto-delete sessions older than this
MAX_SAVED_SESSIONS = 50  # max sessions to keep on disk


def _ensure_dirs():
    VITAL_DIR.mkdir(exist_ok=True)
    SESSIONS_DIR.mkdir(exist_ok=True)


# ── Session class ─────────────────────────────────────────────────────────────

class Session:
    """
    Manages one conversation session.
    Keeps full history in memory, sliding window for AI context.
    """

    def __init__(self, session_id: str = None, working_dir: str = None):
        _ensure_dirs()
        self.id          = session_id or str(uuid.uuid4())[:8]
        self.working_dir = working_dir or str(Path.cwd())
        self.messages    = []   # full history
        self.started_at  = datetime.now().isoformat()
        self.filepath    = SESSIONS_DIR / f"{self.id}.json"

        # Load existing session if resuming
        if session_id and self.filepath.exists():
            self._load()

    def add(self, role: str, content: str):
        """Add a message to history and auto-save."""
        self.messages.append({
            "role":      role,       # "user" or "assistant"
            "content":   content,
            "timestamp": datetime.now().isoformat()
        })
        self._save()

    def get_window(self) -> list[dict]:
        """
        Return last MAX_HISTORY messages for AI context.
        This is the sliding window — keeps token usage lean.
        """
        recent = self.messages[-MAX_HISTORY:]
        # Return in format AI expects: {role, content}
        return [
            {"role": m["role"], "content": m["content"]}
            for m in recent
        ]

    def clear(self):
        """Clear current session messages."""
        self.messages = []
        self._save()
        console.print("\n  [#00ffcc]✓ Session memory cleared.[/]\n")

    def show_history(self, last_n: int = 10):
        """Display last N messages nicely."""
        if not self.messages:
            console.print("\n  [#888888]No messages in this session yet.[/]\n")
            return

        console.print()
        console.print("  [bold #00ffcc]◈ Session History[/]")
        console.print("  [#333355]" + "─" * 50 + "[/]\n")

        recent = self.messages[-last_n:]
        for msg in recent:
            role      = msg["role"]
            content   = msg["content"][:200]  # truncate long messages
            timestamp = msg.get("timestamp", "")[:16].replace("T", " ")

            if role == "user":
                console.print(
                    f"  [bold #ffdd57]You[/] [#444444]{timestamp}[/]"
                )
                console.print(f"  [#ffffff]{content}[/]\n")
            else:
                console.print(
                    f"  [bold #00ffcc]Vital[/] [#444444]{timestamp}[/]"
                )
                console.print(f"  [#aaaaaa]{content}[/]\n")

    def _save(self):
        """Save session to disk."""
        data = {
            "id":          self.id,
            "working_dir": self.working_dir,
            "started_at":  self.started_at,
            "updated_at":  datetime.now().isoformat(),
            "messages":    self.messages,
        }
        self.filepath.write_text(json.dumps(data, indent=2))

        # Update last session pointer
        LAST_FILE.write_text(self.id)

    def _load(self):
        """Load session from disk."""
        try:
            data             = json.loads(self.filepath.read_text())
            self.messages    = data.get("messages", [])
            self.working_dir = data.get("working_dir", self.working_dir)
            self.started_at  = data.get("started_at", self.started_at)
        except Exception as e:
            console.print(f"  [#ff6b6b]Could not load session: {e}[/]")


# ── Session management functions ──────────────────────────────────────────────

def get_last_session_id() -> str | None:
    """Get ID of most recent session."""
    if LAST_FILE.exists():
        return LAST_FILE.read_text().strip()
    return None


def list_sessions(limit: int = 10) -> list[dict]:
    """List recent sessions sorted by last updated."""
    _ensure_dirs()
    sessions = []

    for f in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "id":          data.get("id", f.stem),
                "working_dir": data.get("working_dir", ""),
                "started_at":  data.get("started_at", ""),
                "updated_at":  data.get("updated_at", ""),
                "msg_count":   len(data.get("messages", [])),
            })
        except Exception:
            continue

    # Sort by updated_at descending
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions[:limit]


def show_sessions():
    """Display all saved sessions in a table."""
    sessions = list_sessions()

    if not sessions:
        console.print("\n  [#888888]No saved sessions found.[/]\n")
        return

    console.print()
    console.print("  [bold #00ffcc]◈ Saved Sessions[/]")
    console.print("  [#333355]" + "─" * 55 + "[/]\n")

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold #00ffcc"
    )
    table.add_column("#",          style="#444466", width=3)
    table.add_column("Session ID", style="#ffdd57", width=10)
    table.add_column("Project",    style="#aaaaaa", width=20)
    table.add_column("Messages",   style="#00ffcc", width=8)
    table.add_column("Last Used",  style="#888888", width=18)

    for i, s in enumerate(sessions, 1):
        project  = Path(s["working_dir"]).name
        updated  = s.get("updated_at", "")[:16].replace("T", " ")
        table.add_row(
            str(i),
            s["id"],
            project,
            str(s["msg_count"]),
            updated
        )

    console.print(table)
    console.print(
        "  [#444444]Use 'vital --resume' or '/resume' to load a session[/]\n"
    )


def resume_session() -> Session | None:
    """
    Interactively pick a session to resume.
    Returns loaded Session or None.
    """
    sessions = list_sessions()

    if not sessions:
        console.print("\n  [#888888]No saved sessions to resume.[/]\n")
        return None

    show_sessions()

    try:
        choice = console.input(
            "  [#ffdd57]Enter session number to resume (or Enter to skip):[/] "
        ).strip()
    except (KeyboardInterrupt, EOFError):
        return None

    if not choice:
        return None

    try:
        idx     = int(choice) - 1
        sess_id = sessions[idx]["id"]
        session = Session(session_id=sess_id)
        console.print(
            f"\n  [bold #00ffcc]✓ Resumed session {sess_id}[/] "
            f"[#888888]({len(session.messages)} messages loaded)[/]\n"
        )
        return session
    except (ValueError, IndexError):
        console.print("  [#ff6b6b]Invalid choice.[/]\n")
        return None


def cleanup_old_sessions():
    """Delete sessions older than KEEP_DAYS days."""
    _ensure_dirs()
    cutoff   = datetime.now() - timedelta(days=KEEP_DAYS)
    deleted  = 0

    for f in SESSIONS_DIR.glob("*.json"):
        try:
            data    = json.loads(f.read_text())
            updated = datetime.fromisoformat(
                data.get("updated_at", "2000-01-01")
            )
            if updated < cutoff:
                f.unlink()
                deleted += 1
        except Exception:
            continue

    # Also enforce max sessions limit
    sessions = list_sessions(limit=1000)
    if len(sessions) > MAX_SAVED_SESSIONS:
        for s in sessions[MAX_SAVED_SESSIONS:]:
            f = SESSIONS_DIR / f"{s['id']}.json"
            if f.exists():
                f.unlink()
                deleted += 1

    return deleted
