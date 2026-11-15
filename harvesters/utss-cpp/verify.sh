#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "            UTSS C/C++ SUB-PROJECT VERIFICATION SUITE"
echo "================================================================================"

echo ""
echo "[Step 1/3] Building C/C++ binaries..."
make all

echo ""
echo "[Step 2/3] Executing test suite..."
make test

echo ""
echo "[Step 3/3] Running verification catalog harvest..."
./bin/utss-cpp harvest --db catalog_cpp_verify.db --reset --stratum0 --std-recommended --demo-workspace
./bin/utss-cpp report --db catalog_cpp_verify.db
rm -f catalog_cpp_verify.db

echo ""
echo "================================================================================"
echo " [VERIFIED] All C/C++ tests and verification steps passed cleanly!"
echo "================================================================================"
