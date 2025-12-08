"""Output formatting models."""

import sys

from pydantic import BaseModel


class FormatOptions(BaseModel):
    """Options controlling output formatting."""

    pretty_print: bool = False
    truncate: int | None = None  # Max chars for bodies, None = no truncation
    show_headers: bool = True
    headers_filter: list[str] | None = None  # If set, only show these headers
    debug: bool = False  # Enable debug logging


def debug_log(message: str, enabled: bool = True) -> None:
    """Print a debug message to stderr if enabled."""
    if enabled:
        print(f"[DEBUG] {message}", file=sys.stderr)
