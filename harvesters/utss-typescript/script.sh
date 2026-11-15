#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "    UTSS TYPESCRIPT HARVESTER: BASE CATALOG & SYNTHESIS PROFILES"
echo "================================================================================"

# Ensure project is compiled
npm run build

# ------------------------------------------------------------------------------
# PROFILE 1 [RECOMMENDED]: Curated Tier-1 TypeScript/Node.js Stdlib + Workspace
# ------------------------------------------------------------------------------
# Optimal profile for cross-language transpilation and code synthesis.
# Covers core ECMAScript runtime globals, keywords, utility types, curated Tier-1
# native modules (node:fs, node:path, node:events, node:crypto, node:stream,
# node:buffer, node:util, node:os, node:http, node:process), plus pure AST workspace.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 1 [RECOMMENDED]: Curated Tier-1 Standard Modules + Workspace"
echo " Target Database: catalog_ts_recommended.db"
echo "------------------------------------------------------------------------------"

node --no-warnings dist/cli.js \
    harvest \
    --db catalog_ts_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

echo ""
echo "[Profile 1 Diagnostics] Recommended Catalog Spectrum Report:"
node --no-warnings dist/cli.js report --db catalog_ts_recommended.db

echo ""
echo "[Profile 1 Diagnostics] Stratum 0 Ambient Keywords, Primitives & Builtins:"
node --no-warnings dist/cli.js query --db catalog_ts_recommended.db --ambient

echo ""
echo "[Profile 1 Diagnostics] Stratum 3 Workspace Symbols & AST Coordinates:"
node --no-warnings dist/cli.js query --db catalog_ts_recommended.db --workspace-symbols

echo ""
echo "[Profile 1 Diagnostics] TypeScript Container & Symbol Fidelity Facets:"
node --no-warnings dist/cli.js query --db catalog_ts_recommended.db --ts-facets

# ------------------------------------------------------------------------------
# PROFILE 2 [FULL]: Full Standard Library Distribution
# ------------------------------------------------------------------------------
# Complete coverage over all 46 native Node.js / ECMAScript standard modules.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 2 [FULL]: Full Node.js Standard Library Distribution (46 native modules)"
echo " Target Database: catalog_ts_full.db"
echo "------------------------------------------------------------------------------"

node --no-warnings dist/cli.js \
    harvest \
    --db catalog_ts_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

echo ""
echo "[Profile 2 Diagnostics] Full Standard Distribution Spectrum Report:"
node --no-warnings dist/cli.js report --db catalog_ts_full.db

echo ""
echo "[Profile 2 Diagnostics] Stratum 1 Standard Library Modules Breakdown:"
node --no-warnings dist/cli.js query --db catalog_ts_full.db --stdlib

echo ""
echo "================================================================================"
echo " [SUCCESS] All TypeScript Catalog Profiles Generated & Analyzed 100%"
echo "================================================================================"
