"""
Diagnostic queries and reporting functions for UTSS SQLite catalog databases.
Implements the verification queries from Section 5 of Ideation/1.md and Ideation/2.md.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any


def print_spectrum_report(conn: sqlite3.Connection, db_path: Path | str) -> None:
    """Prints a formatted summary report of the cataloged environment."""
    print("======================================================================")
    print(f" PYTHON SPECTRUM CATALOG SUMMARY ({db_path})")
    print("======================================================================")

    env = conn.execute("SELECT * FROM environments LIMIT 1;").fetchone()
    if env:
        plat_extra = f", platform={env[8]}" if len(env) > 8 else ""
        print(f" Runtime   : {env[2]} {env[3]} on {env[7]} ({env[-1]}{plat_extra})")

    print("\n--- 1. Containers by Stratum & Origin Kind ---")
    rows = conn.execute(
        """
        SELECT d.stratum, d.dist_name, c.container_kind, f.module_origin_kind,
               SUM(CASE WHEN c.is_hidden = 0 THEN 1 ELSE 0 END) AS public_cnt,
               SUM(CASE WHEN c.is_hidden = 1 THEN 1 ELSE 0 END) AS hidden_cnt
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN py_container_facets f ON c.container_id = f.container_id
        WHERE c.container_kind IN ('ambient_scope', 'module', 'package')
        GROUP BY d.stratum, d.dist_name, c.container_kind, f.module_origin_kind
        ORDER BY d.stratum, c.container_kind;
        """
    ).fetchall()
    for stratum, dist_name, c_kind, orig_kind, pub_c, hid_c in rows:
        print(f"  [Stratum {stratum}: {dist_name:<15}] {c_kind:<14} ({str(orig_kind):<12}) -> Public: {pub_c:>4}, Hidden (_): {hid_c:>4}")

    print("\n--- 2. Symbols by Stratum, Kind & Visibility ---")
    sym_rows = conn.execute(
        """
        SELECT d.stratum, s.symbol_kind, s.visibility, s.provenance, COUNT(*)
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        GROUP BY d.stratum, s.symbol_kind, s.visibility, s.provenance
        ORDER BY d.stratum, COUNT(*) DESC;
        """
    ).fetchall()
    for stratum, s_kind, vis, prov, cnt in sym_rows[:25]:
        print(f"  [Stratum {stratum}] {s_kind:<14} | vis={vis:<17} | prov={prov:<15} : {cnt:>6,}")

    print("\n--- 3. Cross-Module Re-Exports & C-Accelerator Aliases (Sample) ---")
    alias_rows = conn.execute(
        """
        SELECT c.qualified_name, a.exposed_name, a.target_module_name, a.target_symbol_name, a.alias_kind
        FROM symbol_aliases a
        JOIN containers c ON a.source_container_id = c.container_id
        WHERE a.alias_kind IN ('c_accelerator_reexport', 'explicit_all_reexport')
        LIMIT 15;
        """
    ).fetchall()
    for src_mod, exp_name, tgt_mod, tgt_sym, akind in alias_rows:
        print(f"  {src_mod}.{exp_name:<24} -> {tgt_mod}.{tgt_sym:<24} ({akind})")

    # Pass 4: Overload summary if present
    ov_count = conn.execute("SELECT COUNT(*) FROM callable_overloads;").fetchone()[0]
    if ov_count > 0:
        print(f"\n--- 4. Polymorphic @overload Sets ({ov_count:,} variants registered) ---")
        ov_sample = conn.execute(
            """
            SELECT con.qualified_name, s.name, COUNT(o.overload_id)
            FROM callable_overloads o
            JOIN callables c ON o.callable_symbol_id = c.symbol_id
            JOIN symbols s ON c.symbol_id = s.symbol_id
            JOIN containers con ON s.container_id = con.container_id
            GROUP BY con.qualified_name, s.name
            LIMIT 10;
            """
        ).fetchall()
        for c_qname, func_name, count in ov_sample:
            print(f"  {c_qname}.{func_name:<20} -> {count} @overload signatures")


def query_ambient_scope(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query A: Everything usable in a fresh Python file WITHOUT any import statement."""
    print("\n--- Query A: Ambient Scope (<ambient>) ---")
    rows = conn.execute(
        """
        SELECT s.symbol_kind, s.name, s.provenance, c.raw_signature, m.runtime_type_name
        FROM symbols s
        JOIN containers con ON s.container_id = con.container_id
        LEFT JOIN callables c ON s.symbol_id = c.symbol_id
        LEFT JOIN state_members m ON s.symbol_id = m.symbol_id
        WHERE con.qualified_name = '<ambient>'
        ORDER BY s.symbol_kind, s.name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    print(f"  {'Kind':<14} | {'Name':<24} | {'Provenance':<16} | {'Type / Signature'}")
    print("  " + "-" * 75)
    for kind, name, prov, sig, rtype in rows:
        desc = sig or rtype or ""
        if len(desc) > 35:
            desc = desc[:32] + "..."
        print(f"  {kind:<14} | {name:<24} | {prov:<16} | {desc}")


def query_module_symbols(conn: sqlite3.Connection, module_name: str, limit: int = 100) -> None:
    """Query B: Public vs. Hidden (_) symbols inside a specific module."""
    print(f"\n--- Query B: Module '{module_name}' Symbols ---")
    rows = conn.execute(
        """
        SELECT s.visibility, s.symbol_kind, s.name, c.raw_signature, pf.py_runtime_type
        FROM symbols s
        JOIN containers con ON s.container_id = con.container_id
        LEFT JOIN callables c ON s.symbol_id = c.symbol_id
        LEFT JOIN py_symbol_facets pf ON s.symbol_id = pf.symbol_id
        WHERE con.qualified_name = ?
        ORDER BY s.is_hidden, s.name
        LIMIT ?;
        """,
        (module_name, limit),
    ).fetchall()
    if not rows:
        print(f"  No symbols found for module '{module_name}'.")
        return
    print(f"  {'Visibility':<16} | {'Kind':<12} | {'Name':<24} | {'Details'}")
    print("  " + "-" * 75)
    for vis, kind, name, sig, ptype in rows:
        detail = sig or ptype or ""
        if len(detail) > 35:
            detail = detail[:32] + "..."
        print(f"  {vis:<16} | {kind:<12} | {name:<24} | {detail}")


def query_c_accelerator_reexports(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query C: Trace public stdlib facades back to their hidden C-extension implementations."""
    print("\n--- Query C: C-Accelerator Re-Exports (Public Facades -> C Implementations) ---")
    rows = conn.execute(
        """
        SELECT con.qualified_name AS public_module,
               a.exposed_name,
               a.target_module_name AS backing_hidden_module,
               a.target_symbol_name,
               a.alias_kind
        FROM symbol_aliases a
        JOIN containers con ON a.source_container_id = con.container_id
        WHERE a.alias_kind = 'c_accelerator_reexport'
        ORDER BY con.qualified_name, a.exposed_name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    print(f"  {'Public Facade':<30} -> {'Backing C-Module Symbol':<30} | {'Alias Kind'}")
    print("  " + "-" * 85)
    for pub_mod, exp_name, tgt_mod, tgt_sym, akind in rows:
        src = f"{pub_mod}.{exp_name}"
        tgt = f"{tgt_mod}.{tgt_sym}"
        print(f"  {src:<30} -> {tgt:<30} | {akind}")


def query_overloads(conn: sqlite3.Connection, callable_name: str | None = None, limit: int = 50) -> None:
    """Query D: Inspect polymorphic @overload sets."""
    print("\n--- Query D: Polymorphic @overload Sets ---")
    sql = """
    SELECT con.qualified_name, s.name, o.overload_ordinal, o.raw_signature, o.return_type_expr
    FROM callable_overloads o
    JOIN callables c ON o.callable_symbol_id = c.symbol_id
    JOIN symbols s ON c.symbol_id = s.symbol_id
    JOIN containers con ON s.container_id = con.container_id
    """
    params: list[Any] = []
    if callable_name:
        sql += " WHERE s.name = ? "
        params.append(callable_name)
    sql += " ORDER BY con.qualified_name, s.name, o.overload_ordinal LIMIT ?;"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    if not rows:
        print("  No @overload signatures found in catalog.")
        return

    print(f"  {'Container':<20} | {'Name':<16} | {'Ord':<4} | {'Signature'}")
    print("  " + "-" * 75)
    for c_qname, name, ord_idx, sig, ret in rows:
        desc = sig or ret or ""
        if len(desc) > 40:
            desc = desc[:37] + "..."
        print(f"  {c_qname:<20} | {name:<16} | #{ord_idx:<3} | {desc}")


def query_pyi_enrichment(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query E: Inspect callables enriched via static .pyi stubs."""
    print("\n--- Query E: Static .pyi Enriched Callables ---")
    rows = conn.execute(
        """
        SELECT con.qualified_name, s.name, s.provenance, c.signature_source, c.raw_signature
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        JOIN containers con ON s.container_id = con.container_id
        WHERE c.signature_source LIKE 'pyi%'
        ORDER BY con.qualified_name, s.name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    if not rows:
        print("  No .pyi enriched callables found in catalog.")
        return

    print(f"  {'Container':<20} | {'Name':<16} | {'Source':<22} | {'Signature'}")
    print("  " + "-" * 75)
    for c_qname, name, prov, src, sig in rows:
        desc = sig or ""
        if len(desc) > 35:
            desc = desc[:32] + "..."
        print(f"  {c_qname:<20} | {name:<16} | {src:<22} | {desc}")


def run_custom_query(conn: sqlite3.Connection, sql: str, limit: int = 100) -> None:
    """Executes arbitrary SQL query and prints tabular results."""
    print(f"\n--- Custom Query: {sql} ---")
    cursor = conn.execute(sql)
    cols = [d[0] for d in cursor.description] if cursor.description else []
    print(" | ".join(cols))
    print("-" * 60)
    for row in cursor.fetchmany(limit):
        print(" | ".join(str(v) for v in row))


def query_workspace_symbols(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query F: Inspect Stratum 3 workspace symbols, synthesized init attributes, and coordinates."""
    print("\n--- Query F: Stratum 3 Workspace Symbols (Pure-AST, Zero Execution) ---")
    rows = conn.execute(
        """
        SELECT s.qualified_name, s.symbol_kind, s.visibility, s.provenance,
               COALESCE(c.raw_signature, m.declared_type_expr, m.runtime_type_name, '') AS detail,
               s.start_line
        FROM symbols s
        JOIN containers con ON s.container_id = con.container_id
        JOIN distributions d ON con.dist_id = d.dist_id
        LEFT JOIN callables c ON s.symbol_id = c.symbol_id
        LEFT JOIN state_members m ON s.symbol_id = m.symbol_id
        WHERE d.stratum = 3
        ORDER BY con.qualified_name, s.start_line, s.name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    if not rows:
        print("  No Stratum 3 workspace symbols found in catalog.")
        return

    print(f"  {'Loc':<6} | {'Qualified Name':<42} | {'Kind':<11} | {'Visibility':<16} | {'Provenance':<20} | Detail")
    print("  " + "-" * 110)
    for qname, skind, vis, prov, detail, sline in rows:
        loc = f"L{sline:<4}" if sline else "L?   "
        detail_str = str(detail)
        if len(detail_str) > 30:
            detail_str = detail_str[:27] + "..."
        print(f"  {loc} | {qname:<42} | {skind:<11} | {vis:<16} | {prov:<20} | {detail_str}")


def query_workspace_generators(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query G: Inspect Stratum 3 generator functions (yield) and coroutines (async def)."""
    print("\n--- Query G: Stratum 3 Generators & Coroutines ---")
    rows = conn.execute(
        """
        SELECT s.qualified_name, c.is_async, c.is_generator, c.raw_signature, c.signature_source
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        JOIN containers con ON s.container_id = con.container_id
        JOIN distributions d ON con.dist_id = d.dist_id
        WHERE d.stratum = 3 AND (c.is_generator = 1 OR c.is_async = 1)
        ORDER BY con.qualified_name, s.name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    if not rows:
        print("  No workspace generators or coroutines found in catalog.")
        return

    print(f"  {'Qualified Name':<42} | {'Async':<5} | {'Gen':<5} | {'Source':<20} | Signature")
    print("  " + "-" * 95)
    for qname, is_async, is_gen, sig, src in rows:
        desc = sig or ""
        if len(desc) > 35:
            desc = desc[:32] + "..."
        print(f"  {qname:<42} | {str(bool(is_async)):<5} | {str(bool(is_gen)):<5} | {src:<20} | {desc}")


def query_workspace_imports(conn: sqlite3.Connection, limit: int = 50) -> None:
    """Query H: Trace Stratum 3 workspace import edges and relative import resolution."""
    print("\n--- Query H: Stratum 3 Workspace Import & Re-Export Graph ---")
    rows = conn.execute(
        """
        SELECT con.qualified_name, a.exposed_name, a.target_module_name, a.target_symbol_name, a.alias_kind, a.is_in_dunder_all
        FROM symbol_aliases a
        JOIN containers con ON a.source_container_id = con.container_id
        JOIN distributions d ON con.dist_id = d.dist_id
        WHERE d.stratum = 3
        ORDER BY con.qualified_name, a.exposed_name
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    if not rows:
        print("  No workspace import edges found in catalog.")
        return

    print(f"  {'Importing Module':<28} | {'Exposed Name':<18} | Target -> Symbol (Kind)")
    print("  " + "-" * 85)
    for src_mod, exp_name, tgt_mod, tgt_sym, akind, in_all in rows:
        all_badge = " [in __all__]" if in_all else ""
        print(f"  {src_mod:<28} | {exp_name:<18} | {tgt_mod}.{tgt_sym} ({akind}{all_badge})")

