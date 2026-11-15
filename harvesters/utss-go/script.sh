#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="/home/abhijit/.local/go/bin:$PATH"

echo "================================================================================"
echo "        UTSS GO HARVESTER: BASE CATALOG & SYNTHESIS PROFILES"
echo "================================================================================"

# Compile Go cataloger
go build -o bin/utss-go ./cmd/utss-go

# ------------------------------------------------------------------------------
# PROFILE 1 [RECOMMENDED]: Curated Tier-1 Go Standard Library + Workspace
# ------------------------------------------------------------------------------
# Optimal profile for cross-language transpilation and code synthesis.
# Covers fundamental Go keywords, predeclared types, builtins, curated Tier-1
# packages (fmt, io, os, strings, strconv, time, sync, context, errors),
# plus pure AST workspace extraction.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 1 [RECOMMENDED]: Curated Tier-1 Go Standard Library + Workspace"
echo " Target Database: catalog_go_recommended.db"
echo "------------------------------------------------------------------------------"

./bin/utss-go \
    harvest \
    --db catalog_go_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

echo ""
echo "[Profile 1 Diagnostics] Recommended Catalog Spectrum Report:"
./bin/utss-go report --db catalog_go_recommended.db

echo ""
echo "[Profile 1 Diagnostics] Stratum 0 Ambient Keywords, Predeclared Types & Builtins:"
./bin/utss-go query --db catalog_go_recommended.db --ambient

echo ""
echo "[Profile 1 Diagnostics] Stratum 3 Workspace Symbols & AST Coordinates:"
./bin/utss-go query --db catalog_go_recommended.db --workspace-symbols

echo ""
echo "[Profile 1 Diagnostics] Go Container & Symbol Fidelity Facets:"
./bin/utss-go query --db catalog_go_recommended.db --go-facets

# ------------------------------------------------------------------------------
# PROFILE 2 [FULL]: Full Standard Library Package Distribution
# ------------------------------------------------------------------------------
# Complete coverage over 50+ Go standard library packages.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 2 [FULL]: Full Go Standard Library Distribution (50+ packages)"
echo " Target Database: catalog_go_full.db"
echo "------------------------------------------------------------------------------"

./bin/utss-go \
    harvest \
    --db catalog_go_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

echo ""
echo "[Profile 2 Diagnostics] Full Standard Distribution Spectrum Report:"
./bin/utss-go report --db catalog_go_full.db

echo ""
echo "[Profile 2 Diagnostics] Stratum 1 Standard Library Packages Breakdown:"
./bin/utss-go query --db catalog_go_full.db --stdlib

echo ""
echo "================================================================================"
echo " [SUCCESS] All Go Catalog Profiles Generated & Analyzed 100%"
echo "================================================================================"
