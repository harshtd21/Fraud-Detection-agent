"""
=====================================================================
 COLORS — makes the agent's output easy to scan at a glance
=====================================================================
WHAT THIS FILE IS:
Plain ANSI escape codes (a standard supported by virtually every
modern terminal — macOS Terminal, Linux terminals, Windows Terminal,
PowerShell, and VS Code's built-in terminal) used to color-code the
three kinds of lines the agent prints:

  [agent]        -> Claude's reasoning, in CYAN
  [tool call]     -> which function is being called, in YELLOW
  [tool result]   -> what that function returned, in GREEN
  section headers -> in BOLD MAGENTA

No extra pip install needed — this uses only Python's built-in string
formatting. If your terminal doesn't support color (some older Windows
setups), pass --no-color when running agent.py and it'll fall back to
plain text automatically.
=====================================================================
"""

import os
import sys

# Respect the NO_COLOR convention (https://no-color.org) and also let
# agent.py force it off via --no-color. Also auto-disable if output
# is being piped/redirected to a file rather than a live terminal,
# since raw escape codes would just show up as garbled text there.
_FORCE_DISABLE = False


def disable_color() -> None:
    """Call this once (e.g. from --no-color) to turn all colors off."""
    global _FORCE_DISABLE
    _FORCE_DISABLE = True


def _color_enabled() -> bool:
    if _FORCE_DISABLE:
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


_RESET = "\033[0m"
_BOLD = "\033[1m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_MAGENTA = "\033[35m"
_DIM = "\033[2m"


def _wrap(text: str, code: str) -> str:
    if not _color_enabled():
        return text
    return f"{code}{text}{_RESET}"


def agent_line(text: str) -> str:
    """Claude's reasoning/text output — cyan."""
    return _wrap(f"[agent]: {text}", _CYAN)


def tool_call_line(text: str) -> str:
    """A tool being invoked — yellow."""
    return _wrap(f"[tool call]: {text}", _YELLOW)


def tool_result_line(text: str) -> str:
    """What a tool returned — green, dimmed slightly since it's raw data."""
    return _wrap(f"[tool result]: {text}", _GREEN + _DIM)


def header(text: str) -> str:
    """Section headers / scenario banners — bold magenta."""
    return _wrap(text, _BOLD + _MAGENTA)


def footer_note(text: str) -> str:
    """Dim informational notes at the end of a run."""
    return _wrap(text, _DIM)
