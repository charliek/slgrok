"""Main Typer application."""

import typer

from slgrok.cli.commands import get_request, list_requests, show_help, tail_requests

app = typer.Typer(
    name="slgrok",
    help="CLI tool for extracting HTTP request/response data from ngrok's inspector API.",
    no_args_is_help=True,
)

# Register commands
app.command("list", help="List captured requests from ngrok inspector")(list_requests)
app.command("tail", help="Watch for new requests in real-time")(tail_requests)
app.command("get", help="Get details of a specific request by ID")(get_request)
app.command("help", help="Show detailed help and examples")(show_help)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """slgrok - ngrok Inspector CLI Tool."""
    # If no command is provided and no args, show help
    if ctx.invoked_subcommand is None:
        # Default to list command behavior would go here if desired
        pass


if __name__ == "__main__":
    app()
