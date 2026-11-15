#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== 1. Checking and Compiling UTSS Rust Solution ==="
cargo check

echo ""
echo "=== 2. Running Rust Test Suite ==="
cargo test --verbose

echo ""
echo "=== 3. Executing Full Spectrum Harvest (Ambient + Std + Demo Workspace) ==="
DB_PATH="$SCRIPT_DIR/catalog_rust_demo.db"
cargo run -- harvest --db "$DB_PATH" --reset --all

echo ""
echo "=== 4. Diagnostic Spectrum Catalog Report ==="
cargo run -- report --db "$DB_PATH"

echo ""
echo "=== 5. Sample Facet & Symbol Queries ==="
cargo run -- query --db "$DB_PATH" --workspace-symbols --facets

echo ""
echo "================================================================"
echo " [SUCCESS] UTSS Rust Cataloger Verification Completed 100%"
echo "================================================================"
