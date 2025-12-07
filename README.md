# slgrok

CLI tool for extracting and formatting HTTP request/response data from ngrok's inspector API.

## Installation

```bash
# Run without installing
uvx slgrok

# Or install as a tool
uv tool install slgrok
```

## Usage

```bash
# List recent requests
slgrok list

# List with filters
slgrok list -n 10 --errors --path "/api/*"

# Watch for new requests in real-time
slgrok tail

# Get a specific request by ID
slgrok get <request-id>

# Show help
slgrok help
```

## Development

### Setup

```bash
uv sync --extra dev
```

### Running Tests

```bash
uv run pytest
```

### Linting & Type Checking

```bash
./scripts/lint.sh
```

Or run individually:

```bash
uv run ruff check .        # Lint
uv run ruff format --check # Format check
uv run pyrefly check       # Type check
```

### Auto-format

```bash
uv run ruff format .
uv run ruff check --fix .
```

### Pre-commit Hooks

Install the pre-commit hooks to run linting and type checking on every commit:

```bash
uv run pre-commit install
```

Run manually on all files:

```bash
uv run pre-commit run --all-files
```
