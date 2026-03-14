"""
verify.py — Vital's Pre-Apply Verification Pipeline

Runs a syntax check on AI-generated code before writing to disk.
Prevents Vital from silently shipping broken files.

Supported: Python (py_compile), JS/TS (basic bracket balance)
"""

import os
import py_compile
import tempfile
from dataclasses import dataclass, field

from rich.console import Console

console = Console()


@dataclass
class VerifyResult:
    passed:   bool
    errors:   list[str] = field(default_factory=list)
    language: str = "unknown"


def verify_code(filepath: str, code: str) -> VerifyResult:
    """
    Verify generated code before applying it to disk.
    Runs the appropriate syntax check for the file's language.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".py":
        return _verify_python(code)

    # JS/TS: basic brace-balance check
    if ext in (".js", ".ts", ".jsx", ".tsx", ".mjs"):
        return _verify_braces(code, ext.lstrip("."))

    # All other types: pass through (no checker available)
    return VerifyResult(passed=True, language=ext.lstrip("."))


def show_verify_error(result: VerifyResult):
    """Print a human-friendly error for a failed verification."""
    console.print(
        "\n  [bold #ff6b6b]✗ Syntax error in generated code —"
        " patch not applied[/]\n"
    )
    for err in result.errors:
        console.print(f"  [#ff6b6b]  {err}[/]")
    console.print()


# ── Checkers ──────────────────────────────────────────────────────────────────

def _verify_python(code: str) -> VerifyResult:
    """Use py_compile to check Python syntax without executing the code."""
    errors: list[str] = []

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp = f.name

    try:
        py_compile.compile(tmp, doraise=True)
    except py_compile.PyCompileError as e:
        msg = str(e).replace(tmp, "<generated>")
        errors.append(msg)
    except Exception as e:
        errors.append(f"Syntax check failed: {e}")
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass

    return VerifyResult(passed=not errors, errors=errors, language="python")


def _verify_braces(code: str, language: str) -> VerifyResult:
    """Basic bracket-balance check for JS/TS."""
    errors: list[str] = []
    pairs  = {"(": ")", "[": "]", "{": "}"}
    closes = set(pairs.values())
    stack: list[str] = []
    in_string: str | None = None

    for i, ch in enumerate(code):
        if in_string:
            if ch == in_string and (i == 0 or code[i - 1] != "\\"):
                in_string = None
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in closes:
            if not stack or stack[-1] != ch:
                errors.append(f"Unmatched '{ch}' near position {i}")
                break
            stack.pop()

    if stack:
        errors.append(f"Unclosed bracket: expected '{stack[-1]}' before end of file")

    return VerifyResult(passed=not errors, errors=errors, language=language)
