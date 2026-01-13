# Agent Operating Guide

All automation, assistants, and developers must follow
`.github/copilot-instructions.md` for workflow, safety, and environment rules.

## How to Use

- Read `.github/copilot-instructions.md` before making changes
- Apply every rule in that file as-is; do not redefine or override them here
- If updates are needed, edit `.github/copilot-instructions.md` and keep this
  file pointing to it

## Quick Reference

- **Lint before commit**: `pre-commit run -a`
- **Run locally**: `python app.py` or `./setup.sh && source venv/bin/activate && python app.py`
- **Docker build**: `docker build -t otel-demo .`
- **Test endpoints**: `curl http://localhost:8080/health`

## Development Workflow

1. Run `./setup.sh` to set up environment
2. Activate venv: `source venv/bin/activate`
3. Make changes to `app.py`
4. Test locally: `python app.py`
5. Run `pre-commit run -a`
6. Commit and push
