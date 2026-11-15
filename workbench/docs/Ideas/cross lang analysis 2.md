The **`utss_comparative_analysis.py`** research suite below connects to all 6 UTSS SQLite databases in read-only mode, aggregates both **Layer 1 Universal Core** and **Layer 2 Language-Fidelity Facet** tables into unified `pandas` DataFrames, generates a 6-chart visual analytics dashboard with `matplotlib` and `seaborn`, and exports the empirical crosswalk CSVs needed for Phase 4 type/protocol normalization.

---

## 1. What the Analysis Suite Computes & Plots

The script executes six cross-language experiments and outputs both high-resolution PNG charts and structured CSV datasets into `analysis_output/`:

* **Figure 1 (`01_strata_and_depth.png`) — Namespace Topology & Hierarchy Depth**: Side-by-side comparison of Stratum 0 (`<ambient>`) vs. Stratum 1 (Stdlib/BCL) symbol counts and a boxplot/distribution of container nesting depth (`parent_container_id` recursive hops) across all 6 languages.
* **Figure 2 (`02_parameter_passing_spectrum.png`) — The Parameter Passing & Ownership Matrix**: A 100% stacked horizontal bar chart profiling `parameters.pass_kind` (`positional_or_keyword`, `keyword_only`, `val`, `ref`, `mut_ref`, `const_ref`, `rvalue_ref`, `out`, `pointer`, `variadic`), quantifying the exact ownership impedance between Python/TypeScript and Rust/C++/C#/Go.
* **Figure 3 (`03_arity_defaults_overloads.png`) — Signature Complexity (Arity, Defaults & Overloads)**: A dual-panel chart measuring callable parameter counts, optional default argument percentages (`is_optional = 1`), and `@overload` multiplicity (`callable_overloads`) to show when a transpiler must synthesize Builder structs or disambiguated function names.
* **Figure 4 (`04_mutability_and_typing.png`) — State Mutability & Type Completeness**: Contrasts `state_members` mutability defaults (`is_mutable`, `is_constant`, `access_mode`) alongside static type annotation completeness on callables and parameters.
* **Figure 5 (`05_layer2_facets_and_protocols.png`) — Layer 2 Facet Crosswalk (Receivers & Dunder Protocols)**: Compares method receiver mechanics (`self_kind` in Rust, `receiver_kind` in Go, `is_const`/`is_noexcept` in C++, `readonly`/`ref struct` in C#) and maps Python's `dunder_category` protocols against target language traits and interfaces.
* **Dataset Export (`rosetta_sequence_crosswalk.csv` & `summary_metrics.csv`)**: Extracts the method-level Rosetta Crosswalk across all 6 standard libraries for `Sequence<T>` (`list`, `List<T>`, `Vec<T>`, `std::vector`, `Array<T>`, `slices`) and `Map<K,V>` (`dict`, `Dictionary<K,V>`, `HashMap<K,V>`, `std::map`, `Map<K,V>`, `maps`).



---

## 2. Complete Analysis Script (`utss_comparative_analysis.py`)

Save this script in the root of your UTSS repository or inside `server/analysis/utss_comparative_analysis.py`:

```python
#!/usr/bin/env python3
"""
UTSS Cross-Language Comparative Data Science & Bridge Synthesis Suite
=====================================================================
Connects to all 6 UTSS SQLite catalogs (Python, C#, Rust, TypeScript, C++, Go)
in read-only mode, builds unified Pandas DataFrames across Layer 1 & Layer 2
tables, generates a 5-figure Matplotlib/Seaborn research suite, and exports
empirical CSV crosswalks for Phase 4 transpiler normalization.

Usage:
    uv run python utss_comparative_analysis.py --db-dir ./dbs --out-dir ./analysis_output
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Consistent visual palette across all 6 languages
LANG_PALETTE: Dict[str, str] = {
    "python": "#3776AB",      # Python Blue
    "csharp": "#68217A",      # .NET Purple
    "rust": "#DEA584",        # Rust Orange/Bronze
    "typescript": "#3178C6",  # TS Azure
    "cpp": "#00599C",         # ISO C++ Cobalt
    "go": "#00ADD8",          # Go Cyan
}

# Known repository and workbench file locations for auto-discovery
DEFAULT_DB_CANDIDATES: Dict[str, List[str]] = {
    "python": [
        "dbs/python_base_full.db",
        "dbs/python_recommended.db",
        "catalog_base_full.db",
        "catalog.db",
    ],
    "csharp": [
        "dbs/cs_base_full.db",
        "dbs/catalog_cs_full.db",
        "dbs/cs_recommended.db",
        "Z_CS/catalog_cs_full.db",
    ],
    "rust": [
        "dbs/rust_base_full.db",
        "dbs/catalog_rust_full.db",
        "dbs/rust_recommended.db",
        "Z_Rust/catalog_rust_full.db",
    ],
    "typescript": [
        "dbs/ts_base_full.db",
        "dbs/catalog_ts_full.db",
        "dbs/ts_recommended.db",
        "Z_TS/catalog_ts_full.db",
    ],
    "cpp": [
        "dbs/cpp_base_full.db",
        "dbs/catalog_cpp_full.db",
        "dbs/cpp_recommended.db",
        "Z_C/catalog_cpp_full.db",
    ],
    "go": [
        "dbs/go_base_full.db",
        "dbs/catalog_go_full.db",
        "dbs/go_recommended.db",
        "Z_Go/catalog_go_full.db",
    ],
}


# ============================================================================
# 1. DATABASE DISCOVERY & READ-ONLY FEDERATION ENGINE
# ============================================================================

def discover_databases(base_dir: Path) -> Dict[str, Path]:
    """Locates the best available SQLite catalog for each of the 6 languages."""
    discovered: Dict[str, Path] = {}

    # 1. Check explicit candidate paths relative to base_dir and parent
    for lang, rel_paths in DEFAULT_DB_CANDIDATES.items():
        for rel in rel_paths:
            for root in (base_dir, base_dir.parent):
                candidate = (root / rel).resolve()
                if candidate.is_file():
                    discovered[lang] = candidate
                    break
            if lang in discovered:
                break

    # 2. Fallback: scan any *.db files in base_dir and inspect `environments.language`
    if len(discovered) < 6 and base_dir.is_dir():
        for db_file in sorted(base_dir.glob("*.db")):
            try:
                uri = f"file:{db_file.resolve()}?mode=ro"
                with sqlite3.connect(uri, uri=True) as conn:
                    row = conn.execute(
                        "SELECT LOWER(language) FROM environments LIMIT 1;"
                    ).fetchone()
                    if row and row[0] in DEFAULT_DB_CANDIDATES:
                        lang = row[0]
                        # Prefer *full* catalogs over smaller slices if both exist
                        if lang not in discovered or "full" in db_file.name:
                            discovered[lang] = db_file.resolve()
            except sqlite3.Error:
                continue

    return discovered


def query_single_db(db_path: Path, sql: str) -> pd.DataFrame:
    """Executes a read-only SQL query against a single UTSS SQLite database."""
    uri = f"file:{db_path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return pd.read_sql_query(sql, conn)


def query_across_all_dbs(dbs: Dict[str, Path], sql: str) -> pd.DataFrame:
    """Runs a Layer 1 Universal Core SQL query across all discovered DBs and concatenates."""
    frames: List[pd.DataFrame] = []
    for lang, db_path in dbs.items():
        try:
            df = query_single_db(db_path, sql)
            if not df.empty:
                if "language" not in df.columns:
                    df.insert(0, "language", lang)
                else:
                    df["language"] = df["language"].str.lower()
                frames.append(df)
        except Exception as exc:
            print(f"  [WARN] Query failed on {lang} ({db_path.name}): {exc}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ============================================================================
# 2. EMPIRICAL SQL EXTRACTORS (MODULES I - IV)
# ============================================================================

def extract_strata_and_topology(dbs: Dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extracts Stratum 0 vs Stratum 1 counts and recursive container hierarchy depth."""
    sql_strata = """
    SELECT
        LOWER(e.language) AS language,
        d.stratum,
        c.container_kind,
        s.symbol_kind,
        COUNT(DISTINCT c.container_id) AS container_count,
        COUNT(s.symbol_id) AS symbol_count
    FROM environments e
    JOIN distributions d ON d.env_id = e.env_id
    JOIN containers c ON c.dist_id = d.dist_id
    LEFT JOIN symbols s ON s.container_id = c.container_id AND s.is_hidden = 0
    GROUP BY e.language, d.stratum, c.container_kind, s.symbol_kind;
    """

    sql_depth = """
    WITH RECURSIVE container_tree AS (
        SELECT
            c.container_id,
            c.dist_id,
            c.container_kind,
            c.qualified_name,
            1 AS depth
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        WHERE d.stratum = 1 AND c.parent_container_id IS NULL
        UNION ALL
        SELECT
            child.container_id,
            child.dist_id,
            child.container_kind,
            child.qualified_name,
            parent.depth + 1 AS depth
        FROM containers child
        JOIN container_tree parent ON child.parent_container_id = parent.container_id
        WHERE parent.depth < 12
    )
    SELECT
        LOWER(e.language) AS language,
        ct.container_kind,
        ct.depth,
        COUNT(DISTINCT ct.container_id) AS container_count,
        COUNT(s.symbol_id) AS symbol_count
    FROM container_tree ct
    JOIN distributions d ON ct.dist_id = d.dist_id
    JOIN environments e ON d.env_id = e.env_id
    LEFT JOIN symbols s ON s.container_id = ct.container_id AND s.is_hidden = 0
    GROUP BY e.language, ct.container_kind, ct.depth;
    """
    return (
        query_across_all_dbs(dbs, sql_strata),
        query_across_all_dbs(dbs, sql_depth),
    )


def extract_parameter_passing(dbs: Dict[str, Path]) -> pd.DataFrame:
    """Extracts parameter pass_kind distributions across languages."""
    sql = """
    SELECT
        LOWER(e.language) AS language,
        p.pass_kind,
        COUNT(p.param_id) AS param_count,
        SUM(CASE WHEN p.is_optional = 1 OR p.default_expr IS NOT NULL THEN 1 ELSE 0 END) AS optional_count,
        SUM(CASE WHEN p.type_expr IS NOT NULL AND p.type_expr != '' THEN 1 ELSE 0 END) AS typed_count
    FROM parameters p
    JOIN callables cal ON p.callable_symbol_id = cal.symbol_id
    JOIN symbols s ON cal.symbol_id = s.symbol_id
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    JOIN environments e ON d.env_id = e.env_id
    WHERE s.is_hidden = 0
    GROUP BY e.language, p.pass_kind;
    """
    return query_across_all_dbs(dbs, sql)


def extract_callable_signatures(dbs: Dict[str, Path]) -> pd.DataFrame:
    """Extracts per-callable arity, optional default counts, overload counts, and async/generator flags."""
    sql = """
    SELECT
        LOWER(e.language) AS language,
        s.symbol_kind,
        cal.is_async,
        cal.is_generator,
        cal.has_overloads,
        cal.overload_count,
        CASE WHEN cal.return_type_expr IS NOT NULL AND cal.return_type_expr != '' THEN 1 ELSE 0 END AS has_return_type,
        CASE WHEN cal.type_params_json IS NOT NULL AND cal.type_params_json NOT IN ('', '[]') THEN 1 ELSE 0 END AS is_generic,
        COUNT(p.param_id) AS arity,
        SUM(CASE WHEN p.is_optional = 1 OR p.default_expr IS NOT NULL THEN 1 ELSE 0 END) AS optional_params
    FROM callables cal
    JOIN symbols s ON cal.symbol_id = s.symbol_id
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    JOIN environments e ON d.env_id = e.env_id
    LEFT JOIN parameters p ON p.callable_symbol_id = cal.symbol_id AND p.overload_id IS NULL
    WHERE s.is_hidden = 0
    GROUP BY e.language, cal.symbol_id, s.symbol_kind, cal.is_async, cal.is_generator,
             cal.has_overloads, cal.overload_count, has_return_type, is_generic;
    """
    return query_across_all_dbs(dbs, sql)


def extract_state_mutability(dbs: Dict[str, Path]) -> pd.DataFrame:
    """Extracts state_members mutability, constant flags, and access modes."""
    sql = """
    SELECT
        LOWER(e.language) AS language,
        s.symbol_kind,
        sm.access_mode,
        sm.is_constant,
        sm.is_mutable,
        CASE WHEN sm.declared_type_expr IS NOT NULL AND sm.declared_type_expr != '' THEN 1 ELSE 0 END AS has_declared_type,
        COUNT(sm.symbol_id) AS member_count
    FROM state_members sm
    JOIN symbols s ON sm.symbol_id = s.symbol_id
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    JOIN environments e ON d.env_id = e.env_id
    WHERE s.is_hidden = 0
    GROUP BY e.language, s.symbol_kind, sm.access_mode, sm.is_constant, sm.is_mutable, has_declared_type;
    """
    return query_across_all_dbs(dbs, sql)


def extract_layer2_facets(dbs: Dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extracts Layer 2 receiver/memory semantics and cross-language protocol families."""
    receiver_frames: List[pd.DataFrame] = []
    protocol_frames: List[pd.DataFrame] = []

    # 1. Python Dunder Protocols & Descriptors
    if "python" in dbs:
        py_rec = query_single_db(
            dbs["python"],
            """
            SELECT 'python' AS language,
                   COALESCE(descriptor_kind, py_runtime_type) AS semantic_category,
                   COUNT(*) AS count
            FROM py_symbol_facets
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(py_rec)

        py_proto = query_single_db(
            dbs["python"],
            """
            SELECT 'python' AS language,
                   dunder_category AS protocol_family,
                   COUNT(*) AS count
            FROM py_symbol_facets
            WHERE dunder_category IS NOT NULL
            GROUP BY dunder_category;
            """,
        )
        protocol_frames.append(py_proto)

    # 2. C# Value/Ref Structs & Operator/Interface Contracts
    if "csharp" in dbs:
        cs_rec = query_single_db(
            dbs["csharp"],
            """
            SELECT 'csharp' AS language,
                   CASE
                       WHEN is_ref_struct = 1 THEN 'ref_struct (stack)'
                       WHEN is_readonly_struct = 1 THEN 'readonly_struct'
                       WHEN type_kind LIKE '%struct%' THEN 'mutable_struct'
                       WHEN type_kind = 'interface' THEN 'interface'
                       ELSE type_kind
                   END AS semantic_category,
                   COUNT(*) AS count
            FROM cs_container_facets
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(cs_rec)

        cs_proto = query_single_db(
            dbs["csharp"],
            """
            SELECT 'csharp' AS language,
                   CASE
                       WHEN operator_kind LIKE '%Addition%' OR operator_kind LIKE '%Subtraction%' OR operator_kind LIKE '%Multiply%' THEN 'numeric'
                       WHEN operator_kind LIKE '%Equality%' OR operator_kind LIKE '%LessThan%' OR operator_kind LIKE '%GreaterThan%' THEN 'comparison'
                       WHEN member_kind = 'indexer' THEN 'container'
                       WHEN explicit_interface_specifier LIKE '%IDisposable%' THEN 'context_manager'
                       ELSE 'lifecycle'
                   END AS protocol_family,
                   COUNT(*) AS count
            FROM cs_symbol_facets
            WHERE operator_kind IS NOT NULL OR member_kind = 'indexer' OR explicit_interface_specifier IS NOT NULL
            GROUP BY protocol_family;
            """,
        )
        protocol_frames.append(cs_proto)

    # 3. Rust Ownership Receivers (self_kind) & Core Traits
    if "rust" in dbs:
        rs_rec = query_single_db(
            dbs["rust"],
            """
            SELECT 'rust' AS language,
                   'self: ' || self_kind || CASE WHEN is_unsafe = 1 THEN ' (unsafe)' ELSE '' END AS semantic_category,
                   COUNT(*) AS count
            FROM rust_symbol_facets
            WHERE member_kind IN ('method', 'associated_fn', 'fn')
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(rs_rec)

        rs_proto = query_single_db(
            dbs["rust"],
            """
            SELECT 'rust' AS language,
                   CASE
                       WHEN c.short_name IN ('Drop', 'Deref', 'DerefMut') THEN 'context_manager'
                       WHEN c.short_name IN ('Iterator', 'IntoIterator', 'Index', 'IndexMut') THEN 'container'
                       WHEN c.short_name IN ('PartialEq', 'Eq', 'PartialOrd', 'Ord', 'Hash') THEN 'comparison'
                       WHEN c.short_name IN ('Add', 'Sub', 'Mul', 'Div', 'Rem', 'Neg') THEN 'numeric'
                       ELSE 'lifecycle'
                   END AS protocol_family,
                   COUNT(s.symbol_id) AS count
            FROM rust_container_facets rcf
            JOIN containers c ON rcf.container_id = c.container_id
            LEFT JOIN symbols s ON s.container_id = c.container_id
            WHERE rcf.item_kind = 'trait'
            GROUP BY protocol_family;
            """,
        )
        protocol_frames.append(rs_proto)

    # 4. Go Value vs Pointer Receivers
    if "go" in dbs:
        go_rec = query_single_db(
            dbs["go"],
            """
            SELECT 'go' AS language,
                   'receiver: ' || receiver_kind AS semantic_category,
                   COUNT(*) AS count
            FROM go_symbol_facets
            WHERE member_kind IN ('method', 'func')
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(go_rec)

    # 5. C++ Const / Noexcept / Constexpr Method Guarantees
    if "cpp" in dbs:
        cpp_rec = query_single_db(
            dbs["cpp"],
            """
            SELECT 'cpp' AS language,
                   CASE
                       WHEN is_constexpr = 1 THEN 'constexpr'
                       WHEN is_const = 1 AND is_noexcept = 1 THEN 'const noexcept'
                       WHEN is_const = 1 THEN 'const method'
                       WHEN is_pure_virtual = 1 THEN 'pure virtual (=0)'
                       ELSE 'mutable / free'
                   END AS semantic_category,
                   COUNT(*) AS count
            FROM cpp_symbol_facets
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(cpp_rec)

    # 6. TypeScript Modifiers
    if "typescript" in dbs:
        ts_rec = query_single_db(
            dbs["typescript"],
            """
            SELECT 'typescript' AS language,
                   CASE
                       WHEN is_readonly = 1 THEN 'readonly member'
                       WHEN is_optional = 1 THEN 'optional (?)'
                       WHEN is_declare = 1 THEN 'ambient declare'
                       ELSE access_modifier
                   END AS semantic_category,
                   COUNT(*) AS count
            FROM ts_symbol_facets
            GROUP BY semantic_category;
            """,
        )
        receiver_frames.append(ts_rec)

    df_rec = pd.concat(receiver_frames, ignore_index=True) if receiver_frames else pd.DataFrame()
    df_proto = pd.concat(protocol_frames, ignore_index=True) if protocol_frames else pd.DataFrame()
    return df_rec, df_proto


def extract_rosetta_crosswalk(dbs: Dict[str, Path]) -> pd.DataFrame:
    """Builds the Rosetta Crosswalk table for Sequence<T> and Map<K,V> across all 6 DBs."""
    target_containers = {
        "python": ("builtins.list", "builtins.dict"),
        "csharp": ("System.Collections.Generic.List", "System.Collections.Generic.Dictionary"),
        "rust": ("alloc::vec::Vec", "std::collections::hash_map::HashMap"),
        "cpp": ("std::vector", "std::map"),
        "typescript": ("Array", "Map"),
        "go": ("slices", "maps"),
    }
    rows: List[pd.DataFrame] = []
    for lang, (seq_qname, map_qname) in target_containers.items():
        if lang not in dbs:
            continue
        sql = f"""
        SELECT
            '{lang}' AS language,
            CASE
                WHEN c.qualified_name LIKE '%{seq_qname.split("::")[-1].split(".")[-1]}' THEN 'Sequence<T>'
                ELSE 'Map<K,V>'
            END AS universal_concept,
            c.qualified_name AS container_qname,
            s.name AS operation_name,
            s.symbol_kind,
            cal.raw_signature,
            cal.return_type_expr
        FROM containers c
        JOIN symbols s ON s.container_id = c.container_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        WHERE c.qualified_name IN ('{seq_qname}', '{map_qname}', 'list', 'dict', 'std::vec::Vec')
          AND s.is_hidden = 0
          AND s.name IN (
              'append', 'Add', 'push', 'push_back', 'Insert', 'insert', 'set',
              '__len__', 'Count', 'len', 'size', 'length',
              'pop', 'Remove', 'RemoveAt', 'pop_back', 'clear', 'Clear', 'Delete', 'get', 'ContainsKey', 'contains_key'
          )
        ORDER BY universal_concept, s.name;
        """
        df = query_single_db(dbs[lang], sql)
        if not df.empty:
            rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


# ============================================================================
# 3. MATPLOTLIB / SEABORN VISUALIZATION SUITE
# ============================================================================

def plot_strata_and_depth(df_strata: pd.DataFrame, df_depth: pd.DataFrame, out_dir: Path) -> None:
    """Figure 1: Stratum 0 vs Stratum 1 Symbol Counts & Container Hierarchy Depth."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=160)

    # Panel A: Stratum 0 vs Stratum 1 Symbol Counts (Log Scale)
    if not df_strata.empty:
        strata_agg = (
            df_strata[df_strata["stratum"].isin([0, 1])]
            .groupby(["language", "stratum"], as_index=False)["symbol_count"]
            .sum()
        )
        strata_agg["stratum_label"] = strata_agg["stratum"].map(
            {0: "Stratum 0: Ambient (Zero-Import)", 1: "Stratum 1: Standard Library / BCL"}
        )
        sns.barplot(
            data=strata_agg,
            x="language",
            y="symbol_count",
            hue="stratum_label",
            ax=axes[0],
            palette=["#F59E0B", "#3B82F6"],
        )
        axes[0].set_yscale("log")
        axes[0].set_title("A. Symbol Inventory by Stratum (Log Scale)", fontsize=13, fontweight="bold")
        axes[0].set_xlabel("Language Runtime", fontsize=11)
        axes[0].set_ylabel("Total Public Symbols (log10)", fontsize=11)
        axes[0].legend(title="Concentric Stratum", frameon=True)
        axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    # Panel B: Container Nesting Depth Distribution in Stratum 1
    if not df_depth.empty:
        depth_pivot = df_depth.pivot_table(
            index="language",
            columns="depth",
            values="container_count",
            aggfunc="sum",
            fill_value=0,
        )
        depth_pct = depth_pivot.div(depth_pivot.sum(axis=1), axis=0) * 100.0
        depth_pct.plot(
            kind="bar",
            stacked=True,
            ax=axes[1],
            colormap="viridis",
            width=0.72,
        )
        axes[1].set_title("B. Stratum 1 Container Nesting Depth (% by Hop Depth)", fontsize=13, fontweight="bold")
        axes[1].set_xlabel("Language Runtime", fontsize=11)
        axes[1].set_ylabel("Percentage of Containers (%)", fontsize=11)
        axes[1].legend(title="Tree Depth", bbox_to_anchor=(1.02, 1), loc="upper left")
        axes[1].tick_params(axis="x", rotation=0)
        axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(out_dir / "01_strata_and_depth.png", bbox_inches="tight")
    plt.close(fig)


def plot_parameter_passing_spectrum(df_params: pd.DataFrame, out_dir: Path) -> None:
    """Figure 2: 100% Stacked Horizontal Bar Chart of parameters.pass_kind."""
    if df_params.empty:
        return

    fig, ax = plt.subplots(figsize=(14, 7), dpi=160)
    pivot = df_params.pivot_table(
        index="language",
        columns="pass_kind",
        values="param_count",
        aggfunc="sum",
        fill_value=0,
    )
    pct = pivot.div(pivot.sum(axis=1), axis=0) * 100.0
    pct.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        colormap="tab20",
        width=0.75,
        edgecolor="white",
        linewidth=0.6,
    )
    ax.set_title(
        "The Parameter Passing & Ownership Spectrum Across 6 Stdlibs (parameters.pass_kind)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Share of All Callable Parameters (%)", fontsize=11)
    ax.set_ylabel("Language", fontsize=11)
    ax.set_xlim(0, 100)
    ax.legend(
        title="Pass / Ownership Kind",
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
        ncol=1,
        frameon=True,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(out_dir / "02_parameter_passing_spectrum.png", bbox_inches="tight")
    plt.close(fig)


def plot_arity_defaults_overloads(df_callables: pd.DataFrame, out_dir: Path) -> None:
    """Figure 3: Callable Arity Distribution, Optional Default Ratio, and Overload Multiplicity."""
    if df_callables.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=160)

    # Panel A: Boxplot of Callable Arity (clamped at 99th percentile for readability)
    df_clamped = df_callables[df_callables["arity"] <= 10].copy()
    sns.boxplot(
        data=df_clamped,
        x="language",
        y="arity",
        hue="language",
        palette=LANG_PALETTE,
        legend=False,
        ax=axes[0],
        showfliers=False,
    )
    axes[0].set_title("A. Callable Parameter Count (Arity) Distribution", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Language Runtime", fontsize=11)
    axes[0].set_ylabel("Parameters per Callable", fontsize=11)
    axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    # Panel B: % Callables with Optional Defaults vs. % Callables with @overload Variants
    summary = (
        df_callables.groupby("language", as_index=False)
        .agg(
            total=("arity", "count"),
            with_defaults=("optional_params", lambda s: (s > 0).sum()),
            with_overloads=("has_overloads", lambda s: (s == 1).sum()),
            generic_callables=("is_generic", lambda s: (s == 1).sum()),
        )
    )
    summary["Pct Default Args"] = 100.0 * summary["with_defaults"] / summary["total"]
    summary["Pct Overloaded"] = 100.0 * summary["with_overloads"] / summary["total"]
    summary["Pct Generic"] = 100.0 * summary["generic_callables"] / summary["total"]

    melted = summary.melt(
        id_vars="language",
        value_vars=["Pct Default Args", "Pct Overloaded", "Pct Generic"],
        var_name="Signature Feature",
        value_name="Percentage",
    )
    sns.barplot(
        data=melted,
        x="language",
        y="Percentage",
        hue="Signature Feature",
        ax=axes[1],
        palette=["#10B981", "#EF4444", "#8B5CF6"],
    )
    axes[1].set_title(
        "B. Signature Impedance: Optional Defaults, Overloads & Generics (%)",
        fontsize=13,
        fontweight="bold",
    )
    axes[1].set_xlabel("Language Runtime", fontsize=11)
    axes[1].set_ylabel("Percentage of Public Callables (%)", fontsize=11)
    axes[1].legend(title="Feature", frameon=True)
    axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(out_dir / "03_arity_defaults_overloads.png", bbox_inches="tight")
    plt.close(fig)


def plot_mutability_and_typing(
    df_state: pd.DataFrame, df_callables: pd.DataFrame, out_dir: Path
) -> None:
    """Figure 4: State Member Mutability Modes & Callable Return-Type Completeness."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=160)

    # Panel A: State Member Mutability Breakdown
    if not df_state.empty:
        df_state["mutability_class"] = np.where(
            df_state["is_constant"] == 1,
            "Constant (is_constant=1)",
            np.where(
                df_state["is_mutable"] == 0,
                "Immutable Field (is_mutable=0)",
                "Mutable State (is_mutable=1)",
            ),
        )
        mut_pivot = df_state.pivot_table(
            index="language",
            columns="mutability_class",
            values="member_count",
            aggfunc="sum",
            fill_value=0,
        )
        mut_pct = mut_pivot.div(mut_pivot.sum(axis=1), axis=0) * 100.0
        mut_pct.plot(
            kind="bar",
            stacked=True,
            ax=axes[0],
            color=["#3B82F6", "#10B981", "#F97316"],
            width=0.7,
        )
        axes[0].set_title("A. State Members by Mutability Class (%)", fontsize=13, fontweight="bold")
        axes[0].set_xlabel("Language Runtime", fontsize=11)
        axes[0].set_ylabel("Share of State Members (%)", fontsize=11)
        axes[0].tick_params(axis="x", rotation=0)
        axes[0].legend(title="Mutability", frameon=True)
        axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    # Panel B: Return-Type Annotation Completeness & Async/Generator Density
    if not df_callables.empty:
        type_summary = (
            df_callables.groupby("language", as_index=False)
            .agg(
                total=("has_return_type", "count"),
                typed=("has_return_type", "sum"),
                async_count=("is_async", "sum"),
                gen_count=("is_generator", "sum"),
            )
        )
        type_summary["Return Type Coverage (%)"] = (
            100.0 * type_summary["typed"] / type_summary["total"]
        )
        sns.barplot(
            data=type_summary,
            x="language",
            y="Return Type Coverage (%)",
            hue="language",
            palette=LANG_PALETTE,
            legend=False,
            ax=axes[1],
        )
        axes[1].set_ylim(0, 105)
        axes[1].set_title(
            "B. Callable Return-Type Annotation Completeness (%)",
            fontsize=13,
            fontweight="bold",
        )
        axes[1].set_xlabel("Language Runtime", fontsize=11)
        axes[1].set_ylabel("Callables with Explicit Return Type (%)", fontsize=11)
        axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(out_dir / "04_mutability_and_typing.png", bbox_inches="tight")
    plt.close(fig)


def plot_layer2_facets(
    df_rec: pd.DataFrame, df_proto: pd.DataFrame, out_dir: Path
) -> None:
    """Figure 5: Layer 2 Receiver/Container Semantics & Protocol Family Alignment."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=160)

    # Panel A: Top Layer 2 Receiver / Memory Categories per Language
    if not df_rec.empty:
        top_rec = (
            df_rec.sort_values("count", ascending=False)
            .groupby("language")
            .head(4)
        )
        sns.barplot(
            data=top_rec,
            y="semantic_category",
            x="count",
            hue="language",
            palette=LANG_PALETTE,
            dodge=False,
            ax=axes[0],
        )
        axes[0].set_xscale("log")
        axes[0].set_title(
            "A. Layer 2 Facet Semantics (Receivers, Structs & Descriptors)",
            fontsize=13,
            fontweight="bold",
        )
        axes[0].set_xlabel("Entity Count (log10)", fontsize=11)
        axes[0].set_ylabel("Layer 2 Semantic Category", fontsize=11)
        axes[0].legend(title="Language", frameon=True)
        axes[0].grid(axis="x", linestyle="--", alpha=0.4)

    # Panel B: Protocol Alignment Across Python Dunders, C# Contracts & Rust Traits
    if not df_proto.empty:
        sns.barplot(
            data=df_proto,
            x="protocol_family",
            y="count",
            hue="language",
            palette=LANG_PALETTE,
            ax=axes[1],
        )
        axes[1].set_yscale("log")
        axes[1].set_title(
            "B. Protocol Alignment: Python Dunders vs. C# & Rust Contracts",
            fontsize=13,
            fontweight="bold",
        )
        axes[1].set_xlabel("Universal Protocol Family", fontsize=11)
        axes[1].set_ylabel("Implementing Symbols / Containers (log10)", fontsize=11)
        axes[1].legend(title="Language", frameon=True)
        axes[1].grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    fig.savefig(out_dir / "05_layer2_facets_and_protocols.png", bbox_inches="tight")
    plt.close(fig)


# ============================================================================
# 4. MAIN CLI & ORCHESTRATOR
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run UTSS Cross-Language Data Science & Bridge Synthesis Analysis."
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=Path("."),
        help="Root directory or dbs/ folder containing UTSS SQLite databases.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("analysis_output"),
        help="Directory to write generated PNG charts and CSV datasets.",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    print("==> 1. Discovering UTSS SQLite catalogs...")
    dbs = discover_databases(args.db_dir)
    if not dbs:
        raise SystemExit(
            f"No UTSS SQLite databases found in {args.db_dir.resolve()}. "
            "Pass --db-dir pointing to your dbs/ or UTSS root directory."
        )

    for lang, path in dbs.items():
        print(f"    - [{lang.upper():10s}] -> {path}")

    print("==> 2. Extracting Layer 1 Universal Core metrics across catalogs...")
    df_strata, df_depth = extract_strata_and_topology(dbs)
    df_params = extract_parameter_passing(dbs)
    df_callables = extract_callable_signatures(dbs)
    df_state = extract_state_mutability(dbs)

    print("==> 3. Extracting Layer 2 Language-Fidelity Facets & Rosetta Crosswalk...")
    df_rec, df_proto = extract_layer2_facets(dbs)
    df_rosetta = extract_rosetta_crosswalk(dbs)

    print("==> 4. Generating Matplotlib/Seaborn comparative charts...")
    plot_strata_and_depth(df_strata, df_depth, args.out_dir)
    plot_parameter_passing_spectrum(df_params, args.out_dir)
    plot_arity_defaults_overloads(df_callables, args.out_dir)
    plot_mutability_and_typing(df_state, df_callables, args.out_dir)
    plot_layer2_facets(df_rec, df_proto, args.out_dir)

    print("==> 5. Exporting empirical CSV tables for Phase 4 normalization...")
    df_strata.to_csv(args.out_dir / "strata_summary.csv", index=False)
    df_params.to_csv(args.out_dir / "parameter_passing_matrix.csv", index=False)
    df_rosetta.to_csv(args.out_dir / "rosetta_sequence_map_crosswalk.csv", index=False)

    # Print executive summary table to terminal
    if not df_callables.empty:
        exec_summary = (
            df_callables.groupby("language", as_index=False)
            .agg(
                total_callables=("arity", "count"),
                avg_arity=("arity", lambda s: round(s.mean(), 2)),
                pct_optional_defaults=("optional_params", lambda s: round(100.0 * (s > 0).mean(), 1)),
                pct_overloaded=("has_overloads", lambda s: round(100.0 * (s == 1).mean(), 1)),
                pct_generic=("is_generic", lambda s: round(100.0 * (s == 1).mean(), 1)),
                pct_async=("is_async", lambda s: round(100.0 * (s == 1).mean(), 1)),
            )
        )
        exec_summary.to_csv(args.out_dir / "callable_executive_summary.csv", index=False)
        print("\n=== UTSS CROSS-LANGUAGE CALLABLE IMPEDANCE SUMMARY ===")
        print(exec_summary.to_string(index=False))

    print(f"\n==> Complete! Charts and CSVs saved to: {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()

```

---

## 3. Running the Suite & Integrating with the React Workbench

1. **Install Data Science Dependencies (via `uv`)**:
```bash
uv add pandas matplotlib seaborn

```


2. **Run the Script Against Your Catalogs**:
* If running inside the **UTSS Analysis Workbench** repository (`dbs/*.db`):





```bash
uv run python utss_comparative_analysis.py --db-dir ./dbs --out-dir ./analysis_output

```

* If running inside the **UTSS Harvester** root (`catalog_base_full.db`, `Z_CS/`, `Z_Rust/`, `Z_TS/`, `Z_C/`, `Z_Go/`):



```bash
uv run python utss_comparative_analysis.py --db-dir . --out-dir ./analysis_output

```

3. **Wire Directly into the FastAPI Comparative Analytics Tab**:
The extractor functions (`extract_strata_and_topology`, `extract_parameter_passing`, `extract_callable_signatures`, `extract_rosetta_crosswalk`) return standard `pandas.DataFrame` objects that serialize directly via `df.to_dict(orient="records")` in a FastAPI route (`/api/comparative/metrics`) to populate your React **Comparative Analytics** tab.



Would you like to build the **FastAPI `/api/comparative/*` backend endpoints and React Comparative Analytics view** to render these charts and SQL lessons interactively in the Workbench, or start designing the **Phase 4 `universal_type_mappings` schema** from the Rosetta Crosswalk output?















Building both the **FastAPI + React Comparative Analytics Workbench** and the **Phase 4 Universal Bridge Schema** connects your 6 language catalogs directly to an interactive research environment and a queryable transpiler lookup engine.

---

## 1. Backend: Federated 6-DB Engine & FastAPI Routes (`server/analysis/comparative_engine.py`)

In the existing Workbench, queries execute against one `.db` file at a time. To power the **Comparative Analytics** tab and the 12 multi-language curriculum lessons, this module creates a read-only federated SQLite coordinator that attaches all 6 language databases simultaneously (`py`, `cs`, `rs`, `ts`, `cpp`, `go`), creates unified cross-language SQL views (`v_all_containers`, `v_all_symbols`, `v_all_callables`, `v_all_parameters`), serves pre-aggregated `pandas` metrics as JSON, and renders on-demand `matplotlib` charts.

```python
# server/analysis/comparative_engine.py
from __future__ import annotations

import io
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Headless rendering for FastAPI endpoints
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/comparative", tags=["Comparative Analytics"])

# Canonical alias mapping for ATTACH DATABASE
LANG_ALIASES: Dict[str, str] = {
    "python": "py",
    "csharp": "cs",
    "rust": "rs",
    "typescript": "ts",
    "cpp": "cpp",
    "go": "go",
}

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|REPLACE)\b",
    re.IGNORECASE,
)


class FederatedQueryRequest(BaseModel):
    sql: str
    limit: int = 500


def strip_sql_literals_and_comments(sql: str) -> str:
    """Strips string literals and comments before checking for forbidden DDL/DML keywords."""
    sql_no_comments = re.sub(r"/\*.*?\*/|--[^\r\n]*", " ", sql, flags=re.DOTALL)
    return re.sub(r"'([^']|'')*'|\"([^\"]|\"\")*\"", "''", sql_no_comments)


def validate_readonly_sql(sql: str) -> None:
    cleaned = strip_sql_literals_and_comments(sql).strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")
    first_token = cleaned.split()[0].upper()
    if first_token not in {"SELECT", "WITH", "EXPLAIN"}:
        raise HTTPException(
            status_code=400,
            detail=f"Only SELECT, WITH, and EXPLAIN queries are permitted (got {first_token}).",
        )
    match = FORBIDDEN_SQL_PATTERN.search(cleaned)
    if match:
        raise HTTPException(
            status_code=400,
            detail=f"Disallowed SQL keyword detected: {match.group(0).upper()}",
        )


class FederatedCatalogEngine:
    """Manages a federated connection across all 6 UTSS SQLite databases."""

    def __init__(self, dbs_dir: Path = Path("dbs")) -> None:
        self.dbs_dir = dbs_dir

    def resolve_language_dbs(self) -> Dict[str, Path]:
        """Discovers the primary SQLite database for each of the 6 languages."""
        resolved: Dict[str, Path] = {}
        if not self.dbs_dir.exists():
            return resolved

        for db_path in sorted(self.dbs_dir.glob("*.db")):
            try:
                uri = f"file:{db_path.resolve()}?mode=ro&immutable=1"
                with sqlite3.connect(uri, uri=True) as conn:
                    row = conn.execute(
                        "SELECT LOWER(language) FROM environments LIMIT 1;"
                    ).fetchone()
                    if row and row[0] in LANG_ALIASES:
                        lang = row[0]
                        if lang not in resolved or "full" in db_path.name:
                            resolved[lang] = db_path.resolve()
            except sqlite3.Error:
                continue
        return resolved

    def create_federated_connection(self) -> tuple[sqlite3.Connection, Dict[str, str]]:
        """
        Creates an in-memory coordinator DB, attaches all discovered language DBs
        in read-only immutable mode, and registers cross-language convenience views.
        """
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        resolved = self.resolve_language_dbs()
        attached_aliases: Dict[str, str] = {}

        for lang, db_path in resolved.items():
            alias = LANG_ALIASES[lang]
            uri = f"file:{db_path}?mode=ro&immutable=1"
            conn.execute(f"ATTACH DATABASE '{uri}' AS {alias};")
            attached_aliases[lang] = alias

        if attached_aliases:
            self._register_unified_views(conn, attached_aliases)

        # Enforce 5.0-second timeout via SQLite progress handler
        start_time = time.monotonic()

        def _timeout_handler() -> int:
            return 1 if (time.monotonic() - start_time) > 5.0 else 0

        conn.set_progress_handler(_timeout_handler, 10000)
        return conn, attached_aliases

    @staticmethod
    def _register_unified_views(
        conn: sqlite3.Connection, aliases: Dict[str, str]
    ) -> None:
        """Creates v_all_containers, v_all_symbols, v_all_callables, and v_all_parameters views."""
        containers_union = " UNION ALL ".join(
            f"""
            SELECT '{lang}' AS language, d.stratum, d.dist_name,
                   c.container_id, c.parent_container_id, c.container_kind,
                   c.qualified_name, c.short_name, c.requires_import, c.visibility, c.is_hidden
            FROM {alias}.containers c
            JOIN {alias}.distributions d ON c.dist_id = d.dist_id
            """
            for lang, alias in aliases.items()
        )
        conn.execute(f"CREATE TEMP VIEW v_all_containers AS {containers_union};")

        symbols_union = " UNION ALL ".join(
            f"""
            SELECT '{lang}' AS language, d.stratum, c.container_kind,
                   c.qualified_name AS container_qname,
                   s.symbol_id, s.container_id, s.name, s.qualified_name,
                   s.symbol_kind, s.visibility, s.provenance, s.is_hidden
            FROM {alias}.symbols s
            JOIN {alias}.containers c ON s.container_id = c.container_id
            JOIN {alias}.distributions d ON c.dist_id = d.dist_id
            """
            for lang, alias in aliases.items()
        )
        conn.execute(f"CREATE TEMP VIEW v_all_symbols AS {symbols_union};")

        callables_union = " UNION ALL ".join(
            f"""
            SELECT '{lang}' AS language, d.stratum, s.symbol_id, s.name,
                   s.qualified_name, s.symbol_kind, s.is_hidden,
                   cal.is_async, cal.is_generator, cal.is_static, cal.is_class_bound,
                   cal.has_overloads, cal.overload_count, cal.type_params_json,
                   cal.return_type_expr, cal.raw_signature, cal.signature_source
            FROM {alias}.callables cal
            JOIN {alias}.symbols s ON cal.symbol_id = s.symbol_id
            JOIN {alias}.containers c ON s.container_id = c.container_id
            JOIN {alias}.distributions d ON c.dist_id = d.dist_id
            """
            for lang, alias in aliases.items()
        )
        conn.execute(f"CREATE TEMP VIEW v_all_callables AS {callables_union};")

        params_union = " UNION ALL ".join(
            f"""
            SELECT '{lang}' AS language, p.param_id, p.callable_symbol_id,
                   p.overload_id, p.ordinal, p.name, p.pass_kind,
                   p.type_expr, p.default_expr, p.is_optional
            FROM {alias}.parameters p
            """
            for lang, alias in aliases.items()
        )
        conn.execute(f"CREATE TEMP VIEW v_all_parameters AS {params_union};")


engine = FederatedCatalogEngine(Path("dbs"))


@router.post("/query")
def run_federated_query(req: FederatedQueryRequest) -> Dict[str, Any]:
    """Executes a read-only SQL query across all 6 attached UTSS databases."""
    validate_readonly_sql(req.sql)
    t0 = time.perf_counter()
    conn, aliases = engine.create_federated_connection()
    try:
        cursor = conn.execute(req.sql)
        columns = [col[0] for col in (cursor.description or [])]
        raw_rows = cursor.fetchmany(req.limit + 1)
        has_more = len(raw_rows) > req.limit
        rows = [dict(r) for r in raw_rows[: req.limit]]
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "has_more": has_more,
            "duration_ms": duration_ms,
            "attached_databases": aliases,
        }
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        conn.close()


@router.get("/dashboard")
def get_comparative_dashboard() -> Dict[str, Any]:
    """Returns pre-aggregated Pandas analytics across all 6 languages for the React UI."""
    conn, aliases = engine.create_federated_connection()
    try:
        # 1. Strata & Symbol Inventory
        df_strata = pd.read_sql_query(
            """
            SELECT language, stratum,
                   COUNT(DISTINCT container_id) AS containers,
                   COUNT(symbol_id) AS symbols
            FROM v_all_symbols
            WHERE is_hidden = 0
            GROUP BY language, stratum
            ORDER BY language, stratum;
            """,
            conn,
        )

        # 2. Parameter Passing & Ownership Breakdown
        df_params = pd.read_sql_query(
            """
            SELECT language, pass_kind, COUNT(*) AS param_count
            FROM v_all_parameters
            GROUP BY language, pass_kind
            ORDER BY language, param_count DESC;
            """,
            conn,
        )

        # 3. Callable Signature Impedance (Arity, Defaults, Overloads, Generics, Async)
        df_impedance = pd.read_sql_query(
            """
            WITH arity_cte AS (
                SELECT c.language, c.symbol_id, c.has_overloads, c.is_async, c.is_generator,
                       CASE WHEN c.type_params_json IS NOT NULL AND c.type_params_json NOT IN ('', '[]') THEN 1 ELSE 0 END AS is_generic,
                       COUNT(p.param_id) AS arity,
                       SUM(CASE WHEN p.is_optional = 1 OR p.default_expr IS NOT NULL THEN 1 ELSE 0 END) AS opt_params
                FROM v_all_callables c
                LEFT JOIN v_all_parameters p
                  ON p.language = c.language AND p.callable_symbol_id = c.symbol_id AND p.overload_id IS NULL
                WHERE c.is_hidden = 0
                GROUP BY c.language, c.symbol_id
            )
            SELECT language,
                   COUNT(*) AS total_callables,
                   ROUND(AVG(arity), 2) AS avg_arity,
                   ROUND(100.0 * SUM(CASE WHEN opt_params > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_with_defaults,
                   ROUND(100.0 * SUM(has_overloads) / COUNT(*), 1) AS pct_overloaded,
                   ROUND(100.0 * SUM(is_generic) / COUNT(*), 1) AS pct_generic,
                   ROUND(100.0 * SUM(is_async) / COUNT(*), 1) AS pct_async
            FROM arity_cte
            GROUP BY language
            ORDER BY total_callables DESC;
            """,
            conn,
        )

        # 4. Rosetta Crosswalk (Dynamic Sequence & Hash Map Operations)
        df_rosetta = pd.read_sql_query(
            """
            SELECT language, container_qname, name AS operation, symbol_kind
            FROM v_all_symbols
            WHERE container_qname IN (
                'builtins.list', 'list',
                'System.Collections.Generic.List',
                'alloc::vec::Vec', 'std::vec::Vec',
                'std::vector', 'Array', 'slices',
                'builtins.dict', 'dict',
                'System.Collections.Generic.Dictionary',
                'std::collections::hash_map::HashMap',
                'std::map', 'Map', 'maps'
            )
              AND is_hidden = 0
              AND name IN (
                  'append', 'Add', 'push', 'push_back', 'insert', 'Insert', 'set',
                  '__len__', 'Count', 'len', 'size', 'length',
                  'pop', 'Remove', 'RemoveAt', 'pop_back', 'clear', 'Clear', 'Delete'
              )
            ORDER BY container_qname, operation;
            """,
            conn,
        )

        return {
            "attached_databases": aliases,
            "strata_summary": df_strata.to_dict(orient="records"),
            "parameter_passing": df_params.to_dict(orient="records"),
            "signature_impedance": df_impedance.to_dict(orient="records"),
            "rosetta_crosswalk": df_rosetta.to_dict(orient="records"),
        }
    finally:
        conn.close()


@router.get("/chart/{chart_kind}")
def render_comparative_chart(
    chart_kind: str,
    theme: str = Query("dark", pattern="^(dark|light)$"),
) -> StreamingResponse:
    """Streams a live Matplotlib/Seaborn PNG chart for the Comparative Analytics UI."""
    dashboard = get_comparative_dashboard()
    bg_color = "#0F172A" if theme == "dark" else "#FFFFFF"
    text_color = "#E2E8F0" if theme == "dark" else "#1E293B"

    plt.rcParams.update({
        "figure.facecolor": bg_color,
        "axes.facecolor": bg_color,
        "axes.edgecolor": text_color,
        "axes.labelcolor": text_color,
        "xtick.color": text_color,
        "ytick.color": text_color,
        "text.color": text_color,
    })

    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=140)

    if chart_kind == "impedance":
        df = pd.DataFrame(dashboard["signature_impedance"])
        if not df.empty:
            melted = df.melt(
                id_vars="language",
                value_vars=["pct_with_defaults", "pct_overloaded", "pct_generic"],
                var_name="Metric",
                value_name="Percentage",
            )
            sns.barplot(data=melted, x="language", y="Percentage", hue="Metric", ax=ax)
            ax.set_title("Signature Impedance: Defaults, Overloads & Generics (%)")
            ax.set_ylabel("% of Public Callables")
    elif chart_kind == "pass_kind":
        df = pd.DataFrame(dashboard["parameter_passing"])
        if not df.empty:
            piv = df.pivot_table(
                index="language", columns="pass_kind", values="param_count", fill_value=0
            )
            pct = piv.div(piv.sum(axis=1), axis=0) * 100.0
            pct.plot(kind="barh", stacked=True, ax=ax, colormap="tab20")
            ax.set_title("Parameter Passing & Ownership Spectrum (%)")
            ax.set_xlabel("Share of Parameters (%)")
            ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown chart_kind: {chart_kind}")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=bg_color)
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

```

---

## 2. Frontend: React Comparative Analytics Tab (`React_UI/src/components/ComparativeWorkbench.tsx`)

This React component plugs into your `TopNav` when the user switches from **Tutoring & Internals** to **Comparative Analytics**. It renders:

1. **Cross-Language Impedance Matrix**: Live comparison of callable arity, optional default arguments, `@overload` prevalence, and generic percentages across all 6 catalogs.
2. **Embedded Matplotlib/Seaborn Visuals**: Loads `/api/comparative/chart/impedance` and `/api/comparative/chart/pass_kind` synchronized with the active dark/light theme.


3. **Federated Multi-DB SQL Runner**: Executes cross-database queries against `/api/comparative/query` with all 6 aliases (`py`, `cs`, `rs`, `ts`, `cpp`, `go`) and `v_all_*` views pre-attached.

```tsx
// React_UI/src/components/ComparativeWorkbench.tsx
import React, { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

interface ImpedanceRow {
  language: string;
  total_callables: number;
  avg_arity: number;
  pct_with_defaults: number;
  pct_overloaded: number;
  pct_generic: number;
  pct_async: number;
}

interface DashboardPayload {
  attached_databases: Record<string, string>;
  signature_impedance: ImpedanceRow[];
  rosetta_crosswalk: Array<{
    language: string;
    container_qname: string;
    operation: string;
    symbol_kind: string;
  }>;
}

const DEFAULT_FEDERATED_SQL = `/* Federated Query across all 6 attached DBs (v_all_callables & v_all_parameters) */
SELECT
    language,
    symbol_kind,
    COUNT(*) AS total_callables,
    SUM(has_overloads) AS overloaded_callables,
    SUM(is_async) AS async_callables,
    SUM(is_generator) AS generator_callables
FROM v_all_callables
WHERE is_hidden = 0 AND stratum IN (0, 1)
GROUP BY language, symbol_kind
ORDER BY language ASC, total_callables DESC;`;

export const ComparativeWorkbench: React.FC<{ isLightTheme?: boolean }> = ({
  isLightTheme = false,
}) => {
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [sql, setSql] = useState<string>(DEFAULT_FEDERATED_SQL);
  const [queryResult, setQueryResult] = useState<{
    columns: string[];
    rows: Record<string, unknown>[];
    duration_ms: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/comparative/dashboard")
      .then((res) => res.json())
      .then((data: DashboardPayload) => setDashboard(data))
      .catch((err) => setError(String(err)));
  }, []);

  const runFederatedSql = async () => {
    setError(null);
    try {
      const res = await fetch("/api/comparative/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql, limit: 500 }),
      });
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || "Query failed");
      }
      setQueryResult(await res.json());
    } catch (err: any) {
      setError(err.message);
    }
  };

  const chartTheme = isLightTheme ? "light" : "dark";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "16px", color: "var(--text-main)" }}>
      {/* 1. Attached Federation Status Banner */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        background: "var(--bg-card)", padding: "12px 16px", borderRadius: "8px",
        border: "1px solid var(--border-color)"
      }}>
        <div>
          <strong>Federated Cross-Language Engine Active</strong>
          <span style={{ marginLeft: "12px", fontSize: "0.85rem", opacity: 0.8 }}>
            Views: <code>v_all_containers</code>, <code>v_all_symbols</code>, <code>v_all_callables</code>, <code>v_all_parameters</code>
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {dashboard && Object.entries(dashboard.attached_databases).map(([lang, alias]) => (
            <span key={lang} style={{
              padding: "4px 8px", borderRadius: "4px", fontSize: "0.75rem",
              background: "var(--bg-surface)", border: "1px solid var(--accent-primary)"
            }}>
              {lang.toUpperCase()} (<code>{alias}.*</code>)
            </span>
          ))}
        </div>
      </div>

      {/* 2. Top Row: Empirical Matplotlib Charts + Signature Impedance Table */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <div style={{ background: "var(--bg-card)", padding: "12px", borderRadius: "8px" }}>
          <img
            src={`/api/comparative/chart/impedance?theme=${chartTheme}`}
            alt="Signature Impedance Chart"
            style={{ width: "100%", height: "auto", borderRadius: "6px" }}
          />
        </div>
        <div style={{ background: "var(--bg-card)", padding: "12px", borderRadius: "8px" }}>
          <img
            src={`/api/comparative/chart/pass_kind?theme=${chartTheme}`}
            alt="Parameter Passing Spectrum Chart"
            style={{ width: "100%", height: "auto", borderRadius: "6px" }}
          />
        </div>
      </div>

      {/* 3. Signature Impedance Matrix Table */}
      {dashboard && (
        <div style={{ background: "var(--bg-card)", padding: "14px", borderRadius: "8px", overflowX: "auto" }}>
          <h4 style={{ margin: "0 0 10px 0" }}>Cross-Language Callable Impedance Summary (Pandas Aggregation)</h4>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-color)", textAlign: "left" }}>
                <th>LANGUAGE</th>
                <th>PUBLIC CALLABLES</th>
                <th>AVG ARITY</th>
                <th>% OPTIONAL DEFAULTS</th>
                <th>% OVERLOADED</th>
                <th>% GENERIC</th>
                <th>% ASYNC</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.signature_impedance.map((row) => (
                <tr key={row.language} style={{ borderBottom: "1px solid rgba(148,163,184,0.15)" }}>
                  <td style={{ fontWeight: 600, textTransform: "uppercase" }}>{row.language}</td>
                  <td>{row.total_callables.toLocaleString()}</td>
                  <td>{row.avg_arity}</td>
                  <td>{row.pct_with_defaults}%</td>
                  <td>{row.pct_overloaded}%</td>
                  <td>{row.pct_generic}%</td>
                  <td>{row.pct_async}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. Federated Multi-Database SQL Runner */}
      <div style={{ background: "var(--bg-card)", padding: "14px", borderRadius: "8px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <strong>Federated 6-Language SQL Runner (Read-Only)</strong>
          <button
            onClick={runFederatedSql}
            style={{
              background: "var(--accent-primary)", color: "#fff", border: "none",
              padding: "6px 14px", borderRadius: "6px", cursor: "pointer", fontWeight: 600
            }}
          >
            ▶ Run Federated Query
          </button>
        </div>
        <div style={{ height: "260px", border: "1px solid var(--border-color)", borderRadius: "6px", overflow: "hidden" }}>
          <Editor
            height="100%"
            defaultLanguage="sql"
            theme={isLightTheme ? "vs" : "vs-dark"}
            value={sql}
            onChange={(val) => setSql(val || "")}
            options={{ minimap: { enabled: false }, fontSize: 13, automaticLayout: true }}
          />
        </div>
        {error && (
          <div style={{ marginTop: "10px", color: "#EF4444", fontSize: "0.85rem" }}>
            SQL Error: {error}
          </div>
        )}
        {queryResult && (
          <div style={{ marginTop: "12px", maxHeight: "320px", overflow: "auto" }}>
            <div style={{ fontSize: "0.8rem", marginBottom: "6px", opacity: 0.8 }}>
              Rows: {queryResult.rows.length} | Duration: {queryResult.duration_ms} ms
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
              <thead>
                <tr style={{ position: "sticky", top: 0, background: "var(--bg-surface)", textAlign: "left" }}>
                  {queryResult.columns.map((col) => (
                    <th key={col} style={{ padding: "6px 8px" }}>{col.toUpperCase()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {queryResult.rows.map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
                    {queryResult.columns.map((col) => (
                      <td key={col} style={{ padding: "6px 8px" }}>
                        {r[col] === null ? <em style={{ opacity: 0.5 }}>NULL</em> : String(r[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

```

---

## 3. Phase 4 Foundation: The Universal Bridge Schema (`schemas/universal_bridge.sql`)

Once your comparative SQL queries and `pandas` scripts identify the exact equivalents across the 6 standard libraries, **Phase 4 (Cross-Language Type & Protocol Normalization)** stores those mappings in a 4-table relational bridge schema (`schemas/universal_bridge.sql`).

Instead of hardcoding Python-to-C# or Python-to-Rust translation rules inside compiler code, any transpiler backend (`psc`, Rust emitter, Go emitter) queries these four tables to resolve types, method lowering templates, and dunder-to-trait contracts:

```sql
-- ============================================================================
-- UTSS PHASE 4: UNIVERSAL TYPE, OPERATION & PROTOCOL BRIDGE SCHEMA
-- Database Target: dbs/utss_universal_bridge.db
-- ============================================================================
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Table 1: universal_concepts
-- Language-agnostic compiler IR primitives, generic containers, and protocols.
-- ----------------------------------------------------------------------------
CREATE TABLE universal_concepts (
    concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_key TEXT NOT NULL UNIQUE,       -- e.g. 'prim.int64', 'prim.bigint', 'prim.utf8_str',
                                            -- 'col.sequence', 'col.map', 'col.set',
                                            -- 'ctrl.optional', 'ctrl.result',
                                            -- 'proto.disposable', 'proto.iterable', 'proto.indexable'
    category TEXT NOT NULL,                 -- 'primitive', 'collection', 'control_flow', 'protocol', 'io'
    type_arity INTEGER NOT NULL DEFAULT 0,  -- 0 = concrete, 1 = generic <T>, 2 = generic <K, V>
    description TEXT NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 2: universal_type_mappings
-- Maps a universal concept to its exact representation in each of the 6 languages.
-- ----------------------------------------------------------------------------
CREATE TABLE universal_type_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,                 -- 'python', 'csharp', 'rust', 'typescript', 'cpp', 'go'
    target_qualified_name TEXT NOT NULL,    -- e.g. 'System.Collections.Generic.List', 'alloc::vec::Vec'
    type_syntax_template TEXT NOT NULL,     -- e.g. 'List<{T0}>', 'Vec<{T0}>', 'std::vector<{T0}>', '[]{T0}'
    required_import TEXT,                   -- NULL if Stratum 0 ambient, else e.g. 'System.Collections.Generic', '<vector>'
    memory_model TEXT NOT NULL,             -- 'value_stack', 'ref_gc', 'owned_heap', 'rc_box'
    nullability_model TEXT NOT NULL,        -- 'nullable_ref', 'option_wrapper', 'value_default', 'pointer_nil'
    notes TEXT,
    UNIQUE(concept_id, language)
);

-- ----------------------------------------------------------------------------
-- Table 3: universal_operation_mappings
-- Rosetta Crosswalk for method/function calls on universal concepts.
-- ----------------------------------------------------------------------------
CREATE TABLE universal_operation_mappings (
    op_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    canonical_op TEXT NOT NULL,             -- e.g. 'append', 'length', 'get_or_default', 'contains_key', 'clear'
    language TEXT NOT NULL,                 -- 'python', 'csharp', 'rust', 'typescript', 'cpp', 'go'
    target_symbol_name TEXT NOT NULL,       -- e.g. 'append', 'Add', 'push', 'push_back', 'len'
    call_syntax_template TEXT NOT NULL,     -- e.g. '{self}.Add({arg0})', '{self}.push({arg0})', '{self} = append({self}, {arg0})'
    receiver_pass_kind TEXT NOT NULL,       -- 'val', 'ref', 'mut_ref', 'pointer', 'free_fn'
    mutates_receiver INTEGER NOT NULL DEFAULT 0,
    returns_new_value INTEGER NOT NULL DEFAULT 0,
    UNIQUE(concept_id, canonical_op, language)
);

-- ----------------------------------------------------------------------------
-- Table 4: universal_protocol_mappings
-- Maps Python duck-typed dunders to nominal Interfaces (C#), Traits (Rust),
-- Implicit Interfaces (Go), Concepts/Operators (C++), and Symbols (TS).
-- ----------------------------------------------------------------------------
CREATE TABLE universal_protocol_mappings (
    proto_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    contract_kind TEXT NOT NULL,            -- 'dunder_method', 'interface', 'trait', 'implicit_interface', 'operator', 'symbol_protocol'
    contract_qualified_name TEXT NOT NULL,  -- e.g. '__enter__/__exit__', 'System.IDisposable', 'core::ops::Drop', 'io.Closer'
    required_methods_json TEXT NOT NULL,    -- e.g. '["Dispose"]', '["drop(&mut self)"]', '["Close() error"]'
    lowering_strategy TEXT NOT NULL,        -- 'using_statement', 'raii_drop_scope', 'defer_close', 'foreach_loop'
    UNIQUE(concept_id, language)
);

-- ============================================================================
-- SEED DATA: CANONICAL ROSETTA CROSSWALK EXAMPLES
-- ============================================================================
INSERT INTO universal_concepts (concept_id, concept_key, category, type_arity, description) VALUES
    (1, 'prim.bigint',      'primitive',  0, 'Arbitrary-precision integer (Python default int)'),
    (2, 'prim.int64',       'primitive',  0, 'Fixed 64-bit signed integer (fast-path lowered int)'),
    (3, 'col.sequence',     'collection', 1, 'Dynamically-sized contiguous growable array <T>'),
    (4, 'col.map',          'collection', 2, 'Hash/dictionary key-value mapping <K, V>'),
    (5, 'proto.disposable', 'protocol',   0, 'Deterministic resource cleanup / context manager'),
    (6, 'proto.iterable',   'protocol',   1, 'Sequential element iteration protocol <T>');

-- Seed: col.sequence (Dynamic Array <T>) across all 6 languages
INSERT INTO universal_type_mappings
    (concept_id, language, target_qualified_name, type_syntax_template, required_import, memory_model, nullability_model)
VALUES
    (3, 'python',     'builtins.list',                   'list[{T0}]',       NULL,                         'ref_gc',     'nullable_ref'),
    (3, 'csharp',     'System.Collections.Generic.List', 'List<{T0}>',       'System.Collections.Generic', 'ref_gc',     'nullable_ref'),
    (3, 'rust',       'alloc::vec::Vec',                 'Vec<{T0}>',        NULL,                         'owned_heap', 'option_wrapper'),
    (3, 'typescript', 'Array',                           'Array<{T0}>',      NULL,                         'ref_gc',     'nullable_ref'),
    (3, 'cpp',        'std::vector',                     'std::vector<{T0}>','<vector>',                   'owned_heap', 'value_default'),
    (3, 'go',         'slices',                          '[]{T0}',           'slices',                     'value_stack','pointer_nil');

-- Seed: col.sequence canonical operations ('append' & 'length')
INSERT INTO universal_operation_mappings
    (concept_id, canonical_op, language, target_symbol_name, call_syntax_template, receiver_pass_kind, mutates_receiver, returns_new_value)
VALUES
    (3, 'append', 'python',     'append',    '{self}.append({arg0})',            'ref',     1, 0),
    (3, 'append', 'csharp',     'Add',       '{self}.Add({arg0})',               'ref',     1, 0),
    (3, 'append', 'rust',       'push',      '{self}.push({arg0})',              'mut_ref', 1, 0),
    (3, 'append', 'typescript', 'push',      '{self}.push({arg0})',              'ref',     1, 0),
    (3, 'append', 'cpp',        'push_back', '{self}.push_back({arg0})',         'mut_ref', 1, 0),
    (3, 'append', 'go',         'append',    '{self} = append({self}, {arg0})',  'free_fn', 0, 1),
    (3, 'length', 'python',     'len',       'len({self})',                      'free_fn', 0, 1),
    (3, 'length', 'csharp',     'Count',     '{self}.Count',                     'ref',     0, 1),
    (3, 'length', 'rust',       'len',       '{self}.len()',                     'ref',     0, 1),
    (3, 'length', 'typescript', 'length',    '{self}.length',                    'ref',     0, 1),
    (3, 'length', 'cpp',        'size',      '{self}.size()',                    'ref',     0, 1),
    (3, 'length', 'go',         'len',       'len({self})',                      'free_fn', 0, 1);

-- Seed: proto.disposable (Context Manager / Resource Cleanup) across all 6 languages
INSERT INTO universal_protocol_mappings
    (concept_id, language, contract_kind, contract_qualified_name, required_methods_json, lowering_strategy)
VALUES
    (5, 'python',     'dunder_method',      'contextlib.AbstractContextManager', '["__enter__", "__exit__"]', 'with_statement'),
    (5, 'csharp',     'interface',          'System.IDisposable',                '["void Dispose()"]',        'using_statement'),
    (5, 'rust',       'trait',              'core::ops::Drop',                   '["fn drop(&mut self)"]',    'raii_drop_scope'),
    (5, 'typescript', 'symbol_protocol',    'Disposable',                        '["[Symbol.dispose]()"]',    'using_declaration'),
    (5, 'cpp',        'operator',           '~Destructor',                       '["~T() noexcept"]',         'raii_drop_scope'),
    (5, 'go',         'implicit_interface', 'io.Closer',                         '["Close() error"]',         'defer_close');

```

---

## 4. Integration Checklist

1. **Register the Comparative Router**: In your FastAPI entrypoint (`server/main.py` or `server/app.py`), mount `app.include_router(comparative_engine.router)`.
2. **Save the 12 Comparative SQL Lessons**: Place the 12 YAML-headed `.sql` files (`comp_01_ambient_baseline.sql` through `comp_12_rosetta_crosswalk.sql`) inside `queries/comparative/` so `server/query_loader.py` indexes them automatically.


3. **Wire the TopNav Tab**: In `React_UI/src/App.tsx`, render `<ComparativeWorkbench 'vscode-light'} isLightTheme="{theme"/>` when the active tab is `"comparative"`.



Would you like to build an **automated populator script (`build_bridge_db.py`)** next that scans your 6 `.db` catalogs to auto-populate `utss_universal_bridge.db` for all standard library collections, primitives, exceptions, and I/O types?