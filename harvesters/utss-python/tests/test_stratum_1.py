import sqlite3
import pytest
from utss.schema import init_db
from utss.cataloger import PythonSpectrumCataloger


def test_discover_stdlib_modules(mem_conn: sqlite3.Connection):
    cataloger = PythonSpectrumCataloger(mem_conn)
    mods = cataloger.discover_stdlib_modules()
    assert len(mods) > 50
    assert "sys" in mods
    assert "math" in mods
    assert "json" in mods
    # Side effect modules must be excluded
    assert "antigravity" not in mods
    assert "this" not in mods


def test_stratum_1_stdlib_harvest(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    # Harvest a targeted subset of stdlib modules
    targets = {"io", "_io", "json", "sys", "math"}
    cataloger.harvest_stratum_1_stdlib(module_filter=targets)

    # Check distribution
    dist_row = mem_conn.execute(
        "SELECT stratum, dist_name FROM distributions WHERE stratum = 1 AND dist_name = 'python-stdlib';"
    ).fetchone()
    assert dist_row is not None

    # Check containers
    containers = {
        row[0]: row[1]
        for row in mem_conn.execute("SELECT qualified_name, container_kind FROM containers WHERE dist_id = 1;").fetchall()
    }
    assert "sys" in containers
    assert "io" in containers
    assert "_io" in containers
    assert "json" in containers

    # Check c_accelerator_reexport in symbol_aliases
    aliases = mem_conn.execute(
        """
        SELECT c.qualified_name, a.exposed_name, a.target_module_name, a.target_symbol_name, a.alias_kind
        FROM symbol_aliases a
        JOIN containers c ON a.source_container_id = c.container_id
        WHERE a.alias_kind = 'c_accelerator_reexport';
        """
    ).fetchall()
    assert len(aliases) > 0
    # e.g., io.BufferedReader -> _io.BufferedReader
    io_aliases = [a for a in aliases if a[0] == "io" and a[2] == "_io"]
    assert len(io_aliases) > 0


def test_stratum_1_resilient_to_python313_c_extensions(mem_conn: sqlite3.Connection):
    # Test that harvesting modules like select and _curses does not crash in Python 3.13
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()
    cataloger.harvest_stratum_1_stdlib(module_filter={"select", "_curses"})
    # Must succeed without error
    sel_container = mem_conn.execute(
        "SELECT qualified_name FROM containers WHERE qualified_name = 'select';"
    ).fetchone()
    assert sel_container is not None
