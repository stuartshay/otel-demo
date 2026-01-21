# Makefile Usage Guide

The otel-demo Makefile provides convenient commands for development workflow automation.

## Quick Start

```bash
# View all available commands
make help

# Set up project (create venv, install dependencies)
make setup

# Start development server
make start

# View logs
make logs

# Stop server
make stop
```

## Common Commands

### Development Server

| Command | Description | Usage |
|---------|-------------|-------|
| `make start` | Start server in background (port 8080) | Development use |
| `make start-fg` | Start server in foreground | Debugging |
| `make stop` | Stop running server | Cleanup |
| `make restart` | Stop and start server | After config changes |
| `make reload` | Graceful reload (HUP signal) | Code changes |
| `make status` | Check if server is running | Health check |
| `make dev` | Alias for `make start` | Quick start |

### Logs

```bash
# Tail logs in real-time (Ctrl+C to stop)
make logs

# View all logs with pager
make logs-view
```

### API Testing

```bash
# Check health endpoint
make health
# Output: {"status": "healthy"}

# Check database endpoint
make db-status
# Output: {"status": "connected", "database": "opendata", ...}

# List all API endpoints
make endpoints
# Output: /health, /db/status, /db/locations, ...
```

### Code Quality

```bash
# Run linter
make lint

# Fix linting issues automatically
make lint-fix

# Format code with ruff
make format

# Check formatting without changes
make format-check

# Run type checking with mypy
make type-check

# Check shell scripts
make shellcheck

# Run all checks
make check
```

### Testing

```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov

# Run tests in verbose mode
make test-verbose

# Run tests in watch mode
make test-watch
```

### Database

```bash
# Test database connection
make db-test

# Query location count
make db-locations

# Check database status endpoint
make db-status
```

### Installation

```bash
# Initial setup (recommended)
make setup

# Install dependencies only
make install

# Install with dev dependencies (pytest, ruff, mypy)
make install-dev

# Clean cache and artifacts
make clean

# Clean everything including venv
make clean-all

# Full reset (clean + setup)
make reset
```

### Docker

```bash
# Build Docker image
make docker-build

# Run container (foreground)
make docker-run

# Run container in background
make docker-run-bg

# Stop container
make docker-stop

# View container logs
make docker-logs

# Open shell in container
make docker-shell

# Push to Docker Hub
make docker-push
```

### Maintenance

```bash
# Update dependencies
make update-deps

# Freeze dependencies to requirements.txt
make freeze

# Check for outdated packages
make requirements-check

# Verify environment
make verify
```

## Workflow Examples

### Daily Development

```bash
# Start your day
make start          # Start server
make logs           # Monitor output

# Make code changes, then test
make restart        # Restart with changes
make health         # Verify API responding

# Before committing
make pre-commit     # Run lint, format-check, type-check
```

### Quick Test Cycle

```bash
# Option 1: Watch mode (auto-runs tests on changes)
make test-watch

# Option 2: Manual run with coverage
make test-cov
```

### Full Check Before Push

```bash
# Run all quality checks and tests
make check

# Or comprehensive all-in-one
make all            # clean + install + lint + format + test
```

### Debugging Issues

```bash
# Server won't start?
make verify         # Check environment
make status         # Check if already running
make logs-view      # View recent logs
make start-fg       # Start in foreground to see errors

# Database connection issues?
make db-test        # Test direct connection
make db-status      # Check via API
```

### Docker Deployment

```bash
# Build and test locally
make docker-build
make docker-run

# In another terminal
make health         # Test endpoint
make docker-stop    # Stop when done

# Push to registry
make docker-push
```

## Tips

- **Colored Output**: Commands use color coding (green=success, yellow=info, red=error)
- **PID Tracking**: Server PID stored in `.otel-demo.pid` for reliable stop/restart
- **Log Management**: Logs saved to `logs/otel-demo.log` for debugging
- **Environment Loading**: `.env` automatically loaded when starting server
- **Pre-commit Integration**: `make pre-commit` runs same checks as git hooks

## Troubleshooting

### Server Already Running

```bash
make stop           # Stop existing server
make start          # Start fresh
```

### Port 8080 In Use

```bash
# Kill any process using port 8080
lsof -ti:8080 | xargs kill -9

# Or use make stop
make stop
```

### Environment Not Set Up

```bash
# Run full setup
make setup

# Or verify what's missing
make verify
```

### Stale PID File

```bash
# Make stop handles this automatically
make stop

# Or manually
rm .otel-demo.pid
```

## Integration with Other Tools

### Pre-commit Hooks

```bash
# Run checks that pre-commit will run
make pre-commit

# Or full suite
make check
```

### CI/CD Pipeline

```bash
# Same commands used in GitHub Actions
make lint
make test
make docker-build
```

## Quick Reference Table

| Task | Command |
|------|---------|
| Start server | `make start` |
| Stop server | `make stop` |
| Restart | `make restart` |
| View logs | `make logs` |
| Test API | `make health` |
| Test database | `make db-status` |
| Run tests | `make test` |
| Lint code | `make lint` |
| Format code | `make format` |
| Run all checks | `make check` |
| Build Docker | `make docker-build` |
| Help | `make help` |

---

For more details on any command, run `make help` or check the [Makefile](../Makefile) source.
