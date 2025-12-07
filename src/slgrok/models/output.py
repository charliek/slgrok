"""Output formatting models."""

from pydantic import BaseModel


class FormatOptions(BaseModel):
    """Options controlling output formatting."""

    pretty_print: bool = False
    truncate: int | None = None  # Max chars for bodies, None = no truncation
    show_headers: bool = True
    headers_filter: list[str] | None = None  # If set, only show these headers
