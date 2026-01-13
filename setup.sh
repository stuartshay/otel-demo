#!/bin/bash
# OTel Demo Setup Script
# Development environment setup for OpenTelemetry demo application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== OTel Demo Environment Setup ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Step 1: Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"
else
    echo -e "${RED}Python 3 is required but not installed${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${BLUE}Step 2: Setting up Python virtual environment...${NC}"
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate venv and install dependencies
echo ""
echo -e "${BLUE}Step 3: Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install dev dependencies
echo ""
echo -e "${BLUE}Step 4: Installing development tools...${NC}"
DEV_PACKAGES=(
    "pre-commit"
    "pytest"
    "pytest-cov"
    "mypy"
    "types-Flask"
)

for pkg in "${DEV_PACKAGES[@]}"; do
    if ! pip show "$pkg" &> /dev/null; then
        pip install "$pkg" -q
        echo -e "${GREEN}✓ $pkg installed${NC}"
    else
        echo -e "${YELLOW}$pkg already installed${NC}"
    fi
done

# Setup pre-commit hooks
echo ""
echo -e "${BLUE}Step 5: Setting up pre-commit hooks...${NC}"
if [[ -d ".git" ]]; then
    pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
else
    echo -e "${YELLOW}Not a git repository - skipping pre-commit setup${NC}"
fi

# Check Docker
echo ""
echo -e "${BLUE}Step 6: Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        echo -e "${GREEN}✓ Docker ${DOCKER_VERSION} is running${NC}"
    else
        echo -e "${YELLOW}⚠ Docker installed but not running or no permissions${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Docker not installed (optional for local development)${NC}"
fi

# Create .env template if not exists
echo ""
echo -e "${BLUE}Step 7: Checking environment configuration...${NC}"
if [[ ! -f ".env" ]]; then
    cat > .env << 'EOF'
# OTel Demo Configuration
# Copy this file and update values as needed

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
OTEL_SERVICE_NAME=otel-demo
OTEL_SERVICE_NAMESPACE=otel-demo
OTEL_ENVIRONMENT=development

# Application Configuration
APP_VERSION=1.0.0
PORT=8080

# For New Relic direct export (optional)
# OTEL_EXPORTER_OTLP_HEADERS=api-key=YOUR_NEW_RELIC_LICENSE_KEY
EOF
    echo -e "${GREEN}✓ Template .env created${NC}"
else
    echo -e "${YELLOW}.env file already exists${NC}"
fi

# Verify setup
echo ""
echo -e "${BLUE}Step 8: Verifying setup...${NC}"
python -c "import flask; import opentelemetry; print('✓ Core imports successful')"
echo -e "${GREEN}✓ All imports verified${NC}"

# Deactivate venv
deactivate

echo ""
echo "==================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "==================================="
echo ""
echo "To start development:"
echo "  1. Activate venv:  source venv/bin/activate"
echo "  2. Run app:        python app.py"
echo "  3. Test:           curl http://localhost:8080/health"
echo ""
echo "Available endpoints:"
echo "  /health  - Health check"
echo "  /ready   - Readiness check"
echo "  /        - Service info with trace ID"
echo "  /chain   - Nested spans demo"
echo "  /error   - Error recording demo"
echo "  /slow    - Slow operation demo"
echo ""
echo "Before committing:"
echo "  pre-commit run -a"
echo ""
echo -e "${GREEN}Happy tracing! 🔍${NC}"
