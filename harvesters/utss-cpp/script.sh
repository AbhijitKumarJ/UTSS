#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "      UTSS C/C++ HARVESTER: BASE CATALOG & SYNTHESIS PROFILES"
echo "================================================================================"

# Compile C++ cataloger
make all

# ------------------------------------------------------------------------------
# PROFILE 1 [RECOMMENDED]: Curated Tier-1 ISO C++ Standard Library + Workspace
# ------------------------------------------------------------------------------
# Optimal profile for cross-language transpilation and code synthesis.
# Covers fundamental C++20 keywords, primitive types, curated Tier-1 headers
# (<iostream>, <vector>, <string>, <memory>, <filesystem>, <cstdio>, <cstdlib>),
# plus pure AST workspace extraction.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 1 [RECOMMENDED]: Curated Tier-1 C++ Standard Library + Workspace"
echo " Target Database: catalog_cpp_recommended.db"
echo "------------------------------------------------------------------------------"

./bin/utss-cpp \
    harvest \
    --db catalog_cpp_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

echo ""
echo "[Profile 1 Diagnostics] Recommended Catalog Spectrum Report:"
./bin/utss-cpp report --db catalog_cpp_recommended.db

echo ""
echo "[Profile 1 Diagnostics] Stratum 0 Ambient Keywords, Primitives & Builtins:"
./bin/utss-cpp query --db catalog_cpp_recommended.db --ambient

echo ""
echo "[Profile 1 Diagnostics] Stratum 3 Workspace Symbols & AST Coordinates:"
./bin/utss-cpp query --db catalog_cpp_recommended.db --workspace-symbols

echo ""
echo "[Profile 1 Diagnostics] C++ Container & Symbol Fidelity Facets:"
./bin/utss-cpp query --db catalog_cpp_recommended.db --cpp-facets

# ------------------------------------------------------------------------------
# PROFILE 2 [FULL]: Full ISO C++20 Standard Library Distribution
# ------------------------------------------------------------------------------
# Complete coverage over 64 standard ISO C++20 headers.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 2 [FULL]: Full ISO C++20 Standard Library Distribution (64 headers)"
echo " Target Database: catalog_cpp_full.db"
echo "------------------------------------------------------------------------------"

./bin/utss-cpp \
    harvest \
    --db catalog_cpp_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

echo ""
echo "[Profile 2 Diagnostics] Full Standard Distribution Spectrum Report:"
./bin/utss-cpp report --db catalog_cpp_full.db

echo ""
echo "[Profile 2 Diagnostics] Stratum 1 Standard Library Modules Breakdown:"
./bin/utss-cpp query --db catalog_cpp_full.db --stdlib

echo ""
echo "================================================================================"
echo " [SUCCESS] All C/C++ Catalog Profiles Generated & Analyzed 100%"
echo "================================================================================"
