import sqlite3
import pytest
from utss.schema import init_db
from utss.cataloger import PythonSpectrumCataloger


def test_stratum_2_third_party_harvest(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    # Harvest installed third party packages (e.g., pytest, packaging, pluggy, iniconfig)
    cataloger.harvest_stratum_2_third_party(target_packages={"pytest", "iniconfig"})

    # Check distributions table
    rows = mem_conn.execute(
        "SELECT dist_name, dist_version FROM distributions WHERE stratum = 2;"
    ).fetchall()
    dist_names = {r[0] for r in rows}
    # At least pytest or iniconfig should be present in the active .venv
    assert "pytest" in dist_names or "iniconfig" in dist_names

    # Check containers table contains modules from harvested packages
    c_rows = mem_conn.execute(
        """
        SELECT c.qualified_name
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        WHERE d.stratum = 2;
        """
    ).fetchall()
    assert len(c_rows) > 0
