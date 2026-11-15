#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ ! -d "${XDG_RUNTIME_DIR}" ]; then
    export XDG_RUNTIME_DIR=/tmp
fi
export DOTNET_CLI_DO_NOT_USE_GLOBAL_MUTEX=1

echo "================================================================================"
echo "   UTSS C# / .NET HARVESTER: BASE CATALOG & SYNTHESIS PROFILES"
echo "================================================================================"

# ------------------------------------------------------------------------------
# PROFILE 1 (RECOMMENDED): Curated Tier-1 BCL Standard Libraries + Workspace
# ------------------------------------------------------------------------------
# Optimal profile for cross-language transpilation and code synthesis.
# Covers the 68 core types across System, Linq, Collections, IO, Text, JSON,
# Regex, Tasks, and Networking, plus Ambient keywords/aliases & Workspace source.
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 1 [RECOMMENDED]: Curated Tier-1 BCL Libraries + Workspace"
echo " Target Database: catalog_cs_recommended.db"
echo "------------------------------------------------------------------------------"

dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- \
    harvest \
    --db catalog_cs_recommended.db \
    --reset \
    --stratum0 \
    --bcl-recommended \
    --demo-workspace

echo ""
echo "[Profile 1 Diagnostics] Recommended Catalog Spectrum Report:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- report --db catalog_cs_recommended.db

echo ""
echo "[Profile 1 Diagnostics] Stratum 0 Ambient Keywords, Primitive Aliases & Literals:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --ambient

echo ""
echo "[Profile 1 Diagnostics] Stratum 3 Workspace Symbols & AST Coordinates:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --workspace-symbols

echo ""
echo "[Profile 1 Diagnostics] C# Container Facets (Records, Interfaces, Structs, Classes):"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --facets


# ------------------------------------------------------------------------------
# PROFILE 2 [FULL]: Complete CoreCLR Base Class Library (1,400+ Types)
# ------------------------------------------------------------------------------
# Deep reflection over the entire CoreCLR runtime surface (System.Private.CoreLib,
# System.Linq, System.Collections, System.IO.FileSystem, System.Text.Json,
# System.Text.RegularExpressions, System.Net.Http, System.Threading.Tasks).
echo ""
echo "------------------------------------------------------------------------------"
echo " PROFILE 2 [FULL]: Complete CoreCLR BCL Assembly Catalog (1,400+ Types)"
echo " Target Database: catalog_cs_full.db"
echo "------------------------------------------------------------------------------"

dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- \
    harvest \
    --db catalog_cs_full.db \
    --reset \
    --stratum0 \
    --bcl-full \
    --demo-workspace

echo ""
echo "[Profile 2 Diagnostics] Full BCL Spectrum Report:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- report --db catalog_cs_full.db

echo ""
echo "[Profile 2 Diagnostics] Stratum 1 BCL Container Breakdown by Type Kind:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-summary

echo ""
echo "[Profile 2 Diagnostics] Top Polymorphic Method Overloads in .NET CoreCLR:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-overloads

echo ""
echo "[Profile 2 Diagnostics] Generic Type Parameters & Implemented Interfaces Sample:"
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-generics

echo ""
echo "================================================================================"
echo " [SUCCESS] All C# / .NET Catalog Profiles Generated & Analyzed 100%"
echo "================================================================================"
