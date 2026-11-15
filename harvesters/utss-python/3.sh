#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo " UTSS PYTHON HARVESTER: BASE CATALOG & CROSS-LANGUAGE SYNTHESIS PROFILES"
echo "================================================================================"

# ------------------------------------------------------------------------------
# 1. Check & Ensure Local Typeshed Availability
# ------------------------------------------------------------------------------
TYPESHED_DIR=""
if [ -d "$SCRIPT_DIR/typeshed/stdlib" ]; then
    TYPESHED_DIR="$SCRIPT_DIR/typeshed/stdlib"
elif [ -d "$HOME/.local/share/uv/tools/jupyterlab/lib/python3.13/site-packages/jedi/third_party/typeshed/stdlib" ]; then
    TYPESHED_DIR="$HOME/.local/share/uv/tools/jupyterlab/lib/python3.13/site-packages/jedi/third_party/typeshed/stdlib"
fi

if [ -n "$TYPESHED_DIR" ]; then
    echo "[Typeshed] Detected local typeshed checkout at: $TYPESHED_DIR"
else
    echo "[Typeshed] Local typeshed not found; will fallback to built-in embedded demo stubs."
fi

# ------------------------------------------------------------------------------
# PROFILE A: Recommended Tier-1 Synthesis Catalog (Curated Stdlib + Workspace)
# ------------------------------------------------------------------------------
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE A: Recommended Synthesis Catalog (Curated Tier-1 Stdlib + Workspace)"
echo " Database: catalog_synthesis.db"
echo "------------------------------------------------------------------------------"

uv run utss harvest \
    --db catalog_synthesis.db \
    --stdlib-modules \
        sys os io json math time datetime pathlib \
        collections collections.abc itertools functools dataclasses enum \
        typing re hashlib base64 uuid random csv \
    --demo-workspace \
    --demo-stubs \
    --reset

echo ""
echo "[Profile A Diagnostics] Workspace AST Symbols & Coordinates (Query F):"
uv run utss query --db catalog_synthesis.db --workspace-symbols

echo ""
echo "[Profile A Diagnostics] Generator Functions (yield) & Coroutines (async def) (Query G):"
uv run utss query --db catalog_synthesis.db --workspace-generators

echo ""
echo "[Profile A Diagnostics] Workspace Import & Re-export Dependency Graph (Query H):"
uv run utss query --db catalog_synthesis.db --workspace-imports


# ------------------------------------------------------------------------------
# PROFILE B: Full Python Base Catalog Generation (Full 289+ Stdlib + Full Typeshed)
# ------------------------------------------------------------------------------
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE B: Full Python Base Catalog Generation (Full Stdlib + Typeshed)"
echo " Database: catalog_base_full.db"
echo "------------------------------------------------------------------------------"

if [ -n "$TYPESHED_DIR" ]; then
    echo "[Profile B] Harvesting all stdlib modules + full typeshed overlay from $TYPESHED_DIR..."
    uv run utss harvest \
        --db catalog_base_full.db \
        --typeshed-dir "$TYPESHED_DIR" \
        --reset
else
    echo "[Profile B] Harvesting all stdlib modules with embedded demo stubs..."
    uv run utss harvest \
        --db catalog_base_full.db \
        --demo-stubs \
        --reset
fi

echo ""
echo "[Profile B Diagnostics] Spectrum Report Summary:"
uv run utss report --db catalog_base_full.db

echo ""
echo "[Profile B Diagnostics] Sample Polymorphic @overload Sets (Query D):"
uv run utss query --db catalog_base_full.db --overloads

echo ""
echo "[Profile B Diagnostics] Sample Statically Enriched Callables (Query E):"
uv run utss query --db catalog_base_full.db --pyi-enriched

echo ""
echo "================================================================================"
echo " [SUCCESS] All Base Catalog & Synthesis Profiles Generated & Verified 100%"
echo "================================================================================"
