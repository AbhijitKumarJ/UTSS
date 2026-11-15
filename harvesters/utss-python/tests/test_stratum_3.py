import sqlite3
from pathlib import Path
import pytest
from utss.schema import init_db
from utss.cataloger import PythonSpectrumCataloger
from utss.workspace import WorkspaceASTHarvester


def test_stratum_3_workspace_ast_harvest(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    # Create dummy project in tmp_path
    pkg_dir = tmp_path / "sample_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('"""Sample package."""\n__all__ = ["Calculator"]\n')
    calc_file = pkg_dir / "calc.py"
    calc_file.write_text(
        '"""Calculation module."""\n'
        'import math\n'
        'from os import path\n'
        '\n'
        'DEFAULT_OFFSET: int = 42\n'
        '\n'
        'class Calculator:\n'
        '    """Calculator class."""\n'
        '    def __init__(self, start: int = 0) -> None:\n'
        '        self.start = start\n'
        '\n'
        '    def compute(self, x: int, y: int = 10) -> int:\n'
        '        return x + y\n'
        '\n'
        'def helper_func(msg: str) -> str:\n'
        '    """Helper function."""\n'
        '    return msg.upper()\n'
    )

    # File with potential runtime side effect that would fail if executed
    side_effect_file = tmp_path / "side_effect.py"
    side_effect_file.write_text(
        'if True:\n'
        '    pass\n'
        '# This line would crash if executed:\n'
        '# raise RuntimeError("Executed!")\n'
        'CRASH_VAR = 999\n'
    )

    # Harvest Stratum 3
    cataloger.harvest_stratum_3_workspace(workspace_dir=tmp_path)

    # 1. Distribution
    dist = mem_conn.execute(
        "SELECT dist_id, dist_name, stratum FROM distributions WHERE stratum = 3;"
    ).fetchone()
    assert dist is not None
    assert dist[1] == "<workspace>"

    # 2. Containers
    containers = {
        row[0]: row[1]
        for row in mem_conn.execute("SELECT qualified_name, container_kind FROM containers WHERE dist_id = ?;", (dist[0],)).fetchall()
    }
    assert "sample_pkg" in containers
    assert containers["sample_pkg"] == "package"
    assert "sample_pkg.calc" in containers
    assert containers["sample_pkg.calc"] == "module"
    assert "sample_pkg.calc.Calculator" in containers
    assert containers["sample_pkg.calc.Calculator"] == "class"

    # 3. Symbols
    calc_symbols = {
        row[0]: (row[1], row[2])
        for row in mem_conn.execute(
            """
            SELECT s.name, s.symbol_kind, s.visibility
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            WHERE c.qualified_name = 'sample_pkg.calc';
            """
        ).fetchall()
    }
    assert "DEFAULT_OFFSET" in calc_symbols
    assert calc_symbols["DEFAULT_OFFSET"][0] == "constant"
    assert "Calculator" in calc_symbols
    assert calc_symbols["Calculator"][0] == "class"
    assert "helper_func" in calc_symbols
    assert calc_symbols["helper_func"][0] == "function"

    # 4. Callable & Parameters
    helper_row = mem_conn.execute(
        """
        SELECT c.return_type_expr, p.name, p.type_expr
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        JOIN parameters p ON p.callable_symbol_id = c.symbol_id
        WHERE s.name = 'helper_func';
        """
    ).fetchone()
    assert helper_row is not None
    assert helper_row[0] == "str"
    assert helper_row[1] == "msg"
    assert helper_row[2] == "str"

    # 5. Symbol Aliases (import math, from os import path)
    aliases = mem_conn.execute(
        """
        SELECT a.exposed_name, a.target_module_name, a.alias_kind
        FROM symbol_aliases a
        JOIN containers c ON a.source_container_id = c.container_id
        WHERE c.qualified_name = 'sample_pkg.calc';
        """
    ).fetchall()
    alias_dict = {a[0]: (a[1], a[2]) for a in aliases}
    assert "math" in alias_dict
    assert alias_dict["math"][0] == "math"
    assert alias_dict["math"][1] in ("imported_module_ref", "workspace_import")
    assert "path" in alias_dict
    assert alias_dict["path"][0] == "os"
    assert alias_dict["path"][1] in ("imported_symbol_ref", "workspace_import")
