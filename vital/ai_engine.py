"""
ai_engine.py — Vital's AI Engine
Now powered by providers.py — supports Groq, OpenAI, Claude, Gemini
"""

from rich.console import Console
from vital import providers

console = Console()


def ask(prompt: str, system: str = None, stream: bool = True) -> str:
    """
    Send a prompt using the default or best available provider.
    Automatically uses council routing if council mode is on.
    """
    config = providers.load_config()

    # Build full prompt with system message if provided
    full_prompt = prompt
    if system:
        full_prompt = f"{system}\n\n{prompt}"

    # Use council mode if enabled and multiple providers available
    if config.get("council_mode") and len(config.get("providers", {})) > 1:
        task_type = _detect_task_type(prompt)
        return providers.council_ask(full_prompt, task_type=task_type)
    else:
        return providers.ask(full_prompt, stream=stream)


def ask_with_context(prompt: str, context: str, system: str = None) -> str:
    """Send prompt with project context attached."""
    full_prompt = f"""Project Context:
{context}

---

{prompt}
"""
    return ask(full_prompt, system=system)


def _detect_task_type(prompt: str) -> str:
    """
    Detect what kind of task this is so council
    can route to the best provider.
    """
    lower = prompt.lower()

    if any(w in lower for w in ["review", "check", "security", "vulnerability", "audit"]):
        return "review"

    if any(w in lower for w in ["architect", "design", "structure", "plan", "best way"]):
        return "architecture"

    if any(w in lower for w in ["explain", "what is", "how does", "document", "describe"]):
        return "explain"

    if any(w in lower for w in ["quick", "fast", "simple", "short"]):
        return "fast"

    if any(w in lower for w in ["code", "write", "create", "build", "generate", "function", "class"]):
        return "code"

    return "general"
