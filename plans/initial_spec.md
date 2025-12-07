# slgrok - ngrok Inspector CLI Tool

## Overview

`slgrok` is a command-line utility that extracts and formats HTTP request/response data from ngrok's local inspector API. It provides human-readable and LLM-optimized markdown output, making it easy to share request logs for debugging, documentation, or AI-assisted troubleshooting.

---

## Requirements

### Functional Requirements

#### FR-1: Request Retrieval

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Retrieve the last N captured requests from ngrok inspector | Must |
| FR-1.2 | Support configurable ngrok inspector base URL (default: `http://127.0.0.1:4040`) | Must |
| FR-1.3 | Retrieve a single request by ID | Should |
| FR-1.4 | Tail/watch mode to stream new requests as they arrive | Must |

#### FR-2: Filtering

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Filter by HTTP status code (exact match, e.g., `404`) | Must |
| FR-2.2 | Filter by status code range (e.g., `4xx`, `5xx`) | Must |
| FR-2.3 | Filter by error responses only (status >= 400) | Must |
| FR-2.4 | Filter by URL path pattern (glob or regex) | Must |
| FR-2.5 | Filter by domain name | Must |
| FR-2.6 | Filter by tunnel name | Must |
| FR-2.7 | Filter by time window using shorthand notation (e.g., `5s`, `2m`, `1h`) | Must |

#### FR-3: Output Formatting

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Output in markdown format with proper code blocks for bodies | Must |
| FR-3.2 | Show full request/response bodies by default | Must |
| FR-3.3 | Optional truncation of bodies with configurable limit | Must |
| FR-3.4 | Optional pretty-print flag for JSON bodies (off by default) | Must |
| FR-3.5 | Include request metadata: method, path, status, duration, timestamp | Must |
| FR-3.6 | Include relevant headers (with option to show all or filter) | Must |
| FR-3.7 | Base64 decode raw request/response bodies from ngrok API | Must |

#### FR-4: User Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Fail fast with clear error message when ngrok is not running | Must |
| FR-4.2 | Provide helpful `--help` documentation for all commands and options | Must |
| FR-4.3 | Support combining multiple filters (AND logic) | Must |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Python 3.13 compatibility |
| NFR-2 | Synchronous execution model |
| NFR-3 | Response time < 500ms for typical queries (excluding network latency) |
| NFR-4 | Comprehensive test coverage with mocked ngrok API responses |

---

## Technical Design

### Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| Package Manager | uv |
| CLI Framework | Typer |
| Data Validation | Pydantic v2 |
| Configuration | Pydantic Settings |
| HTTP Client | httpx |
| Testing | pytest, pytest-mock |

### Project Structure

```
slgrok/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── slgrok/
│       ├── __init__.py
│       ├── __main__.py          # Entry point for `python -m slgrok`
│       ├── main.py              # Typer app initialization
│       ├── settings.py          # Pydantic Settings configuration
│       ├── models/
│       │   ├── __init__.py
│       │   ├── requests.py      # Pydantic models for ngrok request data
│       │   ├── filters.py       # Filter configuration models
│       │   └── output.py        # Output formatting models
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── ngrok.py         # ngrok API client
│       ├── services/
│       │   ├── __init__.py
│       │   ├── inspector.py     # Business logic for fetching/filtering
│       │   └── formatter.py     # Markdown output formatting
│       └── cli/
│           ├── __init__.py
│           ├── commands.py      # Typer command definitions
│           └── options.py       # Reusable CLI option definitions
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures, mock data
│   ├── fixtures/                # Sample ngrok API responses
│   │   └── requests.json
│   ├── test_repositories/
│   │   └── test_ngrok.py
│   ├── test_services/
│   │   ├── test_inspector.py
│   │   └── test_formatter.py
│   └── test_cli/
│       └── test_commands.py
```

### Layer Responsibilities

#### Repository Layer (`repositories/`)

Responsible for all communication with external systems (ngrok API).

**`NgrokRepository`**
- Handles HTTP communication with ngrok inspector API
- Returns raw Pydantic models parsed from API responses
- No business logic or filtering
- Raises typed exceptions for connection errors

```python
class NgrokRepository:
    def __init__(self, base_url: str): ...
    def get_requests(self, limit: int | None = None, tunnel_name: str | None = None) -> list[CapturedRequest]: ...
    def get_request(self, request_id: str) -> CapturedRequest: ...
    def get_status(self) -> AgentStatus: ...
    def health_check(self) -> bool: ...
```

#### Service Layer (`services/`)

Contains business logic, filtering, and formatting.

**`InspectorService`**
- Applies filters to captured requests
- Handles time window calculations
- Manages tail/watch mode logic

```python
class InspectorService:
    def __init__(self, repository: NgrokRepository): ...
    def get_requests(self, filters: RequestFilters) -> list[CapturedRequest]: ...
    def tail_requests(self, filters: RequestFilters) -> Iterator[CapturedRequest]: ...
```

**`FormatterService`**
- Converts captured requests to markdown output
- Handles body truncation
- Handles JSON pretty-printing when enabled
- Decodes base64 bodies

```python
class FormatterService:
    def format_request(self, request: CapturedRequest, options: FormatOptions) -> str: ...
    def format_requests(self, requests: list[CapturedRequest], options: FormatOptions) -> str: ...
```

#### CLI Layer (`cli/`)

Handles user interaction and argument parsing.

**Commands**
- `slgrok list` - List captured requests (default command)
- `slgrok tail` - Watch for new requests in real-time
- `slgrok get <id>` - Get a specific request by ID

### Pydantic Models

#### Configuration (`settings.py`)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SLGROK_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    base_url: HttpUrl = "http://127.0.0.1:4040"
```

#### Request Models (`models/requests.py`)

```python
class HttpHeaders(RootModel[dict[str, list[str]]]):
    """HTTP headers as returned by ngrok API."""
    pass

class RequestData(BaseModel):
    """Incoming HTTP request data."""
    method: str
    proto: str
    headers: HttpHeaders
    uri: str
    raw: str  # Base64 encoded

class ResponseData(BaseModel):
    """HTTP response data."""
    status: str
    status_code: int
    proto: str
    headers: HttpHeaders
    raw: str  # Base64 encoded

class CapturedRequest(BaseModel):
    """A captured request/response pair from ngrok inspector."""
    uri: str
    id: str
    tunnel_name: str
    remote_addr: str
    start: datetime
    duration: int  # nanoseconds
    request: RequestData
    response: ResponseData | None = None

class CapturedRequestList(BaseModel):
    """Response from GET /api/requests/http."""
    uri: str
    requests: list[CapturedRequest]
```

#### Filter Models (`models/filters.py`)

```python
class TimeWindow(BaseModel):
    """Time window for filtering requests."""
    value: int
    unit: Literal["s", "m", "h"]
    
    @classmethod
    def parse(cls, value: str) -> "TimeWindow":
        """Parse shorthand like '5s', '2m', '1h'."""
        ...
    
    def to_timedelta(self) -> timedelta:
        ...

class StatusCodeFilter(BaseModel):
    """Filter for HTTP status codes."""
    exact: list[int] = []
    ranges: list[str] = []  # e.g., "4xx", "5xx"
    errors_only: bool = False
    
    def matches(self, status_code: int) -> bool:
        ...

class RequestFilters(BaseModel):
    """Combined filters for request queries."""
    limit: int | None = None
    status: StatusCodeFilter | None = None
    path_pattern: str | None = None
    domain: str | None = None
    tunnel_name: str | None = None
    time_window: TimeWindow | None = None
```

#### Output Models (`models/output.py`)

```python
class FormatOptions(BaseModel):
    """Options controlling output formatting."""
    pretty_print: bool = False
    truncate: int | None = None  # Max chars for bodies, None = no truncation
    show_headers: bool = True
    headers_filter: list[str] | None = None  # If set, only show these headers
```

### CLI Interface

#### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--base-url` | URL | `http://127.0.0.1:4040` | ngrok inspector base URL |

#### `slgrok list` (default command)

List captured requests from ngrok inspector.

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | int | 20 | Number of requests to retrieve |
| `--status` | `-s` | str | None | Status code filter (e.g., `404`, `4xx`, `5xx`) |
| `--errors` | `-e` | flag | False | Show only error responses (status >= 400) |
| `--path` | `-p` | str | None | Filter by path pattern |
| `--domain` | `-d` | str | None | Filter by domain name |
| `--tunnel` | `-t` | str | None | Filter by tunnel name |
| `--since` | | str | None | Time window (e.g., `5s`, `2m`, `1h`) |
| `--pretty` | | flag | False | Pretty-print JSON bodies |
| `--truncate` | | int | None | Truncate bodies to N characters |

**Examples:**
```bash
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
```

#### `slgrok tail`

Watch for new requests in real-time.

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--status` | `-s` | str | None | Status code filter |
| `--errors` | `-e` | flag | False | Show only errors |
| `--path` | `-p` | str | None | Filter by path pattern |
| `--domain` | `-d` | str | None | Filter by domain name |
| `--tunnel` | `-t` | str | None | Filter by tunnel name |
| `--pretty` | | flag | False | Pretty-print JSON bodies |
| `--truncate` | | int | None | Truncate bodies to N characters |

**Examples:**
```bash
# Watch all requests
slgrok tail

# Watch only errors
slgrok tail --errors

# Watch specific path
slgrok tail --path "/webhook/*"
```

#### `slgrok get <request_id>`

Get details of a specific request by ID.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--pretty` | flag | False | Pretty-print JSON bodies |
| `--truncate` | int | None | Truncate bodies to N characters |

**Examples:**
```bash
slgrok get 548fb5c700000002
slgrok get 548fb5c700000002 --pretty
```

### Output Format

Markdown formatted output for easy reading and LLM consumption.

#### Single Request Output

```markdown
## POST /api/v1/devices/commands
**Status:** 500 Internal Server Error
**Duration:** 234ms
**Timestamp:** 2024-01-15T10:32:07-08:00
**Tunnel:** smartthings-mcp
**Remote:** 192.168.1.100

### Request Headers
```
Content-Type: application/json
Authorization: Bearer ***
X-Request-ID: abc123
```

### Request Body
```json
{
  "deviceId": "device-123",
  "command": "switch:off"
}
```

### Response Headers
```
Content-Type: application/json
X-Error-Code: DEVICE_OFFLINE
```

### Response Body
```json
{
  "error": "Device not responding",
  "code": "DEVICE_OFFLINE"
}
```

---
```

#### Multiple Requests Output

When listing multiple requests, each request is formatted as above, separated by horizontal rules (`---`).

A summary header is included:

```markdown
# ngrok Inspector - 5 requests

**Filters:** errors only, path=/api/*, since=5m
**Retrieved:** 2024-01-15T10:35:00-08:00

---

## POST /api/v1/devices/commands
...
```

### Error Handling

#### Connection Errors

When ngrok is not running or unreachable:

```
Error: Cannot connect to ngrok inspector at http://127.0.0.1:4040

Possible causes:
  • ngrok is not running
  • ngrok is running on a different port (use --base-url)
  • The inspector interface is disabled

Start ngrok with: ngrok http <port>
```

#### No Results

When filters return no results:

```
No requests found matching filters:
  • Status: 5xx
  • Path: /api/*
  • Since: 5m

Try broadening your filters or check if ngrok has captured requests at:
http://127.0.0.1:4040/inspect/http
```

### Testing Strategy

#### Unit Tests

- **Repository tests**: Mock httpx responses, verify correct API calls
- **Service tests**: Test filtering logic with fixture data
- **Formatter tests**: Verify markdown output format

#### Integration Tests

- Test CLI commands with mocked repository
- Verify correct option parsing
- Test error message formatting

#### Test Fixtures

Store sample ngrok API responses in `tests/fixtures/`:

```json
// tests/fixtures/requests.json
{
  "uri": "/api/requests/http",
  "requests": [
    {
      "uri": "/api/requests/http/548fb5c700000002",
      "id": "548fb5c700000002",
      "tunnel_name": "command_line",
      "remote_addr": "192.168.100.25",
      "start": "2024-01-15T10:32:07-08:00",
      "duration": 234000000,
      "request": {
        "method": "POST",
        "proto": "HTTP/1.1",
        "headers": {
          "Content-Type": ["application/json"]
        },
        "uri": "/api/v1/devices",
        "raw": "eyJkZXZpY2VJZCI6ICIxMjMifQ=="
      },
      "response": {
        "status": "200 OK",
        "status_code": 200,
        "proto": "HTTP/1.1",
        "headers": {
          "Content-Type": ["application/json"]
        },
        "raw": "eyJzdWNjZXNzIjogdHJ1ZX0="
      }
    }
  ]
}
```

### Dependencies

```toml
[project]
name = "slgrok"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "typer>=0.15.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.28.0",
    "rich>=13.9.0",  # For terminal output formatting
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.8.0",
    "mypy>=1.14.0",
]

[project.scripts]
slgrok = "slgrok.main:app"
```

### Future Considerations (Out of Scope for v1)

- Request replay from CLI
- Export to file
- Configuration profiles
- Request diffing
- Integration as MCP tool
- Clipboard copy support
- Custom output templates

---

## Appendix

### ngrok Inspector API Reference

Base URL: `http://127.0.0.1:4040/api`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/requests/http` | GET | List captured requests |
| `/api/requests/http/:id` | GET | Get specific request |
| `/api/requests/http` | DELETE | Clear all requests |
| `/api/status` | GET | Agent status |
| `/api/tunnels` | GET | List tunnels |

Query parameters for `GET /api/requests/http`:
- `limit`: Maximum number of requests to return
- `tunnel_name`: Filter by tunnel name
