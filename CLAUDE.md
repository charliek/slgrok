# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Setup development environment
uv sync --extra dev

# Run tests
uv run pytest                    # Run all tests
uv run pytest tests/test_services/test_inspector.py  # Run single test file
uv run pytest -k "test_matches_path"  # Run tests matching pattern

# Linting & type checking
./scripts/lint.sh                # Run all checks
uv run ruff check .              # Lint only
uv run ruff format --check .     # Format check only
uv run pyrefly check             # Type check only

# Auto-fix formatting
uv run ruff format .
uv run ruff check --fix .

# Pre-commit hooks
uv run pre-commit install        # Install hooks
uv run pre-commit run --all-files  # Run manually
```

## Project Architecture

slgrok is a CLI tool for extracting HTTP request/response data from ngrok's local inspector API (http://127.0.0.1:4040).

### Layered Architecture

```
src/slgrok/
├── main.py              # Typer app entry point, registers commands
├── settings.py          # pydantic-settings config (env: SLGROK_BASE_URL)
├── cli/
│   ├── commands.py      # Command implementations (list, tail, get, help)
│   └── options.py       # Typer option type aliases
├── services/
│   ├── inspector.py     # InspectorService: fetching + filtering logic
│   └── formatter.py     # FormatterService: Rich markdown output
├── repositories/
│   └── ngrok.py         # NgrokRepository: httpx client for ngrok API
└── models/
    ├── requests.py      # Pydantic models for ngrok API responses
    ├── filters.py       # RequestFilters, StatusCodeFilter, TimeWindow
    └── output.py        # FormatOptions
```

### Key Patterns

- **Repository pattern**: `NgrokRepository` wraps httpx calls to ngrok's `/api/requests/http` endpoint
- **Service layer**: `InspectorService` handles filtering logic (status codes, path patterns, domains, time windows); `FormatterService` produces Rich-formatted output
- **Commands compose services**: Commands in `cli/commands.py` instantiate repository and services, apply filters, format output
- **Context managers**: `NgrokRepository` supports `with` statement for proper HTTP client cleanup

### Data Flow

1. CLI command parses options → builds `RequestFilters` and `FormatOptions`
2. `NgrokRepository.get_requests()` fetches from ngrok API → returns `list[CapturedRequest]`
3. `InspectorService._apply_filters()` filters locally (status, path glob/regex, domain, time window)
4. `FormatterService.format_requests()` renders Rich markdown with syntax-highlighted bodies

### Configuration

Settings load from environment with `SLGROK_` prefix or `.env` file:
- `SLGROK_BASE_URL`: ngrok inspector URL (default: `http://127.0.0.1:4040`)

## Code Style

- Python 3.13+, uses modern syntax (match statements, type hints)
- Ruff for linting/formatting (100 char line length)
- Pyrefly for type checking
- Pydantic v2 for all data models
