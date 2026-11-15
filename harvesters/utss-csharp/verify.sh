#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ ! -d "${XDG_RUNTIME_DIR}" ]; then
    export XDG_RUNTIME_DIR=/tmp
fi
export DOTNET_CLI_DO_NOT_USE_GLOBAL_MUTEX=1

echo "=== 1. Building UTSS C# Solution ==="
dotnet build UTSS.CSharp.slnx

echo ""
echo "=== 2. Running xUnit Test Suite ==="
dotnet test UTSS.CSharp.slnx --verbosity normal

echo ""
echo "=== 3. Executing Full Spectrum Harvest (Ambient + BCL + Demo Workspace) ==="
DB_PATH="$SCRIPT_DIR/catalog_cs_demo.db"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- harvest --db "$DB_PATH" --reset --all

echo ""
echo "=== 4. Diagnostic Spectrum Catalog Report ==="
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- report --db "$DB_PATH"

echo ""
echo "=== 5. Sample Facet & Symbol Queries ==="
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db "$DB_PATH" --workspace-symbols --facets

echo ""
echo "================================================================"
echo " [SUCCESS] UTSS C# / .NET Cataloger Verification Completed 100%"
echo "================================================================"
