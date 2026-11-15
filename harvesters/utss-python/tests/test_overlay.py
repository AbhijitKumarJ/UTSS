import ast
import sys
import pytest
from utss.overlay import (
    EMBEDDED_DEMO_STUBS,
    eval_static_guard,
    flatten_active_statements,
)


def test_embedded_demo_stubs_present():
    assert "builtins" in EMBEDDED_DEMO_STUBS
    assert "sys" in EMBEDDED_DEMO_STUBS
    assert "os" in EMBEDDED_DEMO_STUBS
    assert "json" in EMBEDDED_DEMO_STUBS
    # Builtins stub should define overloads for open and max
    assert "@overload" in EMBEDDED_DEMO_STUBS["builtins"]


def test_eval_static_guard_version_info():
    # Test on active python runtime version
    py_ver = (sys.version_info.major, sys.version_info.minor)  # (3, 13)

    test1 = ast.parse("sys.version_info >= (3, 12)", mode="eval").body
    assert eval_static_guard(test1, py_version=py_ver, sys_platform=sys.platform) is True

    test2 = ast.parse("sys.version_info < (3, 8)", mode="eval").body
    assert eval_static_guard(test2, py_version=py_ver, sys_platform=sys.platform) is False

    test3 = ast.parse("sys.version_info >= (3, 15)", mode="eval").body
    assert eval_static_guard(test3, py_version=py_ver, sys_platform=sys.platform) is False


def test_eval_static_guard_platform():
    py_ver = (3, 13)
    plat = "linux"

    test1 = ast.parse("sys.platform == 'linux'", mode="eval").body
    assert eval_static_guard(test1, py_version=py_ver, sys_platform=plat) is True

    test2 = ast.parse("sys.platform == 'win32'", mode="eval").body
    assert eval_static_guard(test2, py_version=py_ver, sys_platform=plat) is False

    test3 = ast.parse("sys.platform != 'win32'", mode="eval").body
    assert eval_static_guard(test3, py_version=py_ver, sys_platform=plat) is True


def test_eval_static_guard_compound_boolean():
    py_ver = (3, 13)
    plat = "linux"

    test_and = ast.parse("sys.version_info >= (3, 12) and sys.platform == 'linux'", mode="eval").body
    assert eval_static_guard(test_and, py_version=py_ver, sys_platform=plat) is True

    test_or = ast.parse("sys.platform == 'win32' or sys.version_info >= (3, 12)", mode="eval").body
    assert eval_static_guard(test_or, py_version=py_ver, sys_platform=plat) is True


def test_flatten_active_statements():
    code = """
x = 1
if sys.version_info >= (3, 12):
    def modern_func(): ...
else:
    def legacy_func(): ...

if sys.platform == 'win32':
    win_var: int = 100
"""
    tree = ast.parse(code)
    active = flatten_active_statements(tree.body, py_version=(3, 13), sys_platform="linux")
    names = []
    for stmt in active:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
            names.append(stmt.targets[0].id)
        elif isinstance(stmt, ast.FunctionDef):
            names.append(stmt.name)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)

    assert "x" in names
    assert "modern_func" in names
    assert "legacy_func" not in names
    assert "win_var" not in names


import sqlite3
from pathlib import Path
from utss.schema import init_db
from utss.cataloger import PythonSpectrumCataloger
from utss.overlay import StaticPyiOverlayCataloger


def test_overlay_embedded_stubs(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()
    cataloger.harvest_stratum_0_ambient()
    cataloger.harvest_stratum_1_stdlib(module_filter={"sys", "os", "json"})

    overlay_engine = StaticPyiOverlayCataloger(mem_conn)
    overlay_engine.overlay_embedded_demo_stubs()

    assert overlay_engine.enriched_callables > 0
    assert overlay_engine.inserted_overloads > 0
    assert overlay_engine.enriched_state_members > 0

    # 1. Check C-builtin len() enrichment
    len_row = mem_conn.execute(
        """
        SELECT c.signature_source, c.return_type_expr, p.name, p.type_expr, p.type_source
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        JOIN parameters p ON p.callable_symbol_id = c.symbol_id
        WHERE s.name = 'len' AND s.container_id = 1;
        """
    ).fetchone()
    assert len_row is not None
    assert len_row[0] == "pyi_stub_overlay"
    assert len_row[1] == "int"
    assert len_row[2] == "obj"
    assert len_row[3] == "Sized"
    assert len_row[4] == "pyi_stub"

    # 2. Check open() overloads
    open_call = mem_conn.execute(
        """
        SELECT c.has_overloads, c.overload_count, c.signature_source
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'open' AND s.container_id = 1;
        """
    ).fetchone()
    assert open_call is not None
    assert open_call[0] == 1
    assert open_call[1] == 2
    assert open_call[2] == "pyi_overload_overlay"

    # Check callable_overloads rows for open
    open_overloads = mem_conn.execute(
        """
        SELECT o.overload_ordinal, o.return_type_expr
        FROM callable_overloads o
        JOIN symbols s ON o.callable_symbol_id = s.symbol_id
        WHERE s.name = 'open' AND s.container_id = 1
        ORDER BY o.overload_ordinal;
        """
    ).fetchall()
    assert len(open_overloads) == 2
    assert open_overloads[0][1] == "io.TextIOWrapper"
    assert "Buffered" in open_overloads[1][1]

    # 3. Check generic variable restoration on sys.argv
    argv_row = mem_conn.execute(
        """
        SELECT m.declared_type_expr, s.provenance
        FROM state_members m
        JOIN symbols s ON m.symbol_id = s.symbol_id
        JOIN containers c ON s.container_id = c.container_id
        WHERE c.qualified_name = 'sys' AND s.name = 'argv';
        """
    ).fetchone()
    assert argv_row is not None
    assert argv_row[0] == "list[str]"
    assert argv_row[1] == "pyi_enriched"

    # 4. Check sys.version_info >= (3, 12) branch symbol (getunicodeinternedsize)
    if sys.version_info >= (3, 12):
        sym_row = mem_conn.execute(
            """
            SELECT s.name, s.provenance
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            WHERE c.qualified_name = 'sys' AND s.name = 'getunicodeinternedsize';
            """
        ).fetchone()
        assert sym_row is not None
        assert sym_row[1] in ("pyi_enriched", "pyi_stub_only")


def test_overlay_custom_typeshed_directory(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()
    cataloger.harvest_stratum_1_stdlib(module_filter={"math"})

    # Create dummy typeshed directory with math.pyi
    stdlib_dir = tmp_path / "stdlib"
    stdlib_dir.mkdir()
    math_pyi = stdlib_dir / "math.pyi"
    math_pyi.write_text(
        "from typing import overload\n"
        "@overload\n"
        "def gcd(a: int, b: int) -> int: ...\n"
        "@overload\n"
        "def gcd(*integers: int) -> int: ...\n"
    )

    overlay_engine = StaticPyiOverlayCataloger(mem_conn)
    overlay_engine.overlay_from_directory(tmp_path, module_filter={"math"})

    gcd_call = mem_conn.execute(
        """
        SELECT c.has_overloads, c.overload_count
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        JOIN containers con ON s.container_id = con.container_id
        WHERE con.qualified_name = 'math' AND s.name = 'gcd';
        """
    ).fetchone()
    assert gcd_call is not None
    assert gcd_call[0] == 1
    assert gcd_call[1] == 2
