"""Reusable CLI option definitions."""

from typing import Annotated

import typer

# Global options
BaseUrlOption = Annotated[
    str | None,
    typer.Option(
        "--base-url",
        help="ngrok inspector base URL",
        envvar="SLGROK_BASE_URL",
    ),
]

# List command options
LimitOption = Annotated[
    int,
    typer.Option(
        "--limit",
        "-n",
        help="Number of requests to retrieve",
    ),
]

# Filter options
StatusOption = Annotated[
    str | None,
    typer.Option(
        "--status",
        "-s",
        help="Status code filter (e.g., 404, 4xx, 5xx)",
    ),
]

ErrorsOption = Annotated[
    bool,
    typer.Option(
        "--errors",
        "-e",
        help="Show only error responses (status >= 400)",
    ),
]

PathOption = Annotated[
    str | None,
    typer.Option(
        "--path",
        "-p",
        help="Filter by path pattern (glob or regex)",
    ),
]

DomainOption = Annotated[
    str | None,
    typer.Option(
        "--domain",
        "-d",
        help="Filter by domain name",
    ),
]

TunnelOption = Annotated[
    str | None,
    typer.Option(
        "--tunnel",
        "-t",
        help="Filter by tunnel name",
    ),
]

SinceOption = Annotated[
    str | None,
    typer.Option(
        "--since",
        help="Time window (e.g., 5s, 2m, 1h)",
    ),
]

# Output options
PrettyOption = Annotated[
    bool,
    typer.Option(
        "--pretty",
        help="Pretty-print JSON bodies",
    ),
]

TruncateOption = Annotated[
    int | None,
    typer.Option(
        "--truncate",
        help="Truncate bodies to N characters",
    ),
]

DebugOption = Annotated[
    bool,
    typer.Option(
        "--debug",
        help="Enable debug logging to stderr",
    ),
]
