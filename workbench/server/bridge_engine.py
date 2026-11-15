"""
UTSS Universal Bridge Engine
Coordinates cross-language symbol analysis and type unification across the 6 harvesters.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class BridgeEngine:
    """Manages connections to language-specific SQLite catalogs and bridge mappings."""

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            # Default to repo root relative to workbench/server
            self.root = Path(__file__).resolve().parent.parent.parent
        else:
            self.root = Path(workspace_root)

        self.catalog_paths = {
            "python": self.root / "harvesters/utss-python/catalog_base_full.db",
            "csharp": self.root / "harvesters/utss-csharp/catalog_cs_full.db",
            "rust": self.root / "harvesters/utss-rust/catalog_rust_full.db",
            "typescript": self.root / "harvesters/utss-typescript/catalog_ts_full.db",
            "cpp": self.root / "harvesters/utss-cpp/catalog_cpp_full.db",
            "go": self.root / "harvesters/utss-go/catalog_go_full.db",
        }

    def get_catalog_connection(self, language: str) -> sqlite3.Connection:
        """Returns a read-only SQLite connection to the requested language catalog."""
        if language not in self.catalog_paths:
            raise ValueError(f"Unknown language: {language}. Available: {list(self.catalog_paths.keys())}")
        
        path = self.catalog_paths[language]
        if not path.exists():
            raise FileNotFoundError(f"Catalog for {language} not found at {path}")

        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def inspect_spectrum(self, language: str) -> Dict[str, Any]:
        """Returns row counts and stratum distribution for a specific language catalog."""
        conn = self.get_catalog_connection(language)
        cursor = conn.cursor()
        
        counts = {}
        tables = [
            "environments", "distributions", "containers", "symbols", 
            "callables", "callable_overloads", "parameters", "state_members", 
            "symbol_aliases"
        ]
        for tbl in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                counts[tbl] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[tbl] = 0

        # Language-specific facet counts
        facet_table = f"{language}_container_facets" if language != "csharp" else "cs_container_facets"
        if language == "python":
            facet_table = "py_container_facets"
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {facet_table}")
            counts[facet_table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[facet_table] = 0

        conn.close()
        return {
            "language": language,
            "catalog_path": str(self.catalog_paths[language]),
            "table_counts": counts,
        }

    def find_symbols(self, query: str, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]:
        """Searches for symbols matching `query` across all available language catalogs."""
        results: Dict[str, List[Dict[str, Any]]] = {}

        for lang, path in self.catalog_paths.items():
            if not path.exists():
                results[lang] = []
                continue

            try:
                conn = self.get_catalog_connection(lang)
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT s.symbol_id, s.name, s.symbol_kind, d.stratum, c.short_name as container_name
                    FROM symbols s
                    LEFT JOIN containers c ON s.container_id = c.container_id
                    LEFT JOIN distributions d ON c.dist_id = d.dist_id
                    WHERE s.name LIKE ?
                    LIMIT ?
                    """,
                    (f"%{query}%", limit),
                )
                results[lang] = [dict(row) for row in cur.fetchall()]
                conn.close()
            except Exception as e:
                results[lang] = [{"error": str(e)}]

        return results
