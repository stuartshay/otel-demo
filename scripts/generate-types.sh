#!/bin/bash
# Generate TypeScript types from OpenAPI specification
# Usage: ./scripts/generate-types.sh [API_URL]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TYPES_DIR="$PROJECT_ROOT/packages/otel-types"

# Default to production URL, can override with argument
API_URL="${1:-https://otel.lab.informationcart.com}"
SPEC_URL="${API_URL}/apispec.json"

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

# Fetch OpenAPI spec
echo -e "${BLUE}Step 1: Fetching OpenAPI spec from ${SPEC_URL}${NC}"
TEMP_SPEC=$(mktemp)

if curl -sf -o "$TEMP_SPEC" "$SPEC_URL"; then
    echo -e "${GREEN}✓ Spec downloaded successfully${NC}"
else
    echo -e "${RED}✗ Failed to fetch spec from ${SPEC_URL}${NC}"
    echo -e "${YELLOW}Tip: Make sure the API is running and accessible${NC}"
    rm -f "$TEMP_SPEC"
    exit 1
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
if npx tsc --noEmit "$OUTPUT_FILE" 2>&1 | grep -q "error"; then
    echo -e "${YELLOW}⚠ TypeScript validation warnings (may be expected)${NC}"
else
    echo -e "${GREEN}✓ TypeScript syntax valid${NC}"
fi

echo ""
echo -e "${GREEN}=== Type generation complete! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Review types: cat $OUTPUT_FILE"
echo "  2. Update version in package.json if needed"
echo "  3. Publish to npm: cd $TYPES_DIR && npm publish"
echo ""
