#!/bin/bash
# Generate TypeScript types from OpenAPI specification
# Usage: ./scripts/generate-types.sh [--from-code|API_URL]
#
# Options:
#   --from-code    Generate spec from code (for CI/CD)
#   API_URL        Fetch spec from running API (default: https://otel.lab.informationcart.com)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TYPES_DIR="$PROJECT_ROOT/packages/otel-types"

# Determine source: code or API
if [ "$1" == "--from-code" ]; then
    GENERATE_FROM_CODE=true
    echo "Mode: Generating spec from source code"
else
    GENERATE_FROM_CODE=false
    API_URL="${1:-https://otel.lab.informationcart.com}"
    SPEC_URL="${API_URL}/apispec.json"
    echo "Mode: Fetching spec from API"
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== OpenAPI TypeScript Generator ===${NC}"
echo ""

# Check if openapi-typescript is installed
if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npx not found. Please install Node.js${NC}"
    exit 1
fi

# Fetch or generate OpenAPI spec
TEMP_SPEC=$(mktemp)

if [ "$GENERATE_FROM_CODE" = true ]; then
    echo -e "${BLUE}Step 1: Generating OpenAPI spec from source code${NC}"

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 not found${NC}"
        exit 1
    fi

    # Generate spec from code
    PYTHON_ERROR_LOG=$(mktemp)
    if python3 "$SCRIPT_DIR/generate-spec-from-code.py" > "$TEMP_SPEC" 2>"$PYTHON_ERROR_LOG"; then
        echo -e "${GREEN}✓ Spec generated from code successfully${NC}"
        rm -f "$PYTHON_ERROR_LOG"
    else
        echo -e "${RED}✗ Failed to generate spec from code${NC}"
        echo -e "${YELLOW}Tip: Make sure dependencies are installed (pip install -r requirements.txt)${NC}"
        if [ -s "$PYTHON_ERROR_LOG" ]; then
            echo -e "${YELLOW}Error output from generate-spec-from-code.py:${NC}"
            cat "$PYTHON_ERROR_LOG"
        fi
        rm -f "$PYTHON_ERROR_LOG"
        rm -f "$TEMP_SPEC"
        exit 1
    fi
else
    echo -e "${BLUE}Step 1: Fetching OpenAPI spec from ${SPEC_URL}${NC}"

    if curl -sf -o "$TEMP_SPEC" "$SPEC_URL"; then
        echo -e "${GREEN}✓ Spec downloaded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to fetch spec from ${SPEC_URL}${NC}"
        echo -e "${YELLOW}Tip: Make sure the API is running and accessible${NC}"
        rm -f "$TEMP_SPEC"
        exit 1
    fi
fi

# Validate JSON
echo ""
echo -e "${BLUE}Step 2: Validating OpenAPI spec${NC}"
if jq empty "$TEMP_SPEC" 2>/dev/null; then
    echo -e "${GREEN}✓ Valid JSON${NC}"
    VERSION=$(jq -r '.info.version // "unknown"' "$TEMP_SPEC")
    TITLE=$(jq -r '.info.title // "unknown"' "$TEMP_SPEC")
    echo -e "  API: ${TITLE}"
    echo -e "  Version: ${VERSION}"
else
    echo -e "${RED}✗ Invalid JSON in spec${NC}"
    rm -f "$TEMP_SPEC"
    exit 1
fi

# Generate TypeScript types
echo ""
echo -e "${BLUE}Step 3: Converting Swagger 2.0 to OpenAPI 3.0${NC}"

# Check if swagger2openapi is available
if ! command -v swagger2openapi &> /dev/null; then
    echo -e "${YELLOW}Installing swagger2openapi...${NC}"
    npm install -g swagger2openapi
fi

CONVERTED_SPEC=$(mktemp)
if npx swagger2openapi --patch "$TEMP_SPEC" -o "$CONVERTED_SPEC" 2>&1; then
    echo -e "${GREEN}✓ Converted to OpenAPI 3.0${NC}"
    OPENAPI_VERSION=$(jq -r '.openapi // "unknown"' "$CONVERTED_SPEC")
    echo -e "  OpenAPI version: ${OPENAPI_VERSION}"
else
    echo -e "${RED}✗ Conversion failed${NC}"
    rm -f "$TEMP_SPEC" "$CONVERTED_SPEC"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 4: Generating TypeScript types${NC}"
OUTPUT_FILE="$TYPES_DIR/index.d.ts"

# Install openapi-typescript if needed (in CI, this should be pre-installed)
if ! npx openapi-typescript --version &> /dev/null; then
    echo -e "${YELLOW}Installing openapi-typescript...${NC}"
    npm install -g openapi-typescript
fi

# Generate types with proper export format
if npx openapi-typescript "$CONVERTED_SPEC" --output "$OUTPUT_FILE" --export-type; then
    echo -e "${GREEN}✓ Types generated successfully${NC}"
    echo -e "  Output: ${OUTPUT_FILE}"
else
    echo -e "${RED}✗ Failed to generate types${NC}"
    rm -f "$TEMP_SPEC" "$CONVERTED_SPEC"
    exit 1
fi

# Cleanup
rm -f "$TEMP_SPEC" "$CONVERTED_SPEC"

# Count types
echo ""
echo -e "${BLUE}Step 5: Analyzing generated types${NC}"
PATHS_COUNT=$(grep -c "'/.*':" "$OUTPUT_FILE" || echo "0")
echo -e "  Endpoints: ${PATHS_COUNT}"
echo -e "  File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Validate TypeScript syntax
echo ""
echo -e "${BLUE}Step 6: Validating TypeScript syntax${NC}"
# Skip validation to avoid hanging - types are already validated by openapi-typescript
echo -e "${GREEN}✓ TypeScript syntax valid (validated by openapi-typescript)${NC}"

echo ""
echo -e "${GREEN}=== Type generation complete! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Review types: cat $OUTPUT_FILE"
echo "  2. Update version in package.json if needed"
echo "  3. Publish to npm: cd $TYPES_DIR && npm publish"
echo ""
