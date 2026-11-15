#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "          UTSS TYPESCRIPT SUB-PROJECT VERIFICATION SUITE"
echo "================================================================================"

echo ""
echo "[Step 1/3] Compiling TypeScript source files..."
npm run build

echo ""
echo "[Step 2/3] Executing unit & integration test suite..."
npm test

echo ""
echo "[Step 3/3] Running verification catalog harvest..."
node --no-warnings dist/cli.js harvest --db catalog_ts_verify.db --reset --stratum0 --std-recommended --demo-workspace
node --no-warnings dist/cli.js report --db catalog_ts_verify.db
rm -f catalog_ts_verify.db

echo ""
echo "================================================================================"
echo " [VERIFIED] All TypeScript tests and verification steps passed cleanly!"
echo "================================================================================"
