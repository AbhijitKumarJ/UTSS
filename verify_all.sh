#!/usr/bin/env bash
# ==============================================================================
# Universal Type & Symbol System (UTSS) - Monorepo Test Verification Runner
# Runs the full test suite across all 6 language harvesters & workbench bindgen
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$HOME/.local/go/bin:$PATH"

GREEN="\033[0;32m"
BLUE="\033[0;34m"
RED="\033[0;31m"
BOLD="\033[1m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}==============================================================================${NC}"
echo -e "${BOLD}${BLUE}    UTSS MONOREPO VERIFICATION: ALL 6 LANGUAGE HARVESTERS + WORKBENCH        ${NC}"
echo -e "${BOLD}${BLUE}==============================================================================${NC}"

TOTAL_PASSED=0
TOTAL_FAILED=0

run_check() {
    local name="$1"
    local dir="$2"
    local cmd="$3"

    echo ""
    echo -e "${BOLD}[Testing $name]${NC} Directory: $dir"
    echo -e "Command: $cmd"

    if (cd "$dir" && eval "$cmd"); then
        echo -e "${GREEN}✓ [$name] PASSED${NC}"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
    else
        echo -e "${RED}✗ [$name] FAILED${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi
}

# 1. Python Harvester
run_check "utss-python" "harvesters/utss-python" \
    "PYTHONPATH=.venv/lib/python3.13/site-packages:src python3 -m pytest tests"

# 2. C# .NET Harvester
run_check "utss-csharp" "harvesters/utss-csharp" \
    "dotnet test --no-restore tests/UTSS.CSharp.Tests/UTSS.CSharp.Tests.csproj"

# 3. Rust Harvester
run_check "utss-rust" "harvesters/utss-rust" \
    "cargo test"

# 4. TypeScript Harvester
run_check "utss-typescript" "harvesters/utss-typescript" \
    "npm test"

# 5. C/C++ Harvester
run_check "utss-cpp" "harvesters/utss-cpp" \
    "make test"

# 6. Go Harvester
run_check "utss-go" "harvesters/utss-go" \
    "go test -v ./tests"

# 7. Workbench (93 Test Cases + C# Bindgen Verification)
run_check "utss-workbench" "workbench" \
    "uv run pytest tests && python3 tools/utss_csharp_bindgen.py --db dbs/cs_recommended.db --out /tmp/UtssPackages.test.g.cs"

echo ""
echo -e "${BOLD}${BLUE}==============================================================================${NC}"
if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${BOLD}${GREEN} [ALL PASSED] All $TOTAL_PASSED components verified successfully!${NC}"
    echo -e "${BOLD}${BLUE}==============================================================================${NC}"
    exit 0
else
    echo -e "${BOLD}${RED} [FAILURES] $TOTAL_FAILED components failed, $TOTAL_PASSED passed.${NC}"
    echo -e "${BOLD}${BLUE}==============================================================================${NC}"
    exit 1
fi
