"""
Command-Line Interface (CLI) for UTSS.
Provides `harvest`, `overlay`, `report`, and `query` subcommands.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys
from typing import Sequence

from utss.cataloger import PythonSpectrumCataloger
from utss.overlay import StaticPyiOverlayCataloger
from utss.queries import (
    print_spectrum_report,
    query_ambient_scope,
    query_c_accelerator_reexports,
    query_module_symbols,
    query_overloads,
    query_pyi_enrichment,
    query_workspace_generators,
    query_workspace_imports,
    query_workspace_symbols,
    run_custom_query,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utss",
        description="UTSS: Universal Type & Symbol System for Transpilers (Empirical Python Environment Harvester).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. HARVEST command
    p_harvest = subparsers.add_parser("harvest", help="Harvest environment symbols into SQLite catalog.")
    p_harvest.add_argument(
        "--db",
        type=Path,
        default=Path("python_spectrum_catalog.db"),
        help="Target SQLite catalog database path (default: python_spectrum_catalog.db).",
    )
    p_harvest.add_argument(
        "--stdlib-modules",
        nargs="*",
        help="Optional subset of stdlib modules to harvest (omit to harvest all stdlib modules).",
    )
    p_harvest.add_argument(
        "--include-submodules",
        action="store_true",
        help="Also recursively walk package submodules in stdlib.",
    )
    p_harvest.add_argument(
        "--third-party",
        nargs="*",
        help="Optional list of installed third-party packages to harvest.",
    )
    p_harvest.add_argument(
        "--workspace",
        type=Path,
        help="Optional local workspace directory to harvest Stratum 3 source files via AST.",
    )
    p_harvest.add_argument(
        "--demo-workspace",
        action="store_true",
        help="Create and harvest an embedded multi-file Python workspace in a temporary directory to test Stratum 3.",
    )
    p_harvest.add_argument(
        "--demo-stubs",
        action="store_true",
        help="Apply embedded demo typeshed stubs (builtins, sys, os, json) after harvesting.",
    )
    p_harvest.add_argument(
        "--typeshed-dir",
        type=Path,
        help="Path to a custom Typeshed directory to overlay after harvesting.",
    )
    p_harvest.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all database tables before harvesting.",
    )

    # 2. OVERLAY command
    p_overlay = subparsers.add_parser("overlay", help="Apply static .pyi typeshed stubs to an existing catalog.")
    p_overlay.add_argument(
        "--db",
        type=Path,
        default=Path("python_spectrum_catalog.db"),
        help="Catalog SQLite database path.",
    )
    p_overlay.add_argument(
        "--demo-stubs",
        action="store_true",
        help="Apply embedded demo typeshed stubs (builtins, sys, os, json).",
    )
    p_overlay.add_argument(
        "--typeshed-dir",
        type=Path,
        help="Path to a custom Typeshed directory.",
    )
    p_overlay.add_argument(
        "--modules",
        nargs="*",
        help="Optional subset of modules to overlay.",
    )

    # 3. REPORT command
    p_report = subparsers.add_parser("report", help="Display summary diagnostic report of a catalog.")
    p_report.add_argument(
        "--db",
        type=Path,
        default=Path("python_spectrum_catalog.db"),
        help="Catalog SQLite database path.",
    )

    # 4. QUERY command
    p_query = subparsers.add_parser("query", help="Run diagnostic queries against the catalog.")
    p_query.add_argument(
        "--db",
        type=Path,
        default=Path("python_spectrum_catalog.db"),
        help="Catalog SQLite database path.",
    )
    p_query.add_argument(
        "--ambient",
        action="store_true",
        help="Run Query A: Inspect Stratum 0 ambient scope (no-import symbols).",
    )
    p_query.add_argument(
        "--module",
        type=str,
        help="Run Query B: Inspect public vs. hidden symbols inside a specific module.",
    )
    p_query.add_argument(
        "--c-accelerators",
        action="store_true",
        help="Run Query C: Trace public facades to their backing C-extension implementations.",
    )
    p_query.add_argument(
        "--overloads",
        action="store_true",
        help="Run Query D: Inspect polymorphic @overload sets in catalog.",
    )
    p_query.add_argument(
        "--pyi-enriched",
        action="store_true",
        help="Run Query E: Inspect callables enriched via static .pyi stubs.",
    )
    p_query.add_argument(
        "--workspace-symbols",
        action="store_true",
        help="Run Query F: Inspect Stratum 3 workspace symbols, synthesized init attributes, and coordinates.",
    )
    p_query.add_argument(
        "--workspace-generators",
        action="store_true",
        help="Run Query G: Inspect Stratum 3 generator functions (yield) and coroutines (async def).",
    )
    p_query.add_argument(
        "--workspace-imports",
        action="store_true",
        help="Run Query H: Trace Stratum 3 workspace import edges and relative import resolution.",
    )
    p_query.add_argument(
        "--sql",
        type=str,
        help="Run custom raw SQL query.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "harvest":
        conn = sqlite3.connect(str(args.db))
        cataloger = PythonSpectrumCataloger(conn)
        cataloger.init_db(reset=args.reset)
        cataloger.register_environment()

        print(f"[1/4] Harvesting Stratum 0: Ambient Scope...")
        cataloger.harvest_stratum_0_ambient()

        print(f"[2/4] Harvesting Stratum 1: Stdlib Modules...")
        mod_filter = set(args.stdlib_modules) if args.stdlib_modules else None
        cataloger.harvest_stratum_1_stdlib(module_filter=mod_filter, include_submodules=args.include_submodules)

        print(f"[3/4] Harvesting Stratum 2: Third-Party Packages...")
        tp_filter = set(args.third_party) if args.third_party is not None else set()
        cataloger.harvest_stratum_2_third_party(target_packages=tp_filter)

        if args.demo_workspace:
            import tempfile
            from utss.workspace import EMBEDDED_DEMO_WORKSPACE_FILES
            print(f"[4/4] Harvesting Stratum 3: Embedded Demo Workspace in sandbox...")
            with tempfile.TemporaryDirectory(prefix="utss_demo_ws_") as tmp_dir:
                tmp_root = Path(tmp_dir) / "commerce_workspace"
                for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
                    dest = tmp_root / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content.strip() + "\n", encoding="utf-8")
                cataloger.harvest_stratum_3_workspace(workspace_dir=tmp_root, project_name="commerce_workspace")
        elif args.workspace:
            print(f"[4/4] Harvesting Stratum 3: Workspace AST from {args.workspace}...")
            cataloger.harvest_stratum_3_workspace(workspace_dir=args.workspace)
        else:
            print(f"[4/4] Stratum 3: Workspace AST skipped (pass --workspace <path> or --demo-workspace to enable).")

        if args.demo_stubs:
            print("[Pass 4] Applying embedded demo .pyi typeshed stubs...")
            cataloger.apply_pyi_overlay(use_demo_stubs=True)
        elif args.typeshed_dir:
            print(f"[Pass 4] Applying custom Typeshed overlay from {args.typeshed_dir}...")
            cataloger.apply_pyi_overlay(typeshed_dir=args.typeshed_dir)

        print_spectrum_report(conn, args.db)
        conn.close()
        return 0

    elif args.command == "overlay":
        if not args.db.exists():
            print(f"Error: Database file not found: {args.db}", file=sys.stderr)
            return 1
        conn = sqlite3.connect(str(args.db))
        overlay_engine = StaticPyiOverlayCataloger(conn)
        mod_filter = set(args.modules) if args.modules else None

        if args.demo_stubs:
            print("Applying embedded demo stubs...")
            overlay_engine.overlay_embedded_demo_stubs()
            print("Applied embedded demo stubs successfully.")
        elif args.typeshed_dir:
            print(f"Applying typeshed from {args.typeshed_dir}...")
            overlay_engine.overlay_from_directory(args.typeshed_dir, module_filter=mod_filter)
            print("Applied typeshed successfully.")
        else:
            dirs = overlay_engine.auto_discover_typeshed_dirs()
            if not dirs:
                print("No typeshed directories auto-discovered. Pass --demo-stubs or --typeshed-dir.", file=sys.stderr)
                conn.close()
                return 1
            for d in dirs:
                print(f"Applying auto-discovered typeshed from {d}...")
                overlay_engine.overlay_from_directory(d, module_filter=mod_filter)

        conn.close()
        return 0

    elif args.command == "report":
        if not args.db.exists():
            print(f"Error: Database file not found: {args.db}", file=sys.stderr)
            return 1
        conn = sqlite3.connect(str(args.db))
        print_spectrum_report(conn, args.db)
        conn.close()
        return 0

    elif args.command == "query":
        if not args.db.exists():
            print(f"Error: Database file not found: {args.db}", file=sys.stderr)
            return 1
        conn = sqlite3.connect(str(args.db))
        if args.ambient:
            query_ambient_scope(conn)
        if args.module:
            query_module_symbols(conn, args.module)
        if args.c_accelerators:
            query_c_accelerator_reexports(conn)
        if args.overloads:
            query_overloads(conn)
        if args.pyi_enriched:
            query_pyi_enrichment(conn)
        if args.workspace_symbols:
            query_workspace_symbols(conn)
        if args.workspace_generators:
            query_workspace_generators(conn)
        if args.workspace_imports:
            query_workspace_imports(conn)
        if args.sql:
            run_custom_query(conn, args.sql)
        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
