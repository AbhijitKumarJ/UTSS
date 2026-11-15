import json
import re
import sqlite3
import time
from pathlib import Path
from server.config import Config

class DatabaseManager:
    """Manages multi-database catalog discovery, introspection, and safe read-only SQL execution."""

    FEDERATED_VARIANTS = {
        "recommended": {
            "py": "python_recommended.db",
            "cs": "cs_recommended.db",
            "cpp": "cpp_recommended.db",
            "go": "go_recommended.db",
            "rust": "rust_recommended.db",
            "ts": "ts_recommended.db",
        },
        "full": {
            "py": "python_base_full.db",
            "cs": "cs_base_full.db",
            "cpp": "cpp_full.db",
            "go": "go_full.db",
            "rust": "rust_base_full.db",
            "ts": "ts_full.db",
        },
    }

    FEDERATED_TABLES = [
        "distributions",
        "containers",
        "symbols",
        "callables",
        "parameters",
        "state_members",
        "symbol_aliases",
    ]

    def __init__(self, dbs_dir: Path | None = None):
        self.dbs_dir = dbs_dir or Config.DBS_DIR

    def _get_federated_connection(self, variant: str = "recommended") -> sqlite3.Connection:
        """Creates an in-memory SQLite connection attaching all 6 language databases and mounting v_all_* views."""
        var_key = variant if variant in self.FEDERATED_VARIANTS else "recommended"
        mapping = self.FEDERATED_VARIANTS[var_key]

        conn = sqlite3.connect(":memory:", uri=True, check_same_thread=False)
        cursor = conn.cursor()

        # Attach all 6 databases
        for alias, db_filename in mapping.items():
            db_path = (self.dbs_dir / db_filename).resolve()
            if not db_path.exists():
                continue
            cursor.execute(f"ATTACH DATABASE 'file:{db_path}?mode=ro' AS {alias};")

        # Create master v_all_environments view
        cursor.execute(
            """
            CREATE TEMP VIEW v_all_environments AS
            SELECT * FROM py.environments
            UNION ALL
            SELECT * FROM cs.environments
            UNION ALL
            SELECT * FROM cpp.environments
            UNION ALL
            SELECT * FROM go.environments
            UNION ALL
            SELECT * FROM rust.environments
            UNION ALL
            SELECT * FROM ts.environments;
            """
        )

        # Create master v_all_* views for the other 7 tables
        for table in self.FEDERATED_TABLES:
            cursor.execute(
                f"""
                CREATE TEMP VIEW v_all_{table} AS
                SELECT 'python' AS language, * FROM py.{table}
                UNION ALL
                SELECT 'csharp' AS language, * FROM cs.{table}
                UNION ALL
                SELECT 'cpp' AS language, * FROM cpp.{table}
                UNION ALL
                SELECT 'go' AS language, * FROM go.{table}
                UNION ALL
                SELECT 'rust' AS language, * FROM rust.{table}
                UNION ALL
                SELECT 'typescript' AS language, * FROM ts.{table};
                """
            )

        return conn

    def discover_databases(self) -> list[dict]:
        """Scans the databases directory and introspects metadata for all discovered SQLite DBs."""
        dbs: list[dict] = []
        if not self.dbs_dir.exists():
            return dbs

        for db_path in sorted(self.dbs_dir.glob("*.db")):
            db_info = self._introspect_db(db_path)
            if db_info:
                dbs.append(db_info)

        # Calculate federated aggregate stats
        rec_symbols = 0
        rec_containers = 0
        rec_callables = 0
        full_symbols = 0
        full_containers = 0
        full_callables = 0

        for db in dbs:
            v = db.get("variant")
            if v == "recommended":
                rec_symbols += db.get("symbol_count", 0)
                rec_containers += db.get("container_count", 0)
                rec_callables += db.get("callable_count", 0)
            elif v in {"full", "base_full"}:
                full_symbols += db.get("symbol_count", 0)
                full_containers += db.get("container_count", 0)
                full_callables += db.get("callable_count", 0)

        fed_tables = ["v_all_environments"] + [f"v_all_{t}" for t in self.FEDERATED_TABLES]

        fed_rec = {
            "id": "federated_recommended",
            "filename": "federated_recommended",
            "relative_path": "federated://recommended",
            "language": "federated",
            "runtime": "Federated Multi-Language Engine",
            "version": "All (Curated)",
            "variant": "recommended",
            "symbol_count": rec_symbols,
            "container_count": rec_containers,
            "callable_count": rec_callables,
            "is_available": True,
            "tables": fed_tables,
        }

        fed_full = {
            "id": "federated_full",
            "filename": "federated_full",
            "relative_path": "federated://full",
            "language": "federated",
            "runtime": "Federated Multi-Language Engine",
            "version": "All (Standard Libraries)",
            "variant": "full",
            "symbol_count": full_symbols,
            "container_count": full_containers,
            "callable_count": full_callables,
            "is_available": True,
            "tables": fed_tables,
        }

        federated = []
        if rec_symbols > 0:
            federated.append(fed_rec)
        if full_symbols > 0:
            federated.append(fed_full)

        return federated + dbs

    def get_database(self, db_id: str) -> dict | None:
        """Retrieves metadata for a specific database ID."""
        for db in self.discover_databases():
            if db["id"] == db_id:
                return db
        return None

    def _introspect_db(self, db_path: Path) -> dict | None:
        """Introspects a single SQLite database for environment metadata and symbol counts."""
        db_id = db_path.stem
        filename = db_path.name
        rel_path = str(db_path.relative_to(Config.BASE_DIR) if db_path.is_relative_to(Config.BASE_DIR) else db_path)

        metadata = {
            "id": db_id,
            "filename": filename,
            "relative_path": rel_path,
            "language": "unknown",
            "runtime": None,
            "version": None,
            "variant": None,
            "symbol_count": 0,
            "container_count": 0,
            "callable_count": 0,
            "is_available": True,
            "tables": []
        }

        # Try to infer language & variant from filename (e.g. python_base_full -> python, base_full)
        parts = db_id.split("_", 1)
        if len(parts) == 2 and parts[0] in {"python", "csharp", "cs", "rust", "typescript", "ts", "cpp", "go", "java"}:
            metadata["language"] = "csharp" if parts[0] == "cs" else ("typescript" if parts[0] == "ts" else parts[0])
            metadata["variant"] = parts[1]

        try:
            conn = self._get_connection(db_path)
            cursor = conn.cursor()

            # Discover all user tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            metadata["tables"] = tables

            # If standard UTSS environments table exists, inspect it
            if "environments" in tables:
                cursor.execute(
                    "SELECT language, runtime_name, language_version, platform_triplet FROM environments LIMIT 1;"
                )
                row = cursor.fetchone()
                if row:
                    metadata["language"] = row[0]
                    metadata["runtime"] = row[1]
                    metadata["version"] = row[2]
                    metadata["platform"] = row[3]

            # Inspect symbol and container counts if available
            if "symbols" in tables:
                cursor.execute("SELECT count(*) FROM symbols;")
                metadata["symbol_count"] = cursor.fetchone()[0]

            if "containers" in tables:
                cursor.execute("SELECT count(*) FROM containers;")
                metadata["container_count"] = cursor.fetchone()[0]

            if "callables" in tables:
                cursor.execute("SELECT count(*) FROM callables;")
                metadata["callable_count"] = cursor.fetchone()[0]

            conn.close()
            return metadata
        except Exception as e:
            metadata["is_available"] = False
            metadata["error"] = str(e)
            return metadata

    def _get_connection(self, db_path: Path) -> sqlite3.Connection:
        """Opens a safe read-only SQLite connection using URI mode."""
        uri = f"file:{db_path.resolve()}?mode=ro&immutable=1"
        try:
            return sqlite3.connect(uri, uri=True, check_same_thread=False)
        except sqlite3.OperationalError:
            # Fallback without immutable=1 if filesystem restricts it
            uri_ro = f"file:{db_path.resolve()}?mode=ro"
            return sqlite3.connect(uri_ro, uri=True, check_same_thread=False)

    def _validate_sql_safety(self, sql: str) -> None:
        """Validates that the SQL statement is read-only and permitted."""
        # Strip block comments /* ... */
        cleaned = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        # Strip line comments -- ...
        cleaned = re.sub(r"--[^\n]*", "", cleaned)
        cleaned = cleaned.strip()

        if not cleaned:
            raise ValueError("Query string is empty.")

        first_word_match = re.match(r"^\s*([A-Za-z]+)", cleaned)
        if not first_word_match:
            raise ValueError("Invalid SQL format.")

        first_word = first_word_match.group(1).upper()
        allowed_statements = {"SELECT", "WITH", "EXPLAIN"}
        if first_word not in allowed_statements:
            raise ValueError(f"Disallowed statement type '{first_word}'. Only SELECT, WITH, and EXPLAIN are permitted.")

        # Disallow explicit dangerous tokens in SQL body (outside of string literals)
        # Strip string literals ('...' with escaped quotes '') before checking keywords
        code_without_strings = re.sub(r"'(?:''|[^'])*'", "''", cleaned)
        disallowed_keywords = {"ATTACH", "DETACH", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}
        tokens = set(re.findall(r"\b[A-Za-z]+\b", code_without_strings.upper()))
        forbidden = tokens.intersection(disallowed_keywords)
        if forbidden:
            raise ValueError(f"Disallowed statement or keyword detected: {', '.join(sorted(forbidden))}")

    def execute_query(
        self,
        db_id: str,
        sql: str,
        limit: int | None = None,
        timeout_seconds: float | None = None
    ) -> dict:
        """Executes a user SQL query against the specified database within safety limits."""
        limit = limit or Config.DEFAULT_PREVIEW_LIMIT
        timeout = timeout_seconds or Config.QUERY_TIMEOUT_SECONDS

        is_federated = db_id.startswith("federated_") or ("v_all_" in sql.lower())
        target_path = None

        if not is_federated:
            target_path = self.dbs_dir / f"{db_id}.db"
            if not target_path.exists():
                # Check if db_id already has extension or matches full filename
                direct_path = self.dbs_dir / db_id
                if direct_path.exists():
                    target_path = direct_path
                else:
                    return {"error": f"Database '{db_id}' not found.", "db_id": db_id}

        try:
            self._validate_sql_safety(sql)
        except ValueError as val_err:
            return {"error": str(val_err), "db_id": db_id}

        conn = None
        try:
            if is_federated:
                variant = "recommended" if "recommended" in db_id else "full"
                conn = self._get_federated_connection(variant)
                # In federated connection, views reside in sqlite_temp_schema
                if re.search(r"\bsqlite_schema\b", sql, re.IGNORECASE):
                    sql = re.sub(r"\bsqlite_schema\b", "sqlite_temp_schema", sql, flags=re.IGNORECASE)
                elif re.search(r"\bsqlite_master\b", sql, re.IGNORECASE):
                    sql = re.sub(r"\bsqlite_master\b", "sqlite_temp_master", sql, flags=re.IGNORECASE)
            else:
                conn = self._get_connection(target_path)

            # Enforce execution timeout using sqlite progress handler
            start_time = time.perf_counter()
            def timeout_handler():
                if time.perf_counter() - start_time > timeout:
                    return 1  # non-zero return interrupts the query
                return 0

            # Check every 1000 VM instructions
            conn.set_progress_handler(timeout_handler, 1000)

            cursor = conn.cursor()
            cursor.execute(sql)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            # Single-pass fetch limit + 1 to detect truncation
            rows = cursor.fetchmany(limit + 1)
            has_more = len(rows) > limit
            trimmed_rows = rows[:limit]

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Convert row values to JSON-serializable types if necessary
            clean_rows = []
            for r in trimmed_rows:
                clean_rows.append(list(r))

            return {
                "columns": columns,
                "rows": clean_rows,
                "row_count": len(clean_rows),
                "has_more": has_more,
                "truncated": has_more,
                "execution_time_ms": round(elapsed_ms, 2),
                "db_id": db_id
            }
        except sqlite3.OperationalError as op_err:
            msg = str(op_err)
            if "interrupted" in msg.lower():
                return {"error": f"Query execution timed out (timeout limit: {timeout} seconds).", "db_id": db_id}
            return {"error": msg, "db_id": db_id}
        except Exception as e:
            return {"error": str(e), "db_id": db_id}
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_database_path(self, db_id: str) -> Path | None:
        """Returns the Path to a database file by id, or None if not found."""
        target_path = self.dbs_dir / f"{db_id}.db"
        if target_path.exists():
            return target_path
        direct_path = self.dbs_dir / db_id
        if direct_path.exists():
            return direct_path
        return None

    def get_container_graph(self, db_id: str) -> dict:
        """Extracts container containment hierarchy as nodes and edges."""
        is_federated = db_id.startswith("federated_")
        target_path = None
        if not is_federated:
            target_path = self.get_database_path(db_id)
            if not target_path or not target_path.exists():
                raise FileNotFoundError(f"Database '{db_id}' not found.")

        conn = None
        try:
            if is_federated:
                variant = "recommended" if "recommended" in db_id else "full"
                conn = self._get_federated_connection(variant)
                tbl_containers = "v_all_containers"
                tbl_symbols = "v_all_symbols"
            else:
                conn = self._get_connection(target_path)
                tbl_containers = "containers"
                tbl_symbols = "symbols"

            cursor = conn.cursor()
            
            # Query containers with symbol counts
            query = f"""
                SELECT c.container_id, c.parent_container_id, c.qualified_name, c.short_name,
                       c.container_kind, c.visibility, d.stratum, COALESCE(s.sym_count, 0) as symbol_count
                FROM {tbl_containers} c
                LEFT JOIN distributions d ON c.dist_id = d.dist_id
                LEFT JOIN (
                    SELECT container_id, COUNT(*) as sym_count
                    FROM {tbl_symbols}
                    GROUP BY container_id
                ) s ON c.container_id = s.container_id
                ORDER BY c.container_id ASC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            nodes = []
            edges = []
            node_ids = set()
            
            for r in rows:
                c_id, parent_id, qname, sname, kind, vis, stratum, sym_count = r
                node_id = f"c_{c_id}"
                node_ids.add(node_id)
                nodes.append({
                    "id": node_id,
                    "container_id": c_id,
                    "parent_id": f"c_{parent_id}" if parent_id else None,
                    "name": sname or qname.split(".")[-1],
                    "qualified_name": qname,
                    "kind": kind or "container",
                    "visibility": vis or "public",
                    "stratum": stratum if stratum is not None else 1,
                    "symbol_count": sym_count
                })

            for n in nodes:
                p_id = n["parent_id"]
                if p_id and p_id in node_ids:
                    edges.append({
                        "id": f"e_{p_id}_{n['id']}",
                        "source": p_id,
                        "target": n["id"],
                        "relation_kind": "contains"
                    })

            return {
                "db_id": db_id,
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_inheritance_graph(self, db_id: str) -> dict:
        """Extracts type inheritance and interface implementation DAG."""
        target_path = self.get_database_path(db_id)
        if not target_path or not target_path.exists():
            raise FileNotFoundError(f"Database '{db_id}' not found.")

        conn = None
        try:
            conn = self._get_connection(target_path)
            cursor = conn.cursor()

            # Determine language directly from environments table
            cursor.execute("SELECT language FROM environments LIMIT 1")
            env_row = cursor.fetchone()
            lang = env_row[0] if env_row else "unknown"

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%container_facets%'")
            facet_tables = [r[0] for r in cursor.fetchall()]

            nodes_dict = {}
            edges = []

            cursor.execute("""
                SELECT c.container_id, c.qualified_name, c.short_name, c.container_kind, c.visibility, d.stratum
                FROM containers c
                LEFT JOIN distributions d ON c.dist_id = d.dist_id
                WHERE c.container_kind IN ('class', 'struct', 'interface', 'trait', 'record', 'exception_class')
            """)
            for r in cursor.fetchall():
                c_id, qname, sname, kind, vis, stratum = r
                nodes_dict[qname] = {
                    "id": f"type_{c_id}",
                    "container_id": c_id,
                    "name": sname or qname.split(".")[-1],
                    "qualified_name": qname,
                    "kind": kind,
                    "visibility": vis,
                    "stratum": stratum if stratum is not None else 1,
                    "is_external": False
                }

            def get_or_create_node(qname: str, kind="class") -> str:
                clean_qname = qname.strip()
                if clean_qname in nodes_dict:
                    return nodes_dict[clean_qname]["id"]
                ext_id = f"ext_{len(nodes_dict) + 1}"
                sname = clean_qname.split(".")[-1].split("::")[-1]
                nodes_dict[clean_qname] = {
                    "id": ext_id,
                    "container_id": None,
                    "name": sname,
                    "qualified_name": clean_qname,
                    "kind": kind,
                    "visibility": "public",
                    "stratum": 0,
                    "is_external": True
                }
                return ext_id

            if "py_container_facets" in facet_tables:
                cursor.execute("""
                    SELECT c.qualified_name, f.base_classes_json
                    FROM containers c
                    JOIN py_container_facets f ON c.container_id = f.container_id
                    WHERE f.base_classes_json IS NOT NULL
                """)
                for qname, bases_json in cursor.fetchall():
                    if not bases_json:
                        continue
                    try:
                        bases = json.loads(bases_json)
                        for b in bases:
                            if b and b != "builtins.object":
                                src_id = nodes_dict[qname]["id"]
                                tgt_id = get_or_create_node(b, "class")
                                edges.append({
                                    "id": f"e_{src_id}_{tgt_id}",
                                    "source": src_id,
                                    "target": tgt_id,
                                    "relation_kind": "extends"
                                })
                    except Exception:
                        pass

            elif "cs_container_facets" in facet_tables:
                cursor.execute("""
                    SELECT c.qualified_name, f.base_type_qname, f.implemented_interfaces_json
                    FROM containers c
                    JOIN cs_container_facets f ON c.container_id = f.container_id
                """)
                for qname, base_qname, ifaces_json in cursor.fetchall():
                    if base_qname and base_qname not in ("object", "System.Object", "System.ValueType"):
                        src_id = nodes_dict[qname]["id"]
                        tgt_id = get_or_create_node(base_qname, "class")
                        edges.append({
                            "id": f"e_{src_id}_{tgt_id}",
                            "source": src_id,
                            "target": tgt_id,
                            "relation_kind": "extends"
                        })
                    if ifaces_json:
                        try:
                            ifaces = json.loads(ifaces_json)
                            for iface in ifaces:
                                if iface:
                                    src_id = nodes_dict[qname]["id"]
                                    tgt_id = get_or_create_node(iface, "interface")
                                    edges.append({
                                        "id": f"e_{src_id}_{tgt_id}",
                                        "source": src_id,
                                        "target": tgt_id,
                                        "relation_kind": "implements"
                                    })
                        except Exception:
                            pass

            elif "ts_container_facets" in facet_tables:
                cursor.execute("""
                    SELECT c.qualified_name, f.heritage_clauses_json
                    FROM containers c
                    JOIN ts_container_facets f ON c.container_id = f.container_id
                    WHERE f.heritage_clauses_json IS NOT NULL
                """)
                for qname, clauses_json in cursor.fetchall():
                    try:
                        clauses = json.loads(clauses_json)
                        for clause in clauses:
                            parts = clause.strip().split()
                            if len(parts) >= 2:
                                rel = parts[0]
                                target_name = parts[1]
                                src_id = nodes_dict[qname]["id"]
                                tgt_id = get_or_create_node(target_name, "interface" if rel == "implements" else "class")
                                edges.append({
                                    "id": f"e_{src_id}_{tgt_id}",
                                    "source": src_id,
                                    "target": tgt_id,
                                    "relation_kind": rel
                                })
                    except Exception:
                        pass

            elif "cpp_container_facets" in facet_tables:
                cursor.execute("""
                    SELECT c.qualified_name, f.base_classes_json
                    FROM containers c
                    JOIN cpp_container_facets f ON c.container_id = f.container_id
                    WHERE f.base_classes_json IS NOT NULL
                """)
                for qname, bases_json in cursor.fetchall():
                    try:
                        bases = json.loads(bases_json)
                        for b in bases:
                            parts = b.strip().split()
                            target_name = parts[-1]
                            src_id = nodes_dict[qname]["id"]
                            tgt_id = get_or_create_node(target_name, "class")
                            edges.append({
                                "id": f"e_{src_id}_{tgt_id}",
                                "source": src_id,
                                "target": tgt_id,
                                "relation_kind": "extends"
                            })
                    except Exception:
                        pass

            connected_node_ids = {e["source"] for e in edges} | {e["target"] for e in edges}
            if edges:
                active_nodes = [n for n in nodes_dict.values() if n["id"] in connected_node_ids]
            else:
                active_nodes = list(nodes_dict.values())[:30]

            return {
                "db_id": db_id,
                "language": lang,
                "nodes": active_nodes,
                "edges": edges,
                "total_nodes": len(active_nodes),
                "total_edges": len(edges)
            }
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_concept_cluster(self, concept_key: str) -> dict:
        """Extracts a star graph linking a universal concept to its 6-language implementations."""
        bridge_path = Path(self.dbs_dir) / "utss_universal_bridge.db"
        if not bridge_path.exists():
            raise FileNotFoundError("Universal Bridge database not found.")

        conn = None
        try:
            conn = self._get_connection(bridge_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT concept_id, concept_key, category, type_arity, description
                FROM universal_concepts
                WHERE concept_key = ?
            """, (concept_key,))
            concept_row = cursor.fetchone()
            if not concept_row:
                raise ValueError(f"Concept '{concept_key}' not found.")

            c_id, c_key, cat, arity, desc = concept_row

            root_node = {
                "id": f"concept_{c_id}",
                "name": c_key.split(".")[-1],
                "qualified_name": c_key,
                "kind": "concept",
                "category": cat,
                "description": desc,
                "is_root": True
            }

            nodes = [root_node]
            edges = []

            cursor.execute("""
                SELECT language, target_qualified_name, type_syntax_template,
                       memory_model, nullability_model, verification_status
                FROM universal_type_mappings
                WHERE concept_id = ?
            """, (c_id,))

            for lang, target_qname, syntax, mem_model, null_model, status in cursor.fetchall():
                node_id = f"target_{lang}_{c_id}"
                nodes.append({
                    "id": node_id,
                    "language": lang,
                    "name": target_qname,
                    "qualified_name": f"{lang}::{target_qname}",
                    "kind": "target_type",
                    "syntax_template": syntax,
                    "memory_model": mem_model,
                    "nullability_model": null_model,
                    "verification_status": status
                })
                edges.append({
                    "id": f"e_concept_{node_id}",
                    "source": root_node["id"],
                    "target": node_id,
                    "relation_kind": "lowers_to",
                    "label": mem_model
                })

            return {
                "concept": c_key,
                "category": cat,
                "description": desc,
                "nodes": nodes,
                "edges": edges,
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            }
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
