"""
providers.py — Vital's Multi-Provider AI Engine
Supports: Groq, OpenAI, Anthropic (Claude), Google Gemini
Users can add any combination of keys they have.
"""

import os
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()

# ── Config file location ──────────────────────────────────────────────────────
CONFIG_FILE = Path.home() / ".vital_providers.json"

# ── Provider definitions ──────────────────────────────────────────────────────
PROVIDER_INFO = {
    "groq": {
        "name":        "Groq",
        "color":       "#00ffcc",
        "description": "Ultra-fast inference. Free tier available.",
        "signup_url":  "https://console.groq.com",
        "key_prefix":  "gsk_",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        "strengths": "Speed, code generation, general tasks",
    },
    "openai": {
        "name":        "OpenAI (ChatGPT)",
        "color":       "#74aa9c",
        "description": "GPT-4o and GPT-4 Turbo. Best for complex reasoning.",
        "signup_url":  "https://platform.openai.com",
        "key_prefix":  "sk-",
        "default_model": "gpt-4o",
        "models": [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "strengths": "Architecture planning, complex reasoning",
    },
    "anthropic": {
        "name":        "Anthropic (Claude)",
        "color":       "#cc785c",
        "description": "Claude 3.5 Sonnet. Best for code review and quality.",
        "signup_url":  "https://console.anthropic.com",
        "key_prefix":  "sk-ant-",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229",
        ],
        "strengths": "Code review, security, documentation",
    },
    "gemini": {
        "name":        "Google Gemini",
        "color":       "#4285f4",
        "description": "Gemini 1.5 Pro. Best for large context and explanation.",
        "signup_url":  "https://aistudio.google.com",
        "key_prefix":  "AIza",
        "default_model": "gemini-1.5-pro",
        "models": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
        ],
        "strengths": "Large context, explanation, documentation",
    },
}


# ── Config load/save ──────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load provider config from file."""
    if not CONFIG_FILE.exists():
        return {"providers": {}, "default": None, "council_mode": False}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except Exception:
        return {"providers": {}, "default": None, "council_mode": False}


def save_config(config: dict):
    """Save provider config to file."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_configured_providers() -> dict:
    """Return only providers that have API keys configured."""
    config = load_config()
    return config.get("providers", {})


def get_default_provider() -> str | None:
    """Get the default provider name."""
    config = load_config()
    providers = config.get("providers", {})
    default = config.get("default")

    # If default is set and still configured, use it
    if default and default in providers:
        return default

    # Otherwise use first available
    if providers:
        return list(providers.keys())[0]

    return None


def get_api_key(provider: str) -> str | None:
    """Get API key for a specific provider."""
    config = load_config()
    return config.get("providers", {}).get(provider, {}).get("key")


# ── Setup wizard ──────────────────────────────────────────────────────────────

def setup_providers():
    """
    Interactive setup wizard.
    Users can add any combination of providers they have keys for.
    """
    config = load_config()
    existing = config.get("providers", {})

    console.print()
    console.print("  [bold #00ffcc]◈ Vital Provider Setup[/bold #00ffcc]")
    console.print("  [#333355]" + "─" * 55 + "[/]")
    console.print()
    console.print(
        "  [#888888]Add API keys for any AI providers you have.\n"
        "  You can add 1, 2, 3, or all of them.\n"
        "  Skip any you don't have by pressing Enter.[/]"
    )
    console.print()

    # Show currently configured providers
    if existing:
        console.print("  [#ffdd57]Currently configured:[/]")
        for p, data in existing.items():
            info = PROVIDER_INFO.get(p, {})
            console.print(
                f"  [bold {info.get('color','#ffffff')}]✓ {info.get('name', p)}[/]  "
                f"[#888888]{data.get('model', '')}[/]"
            )
        console.print()

    # Go through each provider
    for provider_id, info in PROVIDER_INFO.items():
        color = info["color"]
        name  = info["name"]
        url   = info["signup_url"]

        # Show provider card
        console.print(
            f"  [bold {color}]◈ {name}[/]  "
            f"[#888888]{info['description']}[/]"
        )
        console.print(f"  [#444444]Get key at: {url}[/]")

        current_key = existing.get(provider_id, {}).get("key", "")
        if current_key:
            masked = current_key[:8] + "..." + current_key[-4:]
            console.print(f"  [#444444]Current key: {masked}[/]")

        # Ask for key
        prompt_text = (
            f"  [#ffdd57]Enter {name} API key "
            f"({'update or ' if current_key else ''}press Enter to skip)[/]"
        )
        key = Prompt.ask(prompt_text, default="", password=True)
        key = key.strip()

        if key:
            # Validate key prefix
            prefix = info.get("key_prefix", "")
            if prefix and not key.startswith(prefix):
                console.print(
                    f"  [#ff6b6b]Warning: Key doesn't start with '{prefix}'. "
                    f"Double check it's correct.[/]"
                )
                if not Confirm.ask("  Save anyway?", default=False):
                    console.print("  [#888888]Skipped.[/]\n")
                    continue

            # Pick model
            models = info["models"]
            console.print(f"\n  [#888888]Available models for {name}:[/]")
            for i, m in enumerate(models, 1):
                console.print(f"  [#444466]  [{i}] {m}[/]")

            model_choice = Prompt.ask(
                "  [#ffdd57]Choose model number[/]",
                default="1"
            )
            try:
                chosen_model = models[int(model_choice) - 1]
            except (ValueError, IndexError):
                chosen_model = info["default_model"]

            # Save
            if "providers" not in config:
                config["providers"] = {}

            config["providers"][provider_id] = {
                "key":   key,
                "model": chosen_model,
            }
            console.print(
                f"  [bold {color}]✓ {name} configured with {chosen_model}[/]\n"
            )
        elif current_key:
            console.print(f"  [#888888]Keeping existing {name} key.[/]\n")
        else:
            console.print(f"  [#444444]Skipped {name}.[/]\n")

    # Set default provider
    configured = list(config.get("providers", {}).keys())
    if len(configured) > 1:
        console.print("  [bold #00ffcc]Which provider should be your default?[/]")
        for i, p in enumerate(configured, 1):
            info = PROVIDER_INFO.get(p, {})
            console.print(
                f"  [#444466]  [{i}] {info.get('name', p)} "
                f"— {info.get('strengths', '')}[/]"
            )
        choice = Prompt.ask("  [#ffdd57]Choose default[/]", default="1")
        try:
            config["default"] = configured[int(choice) - 1]
        except (ValueError, IndexError):
            config["default"] = configured[0]
    elif configured:
        config["default"] = configured[0]

    # Council mode
    if len(configured) > 1:
        console.print()
        console.print(
            "  [bold #00ff88]◈ Council Mode[/bold #00ff88]  "
            "[#888888]Use multiple AIs together for better results[/]"
        )
        council = Confirm.ask(
            "  [#ffdd57]Enable Council Mode?[/]",
            default=True
        )
        config["council_mode"] = council
    else:
        config["council_mode"] = False

    save_config(config)

    # Show summary
    console.print()
    console.print("  [bold #00ffcc]✓ Setup complete![/]")
    _show_provider_status()
    console.print()


def edit_providers():
    """Quick edit — add/remove/change specific providers."""
    config = load_config()
    existing = config.get("providers", {})

    console.print()
    console.print("  [bold #00ffcc]◈ Edit Providers[/]")
    console.print("  [#333355]" + "─" * 40 + "[/]\n")
    console.print(
        "  [bold #00ffcc][A][/] Add/Update a provider  "
        "[bold #ff6b6b][R][/] Remove a provider  "
        "[bold #ffdd57][D][/] Change default  "
        "[bold #888888][Q][/] Quit\n"
    )

    choice = console.input("  Your choice (A/R/D/Q): ").strip().upper()

    if choice == "A":
        setup_providers()

    elif choice == "R":
        if not existing:
            console.print("  [#888888]No providers configured.[/]\n")
            return
        console.print("\n  [#888888]Configured providers:[/]")
        for i, (p, data) in enumerate(existing.items(), 1):
            info = PROVIDER_INFO.get(p, {})
            console.print(f"  [{i}] {info.get('name', p)}")
        idx = Prompt.ask("  Which to remove? (number)", default="")
        try:
            provider_to_remove = list(existing.keys())[int(idx) - 1]
            del config["providers"][provider_to_remove]
            if config.get("default") == provider_to_remove:
                remaining = list(config["providers"].keys())
                config["default"] = remaining[0] if remaining else None
            save_config(config)
            console.print(
                f"  [#ff6b6b]✓ {provider_to_remove} removed.[/]\n"
            )
        except (ValueError, IndexError):
            console.print("  [#888888]Invalid choice.[/]\n")

    elif choice == "D":
        if not existing:
            console.print("  [#888888]No providers configured.[/]\n")
            return
        console.print("\n  [#888888]Choose new default:[/]")
        for i, p in enumerate(existing.keys(), 1):
            info = PROVIDER_INFO.get(p, {})
            console.print(f"  [{i}] {info.get('name', p)}")
        idx = Prompt.ask("  Choose (number)", default="1")
        try:
            config["default"] = list(existing.keys())[int(idx) - 1]
            save_config(config)
            console.print(
                f"  [bold #00ffcc]✓ Default set to {config['default']}[/]\n"
            )
        except (ValueError, IndexError):
            console.print("  [#888888]Invalid choice.[/]\n")

    elif choice == "Q":
        return


# ── Status display ─────────────────────────────────────────────────────────────

def _show_provider_status():
    """Show a table of all configured providers."""
    config   = load_config()
    existing = config.get("providers", {})
    default  = config.get("default")
    council  = config.get("council_mode", False)

    console.print()
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold #00ffcc",
        title="[bold #00ffcc]Vital Providers[/]",
        title_justify="left"
    )
    table.add_column("Provider",  style="#ffdd57")
    table.add_column("Model",     style="#aaaaaa")
    table.add_column("Status",    style="#00ffcc")
    table.add_column("Strengths", style="#888888")

    for provider_id, info in PROVIDER_INFO.items():
        if provider_id in existing:
            data    = existing[provider_id]
            model   = data.get("model", info["default_model"])
            is_def  = "★ Default" if provider_id == default else "✓ Active"
            status  = f"[bold #00ff88]{is_def}[/]"
        else:
            model  = "—"
            status = "[#444444]Not configured[/]"

        table.add_row(
            info["name"],
            model,
            status,
            info["strengths"]
        )

    console.print(table)

    if council:
        console.print(
            "  [bold #00ff88]◈ Council Mode: ON[/]  "
            "[#888888]Multiple AIs will collaborate[/]\n"
        )
    else:
        console.print(
            f"  [#888888]Default provider: "
            f"[bold #00ffcc]{PROVIDER_INFO.get(default, {}).get('name', default)}[/]\n"
        )


# ── Unified ask function ───────────────────────────────────────────────────────

def ask(
    prompt: str,
    provider: str = None,
    stream: bool = True
) -> str:
    """
    Ask a single provider. Uses default if none specified.
    """
    config    = load_config()
    providers = config.get("providers", {})

    if not providers:
        console.print(
            "\n  [#ff6b6b]No providers configured.[/] "
            "Run [bold]vital setup[/bold] first.\n"
        )
        raise SystemExit(1)

    # Pick provider
    target = provider or config.get("default") or list(providers.keys())[0]

    if target not in providers:
        console.print(
            f"\n  [#ff6b6b]Provider '{target}' not configured.[/] "
            f"Run [bold]vital setup[/bold] to add it.\n"
        )
        raise SystemExit(1)

    key   = providers[target]["key"]
    model = providers[target]["model"]

    return _call_provider(target, key, model, prompt, stream)


def council_ask(prompt: str, task_type: str = "general") -> str:
    """
    Council Mode — route to the best provider based on task type,
    or combine multiple providers if all are available.
    """
    config    = load_config()
    providers = config.get("providers", {})

    if not providers:
        console.print(
            "\n  [#ff6b6b]No providers configured.[/] "
            "Run [bold]vital setup[/bold] first.\n"
        )
        raise SystemExit(1)

    # Task routing — pick best provider for the task
    routing = {
        "code":          ["groq", "openai", "anthropic", "gemini"],
        "review":        ["anthropic", "openai", "gemini", "groq"],
        "architecture":  ["openai", "anthropic", "gemini", "groq"],
        "explain":       ["gemini", "anthropic", "openai", "groq"],
        "fast":          ["groq", "gemini", "openai", "anthropic"],
        "general":       ["groq", "openai", "anthropic", "gemini"],
    }

    order = routing.get(task_type, routing["general"])

    # Pick first available from preference order
    for preferred in order:
        if preferred in providers:
            key   = providers[preferred]["key"]
            model = providers[preferred]["model"]
            info  = PROVIDER_INFO.get(preferred, {})
            console.print(
                f"  [#444444]Using {info.get('name', preferred)} "
                f"({model}) for {task_type}...[/]\n"
            )
            return _call_provider(preferred, key, model, prompt, stream=True)

    # Fallback to default
    return ask(prompt)


# ── Provider callers ──────────────────────────────────────────────────────────

def _call_provider(
    provider: str,
    key: str,
    model: str,
    prompt: str,
    stream: bool = True
) -> str:
    """Route to the correct provider's API."""
    try:
        if provider == "groq":
            return _call_groq(key, model, prompt, stream)
        elif provider == "openai":
            return _call_openai(key, model, prompt, stream)
        elif provider == "anthropic":
            return _call_anthropic(key, model, prompt, stream)
        elif provider == "gemini":
            return _call_gemini(key, model, prompt, stream)
        else:
            console.print(f"  [#ff6b6b]Unknown provider: {provider}[/]")
            return ""
    except Exception as e:
        console.print(f"  [#ff6b6b]Error calling {provider}: {e}[/]")
        # Try fallback to another provider
        return _try_fallback(provider, prompt)


def _try_fallback(failed_provider: str, prompt: str) -> str:
    """If a provider fails, try the next available one."""
    config    = load_config()
    providers = config.get("providers", {})
    for p in providers:
        if p != failed_provider:
            console.print(
                f"  [#ffdd57]Falling back to {PROVIDER_INFO.get(p,{}).get('name',p)}...[/]\n"
            )
            key   = providers[p]["key"]
            model = providers[p]["model"]
            return _call_provider(p, key, model, prompt, stream=True)
    return ""


def _call_groq(key: str, model: str, prompt: str, stream: bool) -> str:
    from groq import Groq
    client   = Groq(api_key=key)
    messages = [{"role": "user", "content": prompt}]
    if stream:
        return _stream_response_groq(client, model, messages)
    else:
        r = client.chat.completions.create(model=model, messages=messages)
        return r.choices[0].message.content


def _stream_response_groq(client, model, messages) -> str:
    full = ""
    s = client.chat.completions.create(
        model=model, messages=messages,
        stream=True, max_tokens=4096
    )
    print()
    for chunk in s:
        token = chunk.choices[0].delta.content or ""
        print(token, end="", flush=True)
        full += token
    print()
    return full


def _call_openai(key: str, model: str, prompt: str, stream: bool) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        console.print(
            "  [#ff6b6b]OpenAI package not installed.[/] "
            "Run: [bold]pip install openai[/bold]\n"
        )
        return ""
    client   = OpenAI(api_key=key)
    messages = [{"role": "user", "content": prompt}]
    if stream:
        full = ""
        print()
        s = client.chat.completions.create(
            model=model, messages=messages,
            stream=True, max_tokens=4096
        )
        for chunk in s:
            token = chunk.choices[0].delta.content or ""
            print(token, end="", flush=True)
            full += token
        print()
        return full
    else:
        r = client.chat.completions.create(model=model, messages=messages)
        return r.choices[0].message.content


def _call_anthropic(key: str, model: str, prompt: str, stream: bool) -> str:
    try:
        import anthropic
    except ImportError:
        console.print(
            "  [#ff6b6b]Anthropic package not installed.[/] "
            "Run: [bold]pip install anthropic[/bold]\n"
        )
        return ""
    client = anthropic.Anthropic(api_key=key)
    if stream:
        full = ""
        print()
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        ) as s:
            for text in s.text_stream:
                print(text, end="", flush=True)
                full += text
        print()
        return full
    else:
        r = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text


def _call_gemini(key: str, model: str, prompt: str, stream: bool) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        console.print(
            "  [#ff6b6b]Gemini package not installed.[/] "
            "Run: [bold]pip install google-generativeai[/bold]\n"
        )
        return ""
    genai.configure(api_key=key)
    m = genai.GenerativeModel(model)
    if stream:
        full = ""
        print()
        for chunk in m.generate_content(prompt, stream=True):
            text = chunk.text or ""
            print(text, end="", flush=True)
            full += text
        print()
        return full
    else:
        r = m.generate_content(prompt)
        return r.text
