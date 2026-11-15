"""
Tests for Stratum 3: Deep Pure-AST Workspace Harvester.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from utss.cataloger import PythonSpectrumCataloger
from utss.schema import init_db
from utss.workspace import (
    EMBEDDED_DEMO_WORKSPACE_FILES,
    WorkspaceAstCataloger,
    discover_workspace_py_files,
)


def test_demo_workspace_fixtures_presence():
    expected_files = {
        "src/commerce_engine/__init__.py",
        "src/commerce_engine/models.py",
        "src/commerce_engine/service.py",
        "src/commerce_engine/_internal_metrics.py",
        "cli_runner.py",
    }
    assert set(EMBEDDED_DEMO_WORKSPACE_FILES.keys()) == expected_files


def test_discover_workspace_py_files(tmp_path: Path):
    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    discovered = discover_workspace_py_files(tmp_path)
    qnames = [item[0] for item in discovered]

    assert "commerce_engine" in qnames
    assert "commerce_engine.models" in qnames
    assert "commerce_engine.service" in qnames
    assert "commerce_engine._internal_metrics" in qnames
    assert "cli_runner" in qnames

    # Check that parent packages precede submodules
    assert qnames.index("commerce_engine") < qnames.index("commerce_engine.models")
    assert qnames.index("commerce_engine") < qnames.index("commerce_engine.service")


def test_harvest_workspace_init_attribute_synthesis(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    ws_cataloger = WorkspaceAstCataloger(cataloger)
    dist_id = ws_cataloger.harvest_workspace(tmp_path, project_name="commerce_workspace")
    assert dist_id > 0

    # 1. Synthesized init attributes
    rows = mem_conn.execute(
        """
        SELECT s.name, s.qualified_name, s.visibility, s.provenance, m.declared_type_expr
        FROM symbols s
        JOIN state_members m ON s.symbol_id = m.symbol_id
        WHERE s.provenance = 'ast_init_attribute';
        """
    ).fetchall()
    attr_map = {r[0]: (r[2], r[3], r[4]) for r in rows}

    assert "subtotal" in attr_map
    assert attr_map["subtotal"][2] == "float"  # Propagated from `subtotal: float = 0.0`
    assert attr_map["subtotal"][0] == "public_implicit"

    assert "__secret_token" in attr_map
    assert attr_map["__secret_token"][0] == "private_mangled"

    assert "_audit_trail" in attr_map
    assert attr_map["_audit_trail"][0] == "hidden_internal"


def test_harvest_workspace_generators_and_coroutines(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    ws_cataloger = WorkspaceAstCataloger(cataloger)
    ws_cataloger.harvest_workspace(tmp_path, project_name="commerce_workspace")

    # stream_orders should be detected as generator
    gen_row = mem_conn.execute(
        """
        SELECT c.is_async, c.is_generator, c.raw_signature
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'stream_orders';
        """
    ).fetchone()
    assert gen_row is not None
    assert gen_row[0] == 0  # not async
    assert gen_row[1] == 1  # generator

    # submit_async should be detected as coroutine
    async_row = mem_conn.execute(
        """
        SELECT c.is_async, c.is_generator
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'submit_async';
        """
    ).fetchone()
    assert async_row is not None
    assert async_row[0] == 1  # async
    assert async_row[1] == 0  # not generator

    # watch_events should be detected as async generator
    async_gen_row = mem_conn.execute(
        """
        SELECT c.is_async, c.is_generator
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'watch_events';
        """
    ).fetchone()
    assert async_gen_row is not None
    assert async_gen_row[0] == 1
    assert async_gen_row[1] == 1


def test_harvest_workspace_overloads(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    ws_cataloger = WorkspaceAstCataloger(cataloger)
    ws_cataloger.harvest_workspace(tmp_path, project_name="commerce_workspace")

    row = mem_conn.execute(
        """
        SELECT c.has_overloads, c.overload_count, c.signature_source
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'serialize';
        """
    ).fetchone()
    assert row is not None
    assert row[0] == 1  # has_overloads
    assert row[1] == 2  # 2 @overload variants
    assert row[2] == "ast_overload_source"

    # Check callable_overloads
    overloads = mem_conn.execute(
        """
        SELECT co.overload_ordinal, co.return_type_expr
        FROM callable_overloads co
        JOIN callables c ON co.callable_symbol_id = c.symbol_id
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE s.name = 'serialize'
        ORDER BY co.overload_ordinal;
        """
    ).fetchall()
    assert len(overloads) == 2
    assert overloads[0][1] == "str"
    assert overloads[1][1] == "list[str]"


def test_harvest_workspace_relative_imports(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    ws_cataloger = WorkspaceAstCataloger(cataloger)
    ws_cataloger.harvest_workspace(tmp_path, project_name="commerce_workspace")

    # In commerce_engine/__init__.py: Order is in __all__ -> explicit_all_reexport
    init_alias = mem_conn.execute(
        """
        SELECT a.exposed_name, a.target_module_name, a.target_symbol_name, a.alias_kind, a.is_in_dunder_all
        FROM symbol_aliases a
        JOIN containers c ON a.source_container_id = c.container_id
        WHERE c.qualified_name = 'commerce_engine' AND a.exposed_name = 'Order';
        """
    ).fetchone()
    assert init_alias is not None
    assert init_alias[1] == "commerce_engine.models"
    assert init_alias[2] == "Order"
    assert init_alias[3] == "explicit_all_reexport"
    assert init_alias[4] == 1

    # In commerce_engine/service.py: from .models import Order -> workspace_relative_import
    svc_alias = mem_conn.execute(
        """
        SELECT a.exposed_name, a.target_module_name, a.target_symbol_name, a.alias_kind, a.is_in_dunder_all
        FROM symbol_aliases a
        JOIN containers c ON a.source_container_id = c.container_id
        WHERE c.qualified_name = 'commerce_engine.service' AND a.exposed_name = 'Order';
        """
    ).fetchone()
    assert svc_alias is not None
    assert svc_alias[1] == "commerce_engine.models"
    assert svc_alias[3] == "workspace_relative_import"
    assert svc_alias[4] == 0


def test_harvest_workspace_ast_coordinates(mem_conn: sqlite3.Connection, tmp_path: Path):
    init_db(mem_conn, reset=True)
    cataloger = PythonSpectrumCataloger(mem_conn)
    cataloger.register_environment()

    for rel_path, content in EMBEDDED_DEMO_WORKSPACE_FILES.items():
        dest = tmp_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content.strip() + "\n", encoding="utf-8")

    ws_cataloger = WorkspaceAstCataloger(cataloger)
    ws_cataloger.harvest_workspace(tmp_path, project_name="commerce_workspace")

    # Check containers have coordinates
    c_rows = mem_conn.execute(
        "SELECT qualified_name, start_line, end_line FROM containers WHERE start_line IS NOT NULL;"
    ).fetchall()
    assert len(c_rows) > 0
    for qname, s_line, e_line in c_rows:
        assert s_line >= 1
        assert e_line >= s_line

    # Check symbols have coordinates
    s_rows = mem_conn.execute(
        "SELECT qualified_name, start_line, end_line FROM symbols WHERE start_line IS NOT NULL;"
    ).fetchall()
    assert len(s_rows) > 0
    for qname, s_line, e_line in s_rows:
        assert s_line >= 1
        assert e_line >= s_line
