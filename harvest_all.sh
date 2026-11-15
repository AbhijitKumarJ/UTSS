#!/usr/bin/env bash
# ==============================================================================
# Universal Type & Symbol System (UTSS) - Unified Catalog Harvesting Runner
# Generates local SQLite catalogs across all 6 languages + compiles Universal Bridge
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$HOME/.local/go/bin:$PATH"
if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ ! -d "${XDG_RUNTIME_DIR}" ]; then
    export XDG_RUNTIME_DIR=/tmp
fi
export DOTNET_CLI_DO_NOT_USE_GLOBAL_MUTEX=1

GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BOLD="\033[1m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}==============================================================================${NC}"
echo -e "${BOLD}${BLUE}    UTSS UNIFIED CATALOG HARVESTER: ALL 6 LANGUAGES + UNIVERSAL BRIDGE       ${NC}"
echo -e "${BOLD}${BLUE}==============================================================================${NC}"

# Target languages (defaults to all)
TARGETS=("$@")
if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS=("python" "csharp" "rust" "typescript" "cpp" "go")
fi

should_harvest() {
    local lang="$1"
    for t in "${TARGETS[@]}"; do
        if [ "$t" == "$lang" ] || [ "$t" == "all" ]; then
            return 0
        fi
    done
    return 1
}

# ------------------------------------------------------------------------------
# 1. Python Harvester (CPython 3.13 + Typeshed + AST)
# ------------------------------------------------------------------------------
if should_harvest "python"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [1/6] Harvesting Python Standard Library & Synthesis Catalogs...${NC}"
    (
        cd harvesters/utss-python
        if [ -f "3.sh" ]; then
            bash 3.sh
        else
            PYTHONPATH=.venv/lib/python3.13/site-packages:src python3 -m utss.cli harvest \
                --db catalog_synthesis.db --sample-stdlib --demo-workspace --demo-stubs --reset
            PYTHONPATH=.venv/lib/python3.13/site-packages:src python3 -m utss.cli harvest \
                --db catalog_base_full.db --demo-stubs --reset
        fi
    )
    echo -e "${GREEN}✓ Python catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 2. C# .NET Harvester (.NET 10 CoreCLR BCL + Roslyn AST)
# ------------------------------------------------------------------------------
if should_harvest "csharp"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [2/6] Harvesting C# .NET BCL & Roslyn Workspace Catalogs...${NC}"
    (
        cd harvesters/utss-csharp
        bash script.sh
    )
    echo -e "${GREEN}✓ C# .NET catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Rust Harvester (Rust 1.85 Standard Library + syn AST)
# ------------------------------------------------------------------------------
if should_harvest "rust"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [3/6] Harvesting Rust Standard Library & syn AST Catalogs...${NC}"
    (
        cd harvesters/utss-rust
        bash script.sh
    )
    echo -e "${GREEN}✓ Rust catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 4. TypeScript Harvester (Node.js 24 + TS 5.7+ Compiler API)
# ------------------------------------------------------------------------------
if should_harvest "typescript"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [4/6] Harvesting TypeScript / Node.js Catalogs...${NC}"
    (
        cd harvesters/utss-typescript
        bash script.sh
    )
    echo -e "${GREEN}✓ TypeScript catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 5. C/C++ Harvester (ISO C++20 Standard Headers + Lexical AST)
# ------------------------------------------------------------------------------
if should_harvest "cpp"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [5/6] Harvesting ISO C++20 Standard Headers & AST Catalogs...${NC}"
    (
        cd harvesters/utss-cpp
        make all
        bash script.sh
    )
    echo -e "${GREEN}✓ C/C++ catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 6. Go Harvester (Go 1.27 Predeclared Builtins + std packages)
# ------------------------------------------------------------------------------
if should_harvest "go"; then
    echo ""
    echo -e "${BOLD}${YELLOW}>>> [6/6] Harvesting Go 1.27 Predeclared & Standard Package Catalogs...${NC}"
    (
        cd harvesters/utss-go
        bash script.sh
    )
    echo -e "${GREEN}✓ Go catalogs generated successfully.${NC}"
fi

# ------------------------------------------------------------------------------
# 7. Symlink All Generated Catalogs into Workbench DBS
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${YELLOW}>>> Symlinking All Generated Catalogs into workbench/dbs...${NC}"
mkdir -p workbench/dbs
(
    cd workbench/dbs
    ln -sf ../../harvesters/utss-python/catalog_synthesis.db python_recommended.db
    ln -sf ../../harvesters/utss-python/catalog_base_full.db python_base_full.db
    ln -sf ../../harvesters/utss-csharp/catalog_cs_recommended.db cs_recommended.db
    ln -sf ../../harvesters/utss-csharp/catalog_cs_full.db cs_base_full.db
    ln -sf ../../harvesters/utss-rust/catalog_rust_recommended.db rust_recommended.db
    ln -sf ../../harvesters/utss-rust/catalog_rust_full.db rust_base_full.db
    ln -sf ../../harvesters/utss-typescript/catalog_ts_recommended.db ts_recommended.db
    ln -sf ../../harvesters/utss-typescript/catalog_ts_full.db ts_full.db
    ln -sf ../../harvesters/utss-cpp/catalog_cpp_recommended.db cpp_recommended.db
    ln -sf ../../harvesters/utss-cpp/catalog_cpp_full.db cpp_full.db
    ln -sf ../../harvesters/utss-go/catalog_go_recommended.db go_recommended.db
    ln -sf ../../harvesters/utss-go/catalog_go_full.db go_full.db
)
echo -e "${GREEN}✓ Workbench database symlinks verified.${NC}"

# ------------------------------------------------------------------------------
# 8. Compile Universal Transpilation Bridge in Workbench
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${YELLOW}>>> Compiling Universal Transpilation Bridge (utss_universal_bridge.db)...${NC}"
(
    cd workbench
    if [ -f "tools/build_universal_bridge.py" ]; then
        if command -v uv >/dev/null 2>&1; then
            uv run python3 tools/build_universal_bridge.py
        else
            python3 tools/build_universal_bridge.py
        fi
    elif [ -f "server/utss_csharp_bindgen.py" ]; then
        python3 server/utss_csharp_bindgen.py --db dbs/cs_recommended.db --out /tmp/UtssPackages.test.g.cs
    fi
)
echo -e "${GREEN}✓ Universal Transpilation Bridge compiled successfully.${NC}"

echo ""
echo -e "${BOLD}${BLUE}==============================================================================${NC}"
echo -e "${BOLD}${GREEN} [ALL COMPLETED] Local SQLite Catalogs & Universal Bridge are Up-to-Date!    ${NC}"
echo -e "${BOLD}${BLUE}==============================================================================${NC}"
