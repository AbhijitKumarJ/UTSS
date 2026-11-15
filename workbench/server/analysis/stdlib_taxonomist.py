#!/usr/bin/env python3
"""
UTSS Phase 4: Autonomous Stdlib Taxonomist & Unmapped Ecosystem Explorer
========================================================================
Performs deep structural harvesting across all 6 language databases (Python,
C#, C++, Go, Rust, TypeScript). Classifies standard library containers into
taxonomy domains, identifies mapped concepts vs. unmapped long-tail candidates,
evaluates cross-language impedance risk, and updates `discovered_stdlib_taxonomy`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from server.config import Config

DB_FILES = {
    "python": "python_recommended.db",
    "csharp": "cs_recommended.db",
    "cpp": "cpp_recommended.db",
    "go": "go_recommended.db",
    "rust": "rust_recommended.db",
    "typescript": "ts_recommended.db",
}

COLLECTION_KEYWORDS = {
    "vector", "list", "array", "queue", "stack", "map", "dict", "set",
    "table", "bag", "ring", "deque", "heap", "buffer", "linkedlist",
    "btree", "span", "memory", "sequence"
}

CONCURRENCY_KEYWORDS = {
    "concurrent", "atomic", "sync", "lock", "mutex", "channel",
    "semaphore", "barrier", "thread", "task", "future", "promise",
    "cancelfunc", "context", "waitgroup", "rwlock", "condvar"
}

STREAM_IO_KEYWORDS = {
    "stream", "reader", "writer", "file", "socket", "pipe",
    "scanner", "formatter", "binary", "text", "io", "path", "dir"
}

EXCEPTION_KEYWORDS = {
    "error", "exception", "fault", "panic", "failure", "warning"
}


def _classify_domain(name: str, kind: str) -> str:
    n_lower = name.lower()
    if any(k in n_lower for k in EXCEPTION_KEYWORDS):
        return "exception"
    if any(k in n_lower for k in CONCURRENCY_KEYWORDS):
        return "concurrency"
    if any(k in n_lower for k in COLLECTION_KEYWORDS):
        return "collection"
    if any(k in n_lower for k in STREAM_IO_KEYWORDS):
        return "stream_io"
    if kind in ("interface", "trait") or n_lower.endswith("able") or n_lower.endswith("er"):
        return "protocol_interface"
    return "collection"


def _assess_impedance(domain: str, short_name: str, lang: str) -> Tuple[str, str, str]:
    """
    Returns (impedance_risk, proposed_concept, impedance_notes)
    """
    if domain == "concurrency":
        return (
            "HIGH",
            f"concurrency.{short_name.lower()}",
            "Requires thread synchronization or async scheduling runtime; high impedance when lowering to single-threaded event loop models."
        )
    elif domain == "stream_io":
        return (
            "MEDIUM",
            f"io.{short_name.lower()}",
            "Requires deterministic resource deallocation (RAII / using / with statements) and OS file descriptor cleanup."
        )
    elif domain == "protocol_interface":
        return (
            "MEDIUM",
            f"protocol.{short_name.lower()}",
            "Nominal vs. structural interface compliance semantics vary significantly across nominal OOP (C#/C++) and structural/duck-typing (Go/TypeScript/Python)."
        )
    elif domain == "exception":
        return (
            "LOW",
            f"exception.{short_name.lower()}",
            "Standard exception or error value unwinding; maps cleanly to result types or try-catch hierarchies."
        )
    else:
        return (
            "LOW",
            f"collection.{short_name.lower()}",
            "Algorithmic data structure with high cross-target parity; may require generics boxing or memory layout normalization."
        )


def harvest_stdlib_taxonomy() -> Dict[str, Any]:
    bridge_path = Config.DBS_DIR / "utss_universal_bridge.db"
    bridge_conn = sqlite3.connect(bridge_path)
    bridge_cur = bridge_conn.cursor()

    # Get already mapped qualified names and short names from universal_type_mappings
    mapped_symbols: Dict[str, Set[str]] = {lang: set() for lang in DB_FILES}
    try:
        rows = bridge_cur.execute("""
            SELECT language, target_qualified_name, resolved_qualified_name
            FROM universal_type_mappings
        """).fetchall()
        for lang, t_qname, r_qname in rows:
            if lang in mapped_symbols:
                if t_qname:
                    mapped_symbols[lang].add(t_qname.lower())
                    mapped_symbols[lang].add(t_qname.split(".")[-1].split("::")[-1].lower())
                if r_qname:
                    mapped_symbols[lang].add(r_qname.lower())
                    mapped_symbols[lang].add(r_qname.split(".")[-1].split("::")[-1].lower())
    except Exception:
        pass

    results_per_lang: Dict[str, Dict[str, Any]] = {}
    all_unmapped: List[Dict[str, Any]] = []
    domain_counts: Dict[str, int] = {
        "collection": 0,
        "concurrency": 0,
        "stream_io": 0,
        "exception": 0,
        "protocol_interface": 0,
    }

    # Harvest from each language database
    for lang, db_file in DB_FILES.items():
        db_path = Config.DBS_DIR / db_file
        if not db_path.exists():
            continue

        lang_conn = sqlite3.connect(db_path)
        lang_cur = lang_conn.cursor()

        # Query all class/interface/trait/struct containers
        query = """
            SELECT container_id, qualified_name, short_name, container_kind
            FROM containers
            WHERE container_kind IN ('class', 'interface', 'trait', 'struct')
            AND qualified_name NOT LIKE '<ambient>.__%'
            ORDER BY qualified_name ASC
        """
        containers = lang_cur.execute(query).fetchall()

        total_lang_containers = len(containers)
        mapped_count = 0
        unmapped_candidates: List[Dict[str, Any]] = []

        for cid, qname, sname, kind in containers:
            # Check if mapped
            is_mapped = (
                sname.lower() in mapped_symbols[lang] or
                qname.lower() in mapped_symbols[lang]
            )

            domain = _classify_domain(sname, kind)
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Count public methods in this container
            try:
                method_count = lang_cur.execute("""
                    SELECT COUNT(*) FROM symbols
                    WHERE container_id = ?
                """, (cid,)).fetchone()[0]
            except Exception:
                method_count = 0

            # Insert into discovered_stdlib_taxonomy
            try:
                bridge_cur.execute("""
                    INSERT OR REPLACE INTO discovered_stdlib_taxonomy (
                        language, taxonomy_domain, stratum, entity_kind,
                        qualified_name, short_name, catalog_container_id,
                        public_method_count, layer2_metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lang,
                    domain,
                    1,
                    kind,
                    qname,
                    sname,
                    cid,
                    method_count,
                    json.dumps({"is_mapped": is_mapped, "db_source": db_file})
                ))
            except Exception:
                pass

            if is_mapped:
                mapped_count += 1
            else:
                risk, proposed, notes = _assess_impedance(domain, sname, lang)
                candidate_info = {
                    "language": lang,
                    "qualified_name": qname,
                    "short_name": sname,
                    "domain": domain,
                    "entity_kind": kind,
                    "public_methods": method_count,
                    "proposed_concept": proposed,
                    "impedance_risk": risk,
                    "impedance_notes": notes,
                }
                unmapped_candidates.append(candidate_info)
                all_unmapped.append(candidate_info)

        lang_conn.close()

        unmapped_count = len(unmapped_candidates)
        coverage_pct = round((mapped_count / total_lang_containers * 100), 1) if total_lang_containers > 0 else 0.0

        results_per_lang[lang] = {
            "total_containers": total_lang_containers,
            "mapped_count": mapped_count,
            "unmapped_count": unmapped_count,
            "coverage_pct": coverage_pct,
            "sample_unmapped": unmapped_candidates[:10],
        }

    bridge_conn.commit()
    bridge_conn.close()

    # Sort unmapped candidates by public_methods desc to show most prominent stdlib constructs first
    all_unmapped.sort(key=lambda x: x["public_methods"], reverse=True)

    return {
        "languages": results_per_lang,
        "domain_distribution": domain_counts,
        "total_unmapped_candidates": len(all_unmapped),
        "unmapped_candidates": all_unmapped,
    }


def get_stdlib_coverage_report() -> Dict[str, Any]:
    """
    Returns stdlib coverage report from `discovered_stdlib_taxonomy` or runs harvest if empty.
    """
    bridge_path = Config.DBS_DIR / "utss_universal_bridge.db"
    bridge_conn = sqlite3.connect(bridge_path)
    bridge_cur = bridge_conn.cursor()

    count = bridge_cur.execute("SELECT COUNT(*) FROM discovered_stdlib_taxonomy").fetchone()[0]
    bridge_conn.close()

    if count < 50:
        return harvest_stdlib_taxonomy()

    # Re-harvest to ensure up-to-date analysis across all 6 databases
    return harvest_stdlib_taxonomy()
