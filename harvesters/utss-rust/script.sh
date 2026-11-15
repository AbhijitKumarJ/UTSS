#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "      UTSS RUST HARVESTER: BASE CATALOG & SYNTHESIS PROFILES"
echo "================================================================================"

# ------------------------------------------------------------------------------
# PROFILE 1 [RECOMMENDED]: Curated Tier-1 Standard Library + Workspace
# ------------------------------------------------------------------------------
# Optimal profile for cross-language transpilation and code synthesis.
# Covers core collections (HashMap, HashSet, Vec), IO (Read, Write, File),
# Path, Sync (Arc, Mutex), Time, Thread, plus Ambient Prelude & Workspace source.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 1 [RECOMMENDED]: Curated Tier-1 Rust Standard Library + Workspace"
echo " Target Database: catalog_rust_recommended.db"
echo "------------------------------------------------------------------------------"

cargo run -- \
    harvest \
    --db catalog_rust_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

echo ""
echo "[Profile 1 Diagnostics] Recommended Catalog Spectrum Report:"
cargo run -- report --db catalog_rust_recommended.db

echo ""
echo "[Profile 1 Diagnostics] Stratum 0 Ambient Keywords, Primitives & Prelude Items:"
cargo run -- query --db catalog_rust_recommended.db --ambient

echo ""
echo "[Profile 1 Diagnostics] Stratum 3 Workspace Symbols & AST Coordinates:"
cargo run -- query --db catalog_rust_recommended.db --workspace-symbols

echo ""
echo "[Profile 1 Diagnostics] Rust Container Facets (Structs, Enums, Traits, Generics):"
cargo run -- query --db catalog_rust_recommended.db --facets


# ------------------------------------------------------------------------------
# PROFILE 2 [FULL]: Full Rust Standard Library Modules Surface
# ------------------------------------------------------------------------------
# Complete coverage over the 44 standard library modules in std/core/alloc.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 2 [FULL]: Full Rust Standard Library Distribution"
echo " Target Database: catalog_rust_full.db"
echo "------------------------------------------------------------------------------"

cargo run -- \
    harvest \
    --db catalog_rust_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace



cargo run -- harvest    --db catalog_rust_full.db     --reset     --stratum0     --std-full   --demo-workspace


echo ""
echo "[Profile 2 Diagnostics] Full Standard Library Spectrum Report:"
cargo run -- report --db catalog_rust_full.db

echo ""
echo "[Profile 2 Diagnostics] Stratum 1 Standard Library Breakdown by Item Kind:"
cargo run -- query --db catalog_rust_full.db --std-summary

echo ""
echo "================================================================================"
echo " [SUCCESS] All Rust Catalog Profiles Generated & Analyzed 100%"
echo "================================================================================"
