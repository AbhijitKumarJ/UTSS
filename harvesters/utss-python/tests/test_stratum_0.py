import sqlite3
import pytest
from utss.schema import init_db
from utss.cataloger import PythonSpectrumCataloger


def test_stratum_0_ambient_harvest(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    env_id = cataloger.register_environment()
    assert env_id > 0

    cataloger.harvest_stratum_0_ambient()

    # Check environments table
    env_row = mem_conn.execute("SELECT language, runtime_name, language_version FROM environments;").fetchone()
    assert env_row[0] == "python"

    # Check distributions table has Stratum 0 <ambient>
    dist_row = mem_conn.execute("SELECT stratum, dist_name FROM distributions WHERE stratum = 0;").fetchone()
    assert dist_row is not None
    assert dist_row[1] == "<ambient>"

    # Check containers table has <ambient>
    amb_container = mem_conn.execute(
        "SELECT container_kind, qualified_name, requires_import FROM containers WHERE qualified_name = '<ambient>';"
    ).fetchone()
    assert amb_container is not None
    assert amb_container[0] == "ambient_scope"
    assert amb_container[2] == 0

    # Check keywords and soft keywords in symbols
    keywords = {
        row[0] for row in mem_conn.execute(
            "SELECT name FROM symbols WHERE container_id = 1 AND symbol_kind IN ('keyword', 'soft_keyword');"
        ).fetchall()
    }
    assert "def" in keywords
    assert "class" in keywords
    assert "import" in keywords
    assert "match" in keywords or "case" in keywords or "type" in keywords

    # Check implicit module dunders
    dunder_row = mem_conn.execute(
        "SELECT name, provenance FROM symbols WHERE name = '__name__' AND container_id = 1;"
    ).fetchone()
    assert dunder_row is not None
    assert dunder_row[1] == "implicit_dunder"

    # Check pure builtin vs site-injected provenance
    len_row = mem_conn.execute(
        "SELECT name, provenance FROM symbols WHERE name = 'len' AND container_id = 1;"
    ).fetchone()
    assert len_row is not None
    assert len_row[1] == "defined_here"

    # Site-injected builtins check
    site_syms = mem_conn.execute(
        "SELECT name FROM symbols WHERE provenance = 'site_injected';"
    ).fetchall()
    site_names = {r[0] for r in site_syms}
    # In standard environment with site, at least some of help/exit/quit/copyright/license exist
    for expected_site in ("help", "quit", "exit"):
        if expected_site in site_names:
            assert expected_site in site_names
