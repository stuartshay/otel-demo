# Contributing to otel-demo

Thank you for contributing to otel-demo! This document outlines our development workflow and contribution guidelines.

## 🚨 Critical Rule: Branch Protection

**NEVER commit directly to the `main` branch.**

All changes must go through pull requests from either:

- `develop` branch (for regular development)
- `feature/*` branches (for isolated features)

Direct commits to `main` are **strictly forbidden** and will be rejected.

## Branch Strategy

### Branch Types

| Branch      | Purpose             | Direct Commits | PRs To                  |
| ----------- | ------------------- | -------------- | ----------------------- |
| `main`      | Production releases | ❌ FORBIDDEN   | N/A (receives PRs only) |
| `develop`   | Active development  | ✅ Allowed     | `main`                  |
| `feature/*` | Isolated features   | ✅ Allowed     | `main`                  |

### Workflow Options

#### Option 1: Regular Development (develop → main)

Use this for most changes:

```bash
# Start on develop
git checkout develop
git pull origin develop

# Make your changes
# ... edit files ...

# Run checks
pre-commit run -a
python -m pytest tests/

# Commit and push
git add .
git commit -m "feat: add new feature"
git push origin develop

# Create PR on GitHub: develop → main
```

#### Option 2: Feature Branch (feature/\* → main)

Use this for larger isolated features:

```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/awesome-feature

# Make your changes
# ... edit files ...

# Run checks
pre-commit run -a
python -m pytest tests/

# Commit and push
git add .
git commit -m "feat: implement awesome feature"
git push origin feature/awesome-feature

# Create PR on GitHub: feature/awesome-feature → main
```

## Development Requirements

### Before You Commit

1. ✅ Run pre-commit: `pre-commit run -a`
2. ✅ Type check: `mypy app/`
3. ✅ Tests pass: `python -m pytest tests/`
4. ✅ Test locally: `python run.py`
5. ✅ Pre-commit hooks pass (automatic)

### Code Standards

- **Python**: Follow PEP 8, use type hints
- **Flask**: Follow Flask best practices
- **OpenTelemetry**: Always add custom spans for business logic
- **Logging**: Use structured logging with trace context
- **Security**: Never commit secrets, API keys, or credentials
- **Environment**: Use environment variables for configuration

## Pull Request Process

1. **Create PR** from `develop` or `feature/*` to `main`
2. **Fill PR template** with description of changes
3. **Wait for checks** (lint, tests, Docker build)
4. **Request review** from maintainers
5. **Address feedback** if requested
6. **Merge** after approval

### PR Naming Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add new /distance endpoint`
- `fix: resolve trace propagation issue`
- `docs: update README with environment variables`
- `chore: bump dependencies`
- `refactor: simplify telemetry setup`

## CI/CD Pipeline

When you merge to `main`:

1. GitHub Actions runs lint, type check, and tests
2. Docker image is built and pushed to Docker Hub
3. Version is read from VERSION file (e.g., `1.0.84`)
4. Image tag follows semantic versioning
5. Argo CD auto-syncs deployment to k8s-pi5-cluster

## Local Development Setup

```bash
# Clone repository
git clone https://github.com/stuartshay/otel-demo.git
cd otel-demo

# Switch to develop
git checkout develop

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Start development server
python run.py

# Open http://localhost:8080
```

## Testing

```bash
# Activate venv
source venv/bin/activate

# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=app tests/

# Run specific test
python -m pytest tests/test_health.py -v
```

## Environment Variables

The application uses these environment variables (see `app/config.py`):

```bash
# OpenTelemetry Configuration
OTEL_SERVICE_NAME=otel-demo
OTEL_SERVICE_NAMESPACE=homelab
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector.observability:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_INSECURE=true

# Deployment Environment
DEPLOYMENT_ENVIRONMENT=development  # or production

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
```

## Version Management

This project uses a VERSION file for semantic versioning:

```bash
# Bump patch version (1.0.84 → 1.0.85)
./scripts/update-version.sh 1.0.85

# Commit and push
git add VERSION pyproject.toml .env.sample
git commit -m "chore: bump version to 1.0.85"
git push origin develop

# Create PR to main for release
```

See [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md) for details.

## Troubleshooting

### Build Errors

```bash
# Clean install
rm -rf venv
./setup.sh
source venv/bin/activate
```

### OpenTelemetry Issues

```bash
# Check OTel collector connectivity
curl -v http://otel-collector.observability:4317

# Verify trace export in logs
tail -f logs/app.log | grep trace_id
```

### Git Issues

```bash
# If you accidentally committed to main (before pushing)
git checkout develop
git cherry-pick <commit-sha>
git checkout main
git reset --hard origin/main
```

## Testing Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Service info (returns trace ID)
curl http://localhost:8080/

# Chain demo (nested spans)
curl http://localhost:8080/chain

# Error demo
curl http://localhost:8080/error

# Latency demo
curl http://localhost:8080/slow
```

## Getting Help

- 📖 [README](README.md) - Project overview and quick start
- 📚 [Documentation](docs/) - Detailed guides
- 🐛 [Issues](https://github.com/stuartshay/otel-demo/issues) - Report bugs or request features
- 💬 [Discussions](https://github.com/stuartshay/otel-demo/discussions) - Ask questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
