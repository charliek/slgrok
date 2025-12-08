"""CLI command definitions."""

from typing import Annotated

import typer
from rich.console import Console

from slgrok.cli.help import get_help
from slgrok.cli.options import (
    BaseUrlOption,
    DebugOption,
    DomainOption,
    ErrorsOption,
    LimitOption,
    PathOption,
    PrettyOption,
    SinceOption,
    StatusOption,
    TruncateOption,
    TunnelOption,
)
from slgrok.models.filters import RequestFilters, StatusCodeFilter, TimeWindow
from slgrok.models.output import FormatOptions
from slgrok.models.requests import CapturedRequest
from slgrok.repositories.ngrok import NgrokConnectionError, NgrokRepository
from slgrok.services.formatter import FormatterService
from slgrok.services.inspector import InspectorService
from slgrok.settings import settings

console = Console()
err_console = Console(stderr=True)


def _get_base_url(base_url: str | None) -> str:
    """Get the base URL, preferring CLI option over settings."""
    if base_url is not None:
        return base_url.rstrip("/")
    return str(settings.base_url).rstrip("/")


def _build_filters(
    limit: int | None = None,
    status: str | None = None,
    errors: bool = False,
    path: str | None = None,
    domain: str | None = None,
    tunnel: str | None = None,
    since: str | None = None,
) -> RequestFilters:
    """Build RequestFilters from CLI options."""
    status_filter = None
    if status is not None or errors:
        if status is not None:
            status_filter = StatusCodeFilter.from_string(status, errors_only=errors)
        else:
            status_filter = StatusCodeFilter(errors_only=errors)

    time_window = None
    if since is not None:
        time_window = TimeWindow.parse(since)

    return RequestFilters(
        limit=limit,
        status=status_filter,
        path_pattern=path,
        domain=domain,
        tunnel_name=tunnel,
        time_window=time_window,
    )


def _build_format_options(
    pretty: bool = False,
    truncate: int | None = None,
    debug: bool = False,
) -> FormatOptions:
    """Build FormatOptions from CLI options."""
    return FormatOptions(
        pretty_print=pretty,
        truncate=truncate,
        debug=debug,
    )


def _build_filters_summary(filters: RequestFilters) -> str | None:
    """Build a human-readable summary of applied filters."""
    parts: list[str] = []

    if filters.status is not None:
        if filters.status.errors_only:
            parts.append("errors only")
        if filters.status.exact:
            parts.append(f"status={','.join(str(c) for c in filters.status.exact)}")
        if filters.status.ranges:
            parts.append(f"status={','.join(filters.status.ranges)}")

    if filters.path_pattern is not None:
        parts.append(f"path={filters.path_pattern}")

    if filters.domain is not None:
        parts.append(f"domain={filters.domain}")

    if filters.tunnel_name is not None:
        parts.append(f"tunnel={filters.tunnel_name}")

    if filters.time_window is not None:
        parts.append(f"since={filters.time_window.value}{filters.time_window.unit}")

    return ", ".join(parts) if parts else None


def list_requests(
    base_url: BaseUrlOption = None,
    limit: LimitOption = 20,
    status: StatusOption = None,
    errors: ErrorsOption = False,
    path: PathOption = None,
    domain: DomainOption = None,
    tunnel: TunnelOption = None,
    since: SinceOption = None,
    pretty: PrettyOption = False,
    truncate: TruncateOption = None,
    debug: DebugOption = False,
) -> None:
    """List captured requests from ngrok inspector."""
    try:
        url = _get_base_url(base_url)
        filters = _build_filters(limit, status, errors, path, domain, tunnel, since)
        format_options = _build_format_options(pretty, truncate, debug)

        if debug:
            err_console.print("[dim][DEBUG] Debug mode enabled[/dim]")
            err_console.print(f"[dim][DEBUG] Fetching from {url}[/dim]")

        with NgrokRepository(url) as repo:
            service = InspectorService(repo)
            requests = service.get_requests(filters)

            if debug:
                err_console.print(f"[dim][DEBUG] Retrieved {len(requests)} requests[/dim]")

            if not requests:
                filters_summary = _build_filters_summary(filters)
                err_console.print("No requests found matching filters:")
                if filters_summary:
                    for part in filters_summary.split(", "):
                        err_console.print(f"  • {part}")
                err_console.print("\nTry broadening your filters or check ngrok at:")
                err_console.print(f"{url}/inspect/http")
                raise typer.Exit(1)

            formatter = FormatterService()
            output = formatter.format_requests(
                requests,
                format_options,
                _build_filters_summary(filters),
            )
            console.print(output)

    except NgrokConnectionError as e:
        err_console.print(str(e))
        raise typer.Exit(1) from None
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None


def _log_request_debug(request: CapturedRequest) -> None:
    """Log debug information about a captured request."""
    req_id = request.id
    method = request.request.method
    uri = request.request.uri

    # Check response state
    if request.response is None:
        err_console.print(f"[dim][DEBUG][/dim] {req_id} {method} {uri}: response is None")
        return

    # Check response.raw state
    if request.response.raw is None:
        err_console.print(f"[dim][DEBUG][/dim] {req_id} {method} {uri}: response.raw is None")
    elif len(request.response.raw) == 0:
        err_console.print(f"[dim][DEBUG][/dim] {req_id} {method} {uri}: response.raw is empty")
    else:
        # Log raw length and content-length header for comparison
        raw_len = len(request.response.raw)
        content_length = request.response.headers.root.get("Content-Length", [None])[0]
        status = request.response.status_code
        err_console.print(
            f"[dim][DEBUG][/dim] {req_id} {method} {uri}: "
            f"status={status}, raw_b64_len={raw_len}, content-length={content_length}"
        )


def tail_requests(
    base_url: BaseUrlOption = None,
    status: StatusOption = None,
    errors: ErrorsOption = False,
    path: PathOption = None,
    domain: DomainOption = None,
    tunnel: TunnelOption = None,
    pretty: PrettyOption = False,
    truncate: TruncateOption = None,
    debug: DebugOption = False,
) -> None:
    """Watch for new requests in real-time."""
    try:
        url = _get_base_url(base_url)
        filters = _build_filters(None, status, errors, path, domain, tunnel, None)
        format_options = _build_format_options(pretty, truncate, debug)

        console.print("Watching for requests... (Ctrl+C to stop)\n")
        if debug:
            err_console.print("[dim][DEBUG] Debug mode enabled[/dim]")
            err_console.print(f"[dim][DEBUG] Connecting to {url}[/dim]")

        with NgrokRepository(url) as repo:
            service = InspectorService(repo)
            formatter = FormatterService()

            for request in service.tail_requests(filters, debug=debug):
                if debug:
                    _log_request_debug(request)

                label = f"{request.request.method} {request.request.uri}"
                separator = formatter._build_separator(label)
                output = formatter.format_request(request, format_options)
                console.print(separator)
                console.print("")
                console.print(output)

    except NgrokConnectionError as e:
        err_console.print(str(e))
        raise typer.Exit(1) from None
    except KeyboardInterrupt:
        console.print("\nStopped watching.")
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None


def get_request(
    request_id: Annotated[str, typer.Argument(help="The request ID to retrieve")],
    base_url: BaseUrlOption = None,
    pretty: PrettyOption = False,
    truncate: TruncateOption = None,
    debug: DebugOption = False,
) -> None:
    """Get details of a specific request by ID."""
    try:
        url = _get_base_url(base_url)
        format_options = _build_format_options(pretty, truncate, debug)

        if debug:
            err_console.print("[dim][DEBUG] Debug mode enabled[/dim]")
            err_console.print(f"[dim][DEBUG] Fetching {request_id} from {url}[/dim]")

        with NgrokRepository(url) as repo:
            request = repo.get_request(request_id)

            if debug:
                _log_request_debug(request)

            formatter = FormatterService()
            output = formatter.format_request(request, format_options)
            console.print(output)

    except NgrokConnectionError as e:
        err_console.print(str(e))
        raise typer.Exit(1) from None
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None


def show_help(
    command: Annotated[
        str | None,
        typer.Argument(help="Command to get help for"),
    ] = None,
) -> None:
    """Show detailed help and examples."""
    help_text = get_help(command)
    console.print(help_text)
