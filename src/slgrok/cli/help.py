"""Help content for slgrok CLI."""

OVERVIEW = """
slgrok - ngrok Inspector CLI Tool

Extract and format HTTP request/response data from ngrok's local inspector API.
Provides human-readable and LLM-optimized markdown output.

COMMANDS:
  list    List captured requests (default)
  tail    Watch for new requests in real-time
  get     Get a specific request by ID
  help    Show detailed help and examples

QUICK START:
  # Make sure ngrok is running first
  ngrok http 8080

  # View last 10 requests
  slgrok list -n 10

  # Watch for errors in real-time
  slgrok tail --errors

  # Get details of a specific request
  slgrok get <request-id>

GLOBAL OPTIONS:
  --base-url    ngrok inspector URL (default: http://127.0.0.1:4040)

For more help on a specific command, use: slgrok help <command>
"""

LIST_HELP = """
LIST COMMAND

List captured requests from ngrok inspector.

USAGE:
  slgrok list [OPTIONS]

OPTIONS:
  -n, --limit INT      Number of requests to retrieve (default: 20)
  -s, --status TEXT    Status code filter (e.g., 404, 4xx, 5xx)
  -e, --errors         Show only error responses (status >= 400)
  -p, --path TEXT      Filter by path pattern (glob or regex)
  -d, --domain TEXT    Filter by domain name
  -t, --tunnel TEXT    Filter by tunnel name
  --since TEXT         Time window (e.g., 5s, 2m, 1h)
  --pretty             Pretty-print JSON bodies
  --truncate INT       Truncate bodies to N characters

EXAMPLES:
  # Last 10 requests
  slgrok list -n 10

  # Only errors from the last 5 minutes
  slgrok list --errors --since 5m

  # 4xx errors on /api paths
  slgrok list --status 4xx --path "/api/*"

  # Pretty-printed output, truncated for LLM
  slgrok list --pretty --truncate 2000

  # From specific tunnel
  slgrok list --tunnel my-api

FILTER COMBINATIONS:
  Multiple filters can be combined (AND logic):
  slgrok list --errors --path "/api/*" --since 10m
"""

TAIL_HELP = """
TAIL COMMAND

Watch for new requests in real-time.

USAGE:
  slgrok tail [OPTIONS]

OPTIONS:
  -s, --status TEXT    Status code filter (e.g., 404, 4xx, 5xx)
  -e, --errors         Show only error responses (status >= 400)
  -p, --path TEXT      Filter by path pattern (glob or regex)
  -d, --domain TEXT    Filter by domain name
  -t, --tunnel TEXT    Filter by tunnel name
  --pretty             Pretty-print JSON bodies
  --truncate INT       Truncate bodies to N characters

EXAMPLES:
  # Watch all requests
  slgrok tail

  # Watch only errors
  slgrok tail --errors

  # Watch specific path
  slgrok tail --path "/webhook/*"

  # Watch 5xx errors with pretty output
  slgrok tail --status 5xx --pretty

Press Ctrl+C to stop watching.
"""

GET_HELP = """
GET COMMAND

Get details of a specific request by ID.

USAGE:
  slgrok get <request-id> [OPTIONS]

ARGUMENTS:
  request-id    The ID of the request to retrieve

OPTIONS:
  --pretty        Pretty-print JSON bodies
  --truncate INT  Truncate bodies to N characters

EXAMPLES:
  # Get a specific request
  slgrok get 548fb5c700000002

  # Get with pretty-printed JSON
  slgrok get 548fb5c700000002 --pretty

FINDING REQUEST IDS:
  Request IDs are shown in the output of 'slgrok list'.
  You can also find them in the ngrok inspector web UI.
"""

COMMAND_HELP = {
    "list": LIST_HELP,
    "tail": TAIL_HELP,
    "get": GET_HELP,
}


def get_help(command: str | None = None) -> str:
    """Get help text for a command or overview.

    Args:
        command: Optional command name

    Returns:
        Help text string
    """
    if command is None:
        return OVERVIEW.strip()

    help_text = COMMAND_HELP.get(command.lower())
    if help_text is None:
        return f"Unknown command: {command}\n\nAvailable commands: list, tail, get"

    return help_text.strip()
