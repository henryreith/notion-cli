"""Operating mode detection and confirmation helpers."""
import os
import sys

import click


def get_mode(explicit: str | None = None) -> str:
    """Determine operating mode.

    Priority: explicit flag → NOTION_MODE env → TTY detection
    Returns: 'interactive', 'auto', or 'ci'
    """
    if explicit:
        return explicit
    env = os.environ.get("NOTION_MODE")
    if env in ("interactive", "auto", "ci"):
        return env
    # TTY detection
    if sys.stdout.isatty():
        return "interactive"
    return "auto"


def confirm(prompt: str, mode: str | None = None) -> bool:
    """Prompt for confirmation based on mode.

    Returns True if action should proceed:
    - auto/ci mode: always True (no prompt)
    - interactive mode: asks user
    """
    if mode is None:
        mode = get_mode()
    if mode in ("auto", "ci"):
        return True
    return click.confirm(prompt)
