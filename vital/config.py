import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt

console = Console()

ENV_FILE = Path.home() / ".vital_env"


def get_api_key() -> str:
    """Get API key — checks providers config first, then env."""
    # Try new multi-provider system first
    try:
        from vital.providers import get_api_key as providers_get_key
        from vital.providers import get_default_provider
        default = get_default_provider()
        if default:
            key = providers_get_key(default)
            if key:
                return key
    except Exception:
        pass

    # Fallback to old .vital_env file
    load_dotenv(ENV_FILE)
    load_dotenv()
    return os.getenv("GROQ_API_KEY")


def setup():
    """Launch the full multi-provider setup wizard."""
    from vital.providers import setup_providers
    setup_providers()


def require_api_key() -> str:
    """Get API key or exit with helpful message."""
    key = get_api_key()
    if not key:
        console.print(
            "\n  [#ff6b6b]No API key found.[/] "
            "Run [bold]vital setup[/bold] to configure your providers.\n"
        )
        raise SystemExit(1)
    return key
