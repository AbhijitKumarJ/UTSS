#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="/home/abhijit/.local/go/bin:$PATH"

echo "================================================================================"
echo "             UTSS GO SUB-PROJECT VERIFICATION SUITE"
echo "================================================================================"

echo ""
echo "[Step 1/3] Building Go binaries..."
go build -o bin/utss-go ./cmd/utss-go

echo ""
echo "[Step 2/3] Executing test suite..."
go test -v ./tests

echo ""
echo "[Step 3/3] Running verification catalog harvest..."
./bin/utss-go harvest --db catalog_go_verify.db --reset --stratum0 --std-recommended --demo-workspace
./bin/utss-go report --db catalog_go_verify.db
rm -f catalog_go_verify.db

echo ""
echo "================================================================================"
echo " [VERIFIED] All Go tests and verification steps passed cleanly!"
echo "================================================================================"
