"""
Stratum 3: Deep Pure-AST Workspace Source Code Harvester.
Scans and parses local Python project directories using `ast.parse` without importing or executing user code.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from utss.introspect import (
    DUNDER_CATEGORIES,
    classify_identifier_visibility,
    compute_file_sha256,
    safe_repr,
)


WORKSPACE_IGNORED_DIRS: frozenset[str] = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
})

# Embedded multi-file workspace fixtures used when `--demo-workspace` is passed
EMBEDDED_DEMO_WORKSPACE_FILES: dict[str, str] = {
    "src/commerce_engine/__init__.py": '''
"""Top-level Commerce Engine package."""
from .models import Order, OrderStatus, CustomerId
from .service import OrderProcessor, stream_orders

__all__ = ["Order", "OrderStatus", "CustomerId", "OrderProcessor", "stream_orders"]
__version__ = "0.4.0"
''',
    "src/commerce_engine/models.py": '''
"""Domain models and type aliases for Commerce Engine."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

type CustomerId = int
DEFAULT_CURRENCY: str = "USD"
_INTERNAL_TAX_RATE = 0.0825

class OrderStatus:
    PENDING: str = "pending"
    PAID: str = "paid"
    CANCELLED: str = "cancelled"

class Order:
    """Represents a customer order with instance attributes initialized in __init__."""
    registry_count: int = 0

    def __init__(self, order_id: str, customer_id: CustomerId, subtotal: float = 0.0) -> None:
        self.order_id = order_id
        self.customer_id = customer_id
        self.subtotal = subtotal
        self.status: str = OrderStatus.PENDING
        self._audit_trail: list[str] = []
        self.__secret_token = "tok_live_99"

    @property
    def total_with_tax(self) -> float:
        return self.subtotal * (1.0 + _INTERNAL_TAX_RATE)

    @staticmethod
    def validate_id(raw_id: str) -> bool:
        return bool(raw_id and raw_id.startswith("ord_"))
''',
    "src/commerce_engine/service.py": '''
"""Order processing service with overloads, async methods, and generators."""
from __future__ import annotations
import json
import os
from typing import AsyncIterator, Iterator, overload
from .models import Order, OrderStatus, DEFAULT_CURRENCY
from . import _internal_metrics as metrics

__all__ = ["OrderProcessor", "stream_orders"]

class ProcessingError(RuntimeError):
    """Raised when an order cannot be processed."""
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code

class OrderProcessor:
    def __init__(self, region: str = "IN-WB", max_retries: int = 3) -> None:
        self.region = region
        self.max_retries = max_retries
        self.currency = DEFAULT_CURRENCY
        self._processed_ids: set[str] = set()

    @overload
    def serialize(self, order: Order, *, as_bytes: bool = False) -> str: ...
    @overload
    def serialize(self, order: list[Order], *, as_bytes: bool = False) -> list[str]: ...
    def serialize(self, order: Order | list[Order], *, as_bytes: bool = False) -> str | list[str]:
        if isinstance(order, list):
            return [json.dumps({"id": o.order_id, "status": o.status}) for o in order]
        return json.dumps({"id": order.order_id, "status": order.status})

    async def submit_async(self, order: Order) -> bool:
        metrics._increment_counter("submitted")
        order.status = OrderStatus.PAID
        self._processed_ids.add(order.order_id)
        return True

def stream_orders(batch: list[Order]) -> Iterator[Order]:
    """Generator function detected statically via ast.Yield."""
    for item in batch:
        if item.status != OrderStatus.CANCELLED:
            yield item

async def watch_events(channel: str) -> AsyncIterator[dict[str, str]]:
    """Async generator function detected statically via AsyncFunctionDef + ast.Yield."""
    yield {"channel": channel, "env": os.getenv("APP_ENV", "dev")}
''',
    "src/commerce_engine/_internal_metrics.py": '''
"""Private telemetry helper module."""
_COUNTERS: dict[str, int] = {}

def _increment_counter(name: str, delta: int = 1) -> int:
    _COUNTERS[name] = _COUNTERS.get(name, 0) + delta
    return _COUNTERS[name]
''',
    "cli_runner.py": '''
"""Top-level workspace CLI entrypoint script."""
import sys
from commerce_engine import Order, OrderProcessor

def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    proc = OrderProcessor(region="IN-KOL")
    sample = Order("ord_101", 42, subtotal=250.0)
    print(proc.serialize(sample), len(args))
    return 0

if __name__ == "__main__":
    EXIT_CODE: int = main()
    sys.exit(EXIT_CODE)
''',
}


def parse_ast_func_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    skip_implicit_first_param: bool = False,
) -> tuple[str, str | None, list[str], list[dict[str, Any]], dict[str, str]]:
    """
    Shared AST signature parser for both `.pyi` overlays and Stratum 3 `.py` files.
    Returns (raw_signature, return_type_expr, type_params, params_list, param_type_map).
    """
    args = node.args
    params: list[dict[str, Any]] = []
    param_type_map: dict[str, str] = {}
    ordinal = 0

    pos_all = list(args.posonlyargs) + list(args.args)
    num_pos_defaults = len(args.defaults)
    default_start_idx = len(pos_all) - num_pos_defaults

    for idx, arg in enumerate(pos_all):
        ann_str = ast.unparse(arg.annotation) if arg.annotation else None
        if ann_str:
            param_type_map[arg.arg] = ann_str
        if skip_implicit_first_param and idx == 0 and arg.arg in ("self", "cls"):
            continue
        pass_kind = "positional_only" if idx < len(args.posonlyargs) else "positional_or_keyword"
        def_node = args.defaults[idx - default_start_idx] if idx >= default_start_idx else None
        def_str = ast.unparse(def_node) if def_node is not None else None
        params.append({
            "ordinal": ordinal,
            "name": arg.arg,
            "pass_kind": pass_kind,
            "type_expr": ann_str,
            "default_expr": def_str,
            "is_optional": 1 if def_node is not None else 0,
        })
        ordinal += 1

    if args.vararg is not None:
        ann_str = ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
        params.append({
            "ordinal": ordinal,
            "name": args.vararg.arg,
            "pass_kind": "var_positional",
            "type_expr": ann_str,
            "default_expr": None,
            "is_optional": 1,
        })
        ordinal += 1

    for kw_arg, kw_def in zip(args.kwonlyargs, args.kw_defaults):
        ann_str = ast.unparse(kw_arg.annotation) if kw_arg.annotation else None
        if ann_str:
            param_type_map[kw_arg.arg] = ann_str
        def_str = ast.unparse(kw_def) if kw_def is not None else None
        params.append({
            "ordinal": ordinal,
            "name": kw_arg.arg,
            "pass_kind": "keyword_only",
            "type_expr": ann_str,
            "default_expr": def_str,
            "is_optional": 1 if kw_def is not None else 0,
        })
        ordinal += 1

    if args.kwarg is not None:
        ann_str = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
        params.append({
            "ordinal": ordinal,
            "name": args.kwarg.arg,
            "pass_kind": "var_keyword",
            "type_expr": ann_str,
            "default_expr": None,
            "is_optional": 1,
        })
        ordinal += 1

    ret_str = ast.unparse(node.returns) if node.returns is not None else None
    raw_sig = f"({ast.unparse(args)})" + (f" -> {ret_str}" if ret_str else "")
    type_params = [ast.unparse(tp) for tp in getattr(node, "type_params", [])]
    return (raw_sig, ret_str, type_params, params, param_type_map)


def discover_workspace_py_files(workspace_root: Path) -> list[tuple[str, bool, bool, Path]]:
    """
    Discovers all `.py` files under `workspace_root`, automatically handling `src/`
    layouts and sorting parent packages before child submodules.
    Returns list of (qualified_module_name, is_package, is_top_script, file_path).
    """
    src_layout_dir = workspace_root / "src"
    has_src_layout = src_layout_dir.is_dir()

    results: list[tuple[str, bool, bool, Path]] = []
    for py_file in sorted(workspace_root.rglob("*.py")):
        rel_parts = py_file.relative_to(workspace_root).parts
        if any(part in WORKSPACE_IGNORED_DIRS or part.endswith(".egg-info") for part in rel_parts):
            continue

        if has_src_layout and rel_parts[0] == "src" and len(rel_parts) > 1:
            mod_parts = list(rel_parts[1:])
        else:
            mod_parts = list(rel_parts)

        if mod_parts[-1] == "__init__.py":
            pkg_parts = mod_parts[:-1]
            if not pkg_parts:
                mod_qname = workspace_root.name
            else:
                mod_qname = ".".join(pkg_parts)
            results.append((mod_qname, True, False, py_file))
        else:
            stem = Path(mod_parts[-1]).stem
            dotted_parts = [*mod_parts[:-1], stem]
            mod_qname = ".".join(dotted_parts)
            is_top_script = len(dotted_parts) == 1
            results.append((mod_qname, False, is_top_script, py_file))

    results.sort(key=lambda item: (item[0].count("."), 0 if item[1] else 1, item[0]))
    return results


class WorkspaceAstCataloger:
    """
    Pure-AST harvester for Stratum 3 (Local Project / Workspace `.py` files).
    Never imports or executes user code. Extracts:
      - Packages (`__init__.py`), PEP 420 namespace packages, modules, and scripts
      - Static `__all__` export lists
      - Absolute and relative imports (`from ..pkg import sym`) into `symbol_aliases`
      - Classes, base classes, metaclasses, class attributes, and `@property` descriptors
      - Instance attributes (`self.x = ...` / `self.x: T = ...`) synthesized from `__init__`
        with automatic parameter type propagation
      - Functions, methods, `@overload` groups, static `is_generator` (`yield` / `yield from`),
        and `is_async` flags
      - Module globals, constants, `if TYPE_CHECKING:` blocks, `if __name__ == '__main__':` blocks,
        and PEP 695 `type X = ...` aliases
      - Exact 1-indexed line & 0-indexed column coordinates (`start_line`..`end_col`)
    """

    def __init__(self, cataloger: Any) -> None:
        self.cataloger = cataloger
        self.conn = cataloger.conn
        self.files_scanned: int = 0
        self.classes_found: int = 0
        self.callables_found: int = 0
        self.init_attrs_synthesized: int = 0
        self.imports_recorded: int = 0

    def harvest_workspace(
        self,
        workspace_root: Path,
        *,
        project_name: str | None = None,
        project_version: str = "0.1.0-local",
    ) -> int:
        workspace_root = workspace_root.resolve()
        dist_name = project_name or "<workspace>"
        dist_id = self.cataloger.register_distribution(
            stratum=3,
            dist_name=dist_name,
            dist_version=project_version,
            summary=f"Local workspace Python source tree at {workspace_root}",
        )

        discovered = discover_workspace_py_files(workspace_root)
        for mod_qname, is_pkg, is_script, py_path in discovered:
            self._harvest_workspace_file(
                dist_id=dist_id,
                mod_qname=mod_qname,
                is_pkg=is_pkg,
                is_script=is_script,
                py_path=py_path,
            )

        self.conn.commit()
        return dist_id

    def _harvest_workspace_file(
        self,
        *,
        dist_id: int,
        mod_qname: str,
        is_pkg: bool,
        is_script: bool,
        py_path: Path,
    ) -> None:
        try:
            source = py_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_path))
        except Exception:
            return

        self.files_scanned += 1
        dunder_all_list = self._extract_static_dunder_all(tree.body)
        dunder_all_set = set(dunder_all_list) if dunder_all_list is not None else None
        has_lazy_getattr = any(
            isinstance(s, ast.FunctionDef) and s.name == "__getattr__" for s in tree.body
        )

        parent_cid = self._ensure_parent_package_containers(dist_id, mod_qname)
        short_name = mod_qname.rsplit(".", 1)[-1]
        vis, is_hid = classify_identifier_visibility(short_name)

        mod_cid = self.cataloger.register_container(
            dist_id=dist_id,
            parent_id=parent_cid,
            container_kind="package" if is_pkg else "module",
            qualified_name=mod_qname,
            short_name=short_name,
            requires_import=0 if is_script else 1,
            visibility=vis,
            is_hidden=is_hid,
            physical_path=str(py_path),
            docstring=ast.get_docstring(tree),
            module_origin_kind="workspace_script" if is_script else "workspace_py",
            dunder_all=dunder_all_list,
            has_lazy_getattr=has_lazy_getattr,
            start_line=1,
            start_col=0,
            end_line=len(source.splitlines()) or 1,
            end_col=0,
        )

        current_pkg_parts = mod_qname.split(".") if is_pkg else mod_qname.split(".")[:-1]

        self._walk_container_statements(
            dist_id=dist_id,
            container_id=mod_cid,
            container_qname=mod_qname,
            current_pkg_parts=current_pkg_parts,
            stmts=tree.body,
            dunder_all=dunder_all_set,
            is_class_scope=False,
            provenance="ast_defined",
        )

    def _ensure_parent_package_containers(self, dist_id: int, mod_qname: str) -> int | None:
        """Ensures intermediate parent packages (including PEP 420 namespace folders) exist in `containers`."""
        if "." not in mod_qname:
            return None
        parts = mod_qname.split(".")[:-1]
        parent_cid: int | None = None
        for idx in range(1, len(parts) + 1):
            prefix_qname = ".".join(parts[:idx])
            row = self.conn.execute(
                "SELECT container_id FROM containers WHERE dist_id = ? AND qualified_name = ? LIMIT 1;",
                (dist_id, prefix_qname),
            ).fetchone()
            if row:
                parent_cid = int(row[0])
            else:
                short = parts[idx - 1]
                vis, is_hid = classify_identifier_visibility(short)
                parent_cid = self.cataloger.register_container(
                    dist_id=dist_id,
                    parent_id=parent_cid,
                    container_kind="package",
                    qualified_name=prefix_qname,
                    short_name=short,
                    requires_import=1,
                    visibility=vis,
                    is_hidden=is_hid,
                    module_origin_kind="namespace_pkg",
                )
        return parent_cid

    @staticmethod
    def _extract_static_dunder_all(stmts: list[ast.stmt]) -> list[str] | None:
        """Statically evaluates `__all__ = [...]` and `__all__ += [...]` string literals."""
        exported: list[str] | None = None
        for stmt in stmts:
            val_node: ast.expr | None = None
            if isinstance(stmt, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id == "__all__" for t in stmt.targets):
                    val_node = stmt.value
                    if exported is None:
                        exported = []
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "__all__":
                val_node = stmt.value
                if exported is None:
                    exported = []
            elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "__all__":
                val_node = stmt.value
                if exported is None:
                    exported = []

            if val_node is not None and isinstance(val_node, (ast.List, ast.Tuple, ast.Set)):
                for elt in val_node.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        if exported is not None and elt.value not in exported:
                            exported.append(elt.value)
        return exported

    def _walk_container_statements(
        self,
        *,
        dist_id: int,
        container_id: int,
        container_qname: str,
        current_pkg_parts: list[str],
        stmts: list[ast.stmt],
        dunder_all: set[str] | None,
        is_class_scope: bool,
        provenance: str,
    ) -> None:
        func_groups: dict[str, list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]]] = {}

        for stmt in stmts:
            # 1. Descend into conditional blocks (`if TYPE_CHECKING:`, `if __name__ == '__main__':`, `try/except`)
            if isinstance(stmt, ast.If):
                cond_str = ast.unparse(stmt.test).strip()
                sub_prov = provenance
                if "TYPE_CHECKING" in cond_str:
                    sub_prov = "ast_type_checking_only"
                elif "__name__" in cond_str and "__main__" in cond_str:
                    sub_prov = "ast_main_guard"
                self._walk_container_statements(
                    dist_id=dist_id,
                    container_id=container_id,
                    container_qname=container_qname,
                    current_pkg_parts=current_pkg_parts,
                    stmts=stmt.body + stmt.orelse,
                    dunder_all=dunder_all,
                    is_class_scope=is_class_scope,
                    provenance=sub_prov,
                )
                continue

            if isinstance(stmt, ast.Try):
                sub_stmts = list(stmt.body) + list(stmt.orelse) + list(stmt.finalbody)
                for handler in stmt.handlers:
                    sub_stmts.extend(handler.body)
                self._walk_container_statements(
                    dist_id=dist_id,
                    container_id=container_id,
                    container_qname=container_qname,
                    current_pkg_parts=current_pkg_parts,
                    stmts=sub_stmts,
                    dunder_all=dunder_all,
                    is_class_scope=is_class_scope,
                    provenance=provenance,
                )
                continue

            # 2. Imports (`import x` and `from ..pkg import y`)
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    exposed = alias.asname or alias.name.split(".")[0]
                    in_all = 1 if (dunder_all and exposed in dunder_all) else 0
                    self.conn.execute(
                        """
                        INSERT INTO symbol_aliases (
                            source_container_id, exposed_name, target_module_name,
                            target_symbol_name, alias_kind, is_in_dunder_all
                        )
                        VALUES (?, ?, ?, '<module>', 'workspace_import', ?)
                        ON CONFLICT(source_container_id, exposed_name) DO NOTHING;
                        """,
                        (container_id, exposed, alias.name, in_all),
                    )
                    self.imports_recorded += 1
                continue

            if isinstance(stmt, ast.ImportFrom):
                resolved_mod = self._resolve_import_from_module(current_pkg_parts, stmt.module, stmt.level)
                is_rel = stmt.level > 0
                for alias in stmt.names:
                    if alias.name == "*":
                        self.conn.execute(
                            """
                            INSERT INTO symbol_aliases (
                                source_container_id, exposed_name, target_module_name,
                                target_symbol_name, alias_kind, is_in_dunder_all
                            )
                            VALUES (?, ?, ?, '*', 'wildcard_import', 0)
                            ON CONFLICT(source_container_id, exposed_name) DO NOTHING;
                            """,
                            (container_id, f"*:{resolved_mod}", resolved_mod),
                        )
                        self.imports_recorded += 1
                        continue

                    exposed = alias.asname or alias.name
                    in_all = dunder_all is not None and exposed in dunder_all
                    akind = (
                        "explicit_all_reexport"
                        if in_all
                        else ("workspace_relative_import" if is_rel else "workspace_import")
                    )
                    self.conn.execute(
                        """
                        INSERT INTO symbol_aliases (
                            source_container_id, exposed_name, target_module_name,
                            target_symbol_name, alias_kind, is_in_dunder_all
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(source_container_id, exposed_name) DO NOTHING;
                        """,
                        (container_id, exposed, resolved_mod, alias.name, akind, 1 if in_all else 0),
                    )
                    self.imports_recorded += 1
                continue

            # 3. PEP 695 `type Alias = ...` (Python 3.12+)
            if hasattr(ast, "TypeAlias") and isinstance(stmt, ast.TypeAlias):
                alias_name = stmt.name.id
                val_expr = ast.unparse(stmt.value)
                self._insert_ast_state_or_alias(
                    container_id=container_id,
                    container_qname=container_qname,
                    name=alias_name,
                    symbol_kind="type_alias",
                    declared_type_expr=val_expr,
                    runtime_type_name="TypeAliasType",
                    literal_repr=val_expr,
                    is_constant=1,
                    is_mutable=0,
                    dunder_all=dunder_all,
                    provenance=provenance,
                    node=stmt,
                )
                continue

            # 4. Functions & Methods (grouped by name to merge `@overload` variants)
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_groups.setdefault(stmt.name, []).append((stmt, provenance))
                continue

            # 5. Classes & Exceptions
            if isinstance(stmt, ast.ClassDef):
                self._harvest_ast_class(
                    dist_id=dist_id,
                    parent_cid=container_id,
                    parent_qname=container_qname,
                    current_pkg_parts=current_pkg_parts,
                    cls_node=stmt,
                    dunder_all=dunder_all,
                    provenance=provenance,
                )
                continue

            # 6. Annotated Assignments (`x: int = 10`)
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                var_name = stmt.target.id
                if var_name == "__all__":
                    continue
                decl_t = ast.unparse(stmt.annotation)
                val_repr = ast.unparse(stmt.value) if stmt.value is not None else None
                is_const = 1 if (var_name.isupper() or "Final" in decl_t) else 0
                self._insert_ast_state_or_alias(
                    container_id=container_id,
                    container_qname=container_qname,
                    name=var_name,
                    symbol_kind="property" if is_class_scope else ("constant" if is_const else "variable"),
                    declared_type_expr=decl_t,
                    runtime_type_name=decl_t,
                    literal_repr=val_repr,
                    is_constant=is_const,
                    is_mutable=0 if is_const else 1,
                    dunder_all=dunder_all,
                    provenance=provenance,
                    node=stmt,
                )
                continue

            # 7. Standard Assignments (`x = 10`)
            if isinstance(stmt, ast.Assign):
                val_repr = ast.unparse(stmt.value)
                inferred_t = self._infer_ast_expr_type(stmt.value) or "object"
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        if var_name == "__all__":
                            continue
                        is_const = 1 if var_name.isupper() else 0
                        self._insert_ast_state_or_alias(
                            container_id=container_id,
                            container_qname=container_qname,
                            name=var_name,
                            symbol_kind="property" if is_class_scope else ("constant" if is_const else "variable"),
                            declared_type_expr=inferred_t if inferred_t != "object" else None,
                            runtime_type_name=inferred_t,
                            literal_repr=val_repr,
                            is_constant=is_const,
                            is_mutable=0 if is_const else 1,
                            dunder_all=dunder_all,
                            provenance=provenance,
                            node=stmt,
                        )

        # Process function groups
        for func_name, def_tuples in func_groups.items():
            self._harvest_ast_function_group(
                container_id=container_id,
                container_qname=container_qname,
                func_name=func_name,
                def_tuples=def_tuples,
                dunder_all=dunder_all,
                is_class_scope=is_class_scope,
            )

    @staticmethod
    def _resolve_import_from_module(current_pkg_parts: list[str], mod: str | None, level: int) -> str:
        """Resolves relative imports (`level > 0`) against package hierarchy."""
        if level == 0:
            return mod or ""
        base = current_pkg_parts[: max(0, len(current_pkg_parts) - (level - 1))]
        if mod:
            return f"{'.'.join(base)}.{mod}" if base else mod
        return ".".join(base)

    def _harvest_ast_class(
        self,
        *,
        dist_id: int,
        parent_cid: int,
        parent_qname: str,
        current_pkg_parts: list[str],
        cls_node: ast.ClassDef,
        dunder_all: set[str] | None,
        provenance: str,
    ) -> None:
        cls_name = cls_node.name
        cls_qname = f"{parent_qname}.{cls_name}"
        vis, is_hid = classify_identifier_visibility(cls_name, dunder_all)
        bases = [ast.unparse(b) for b in cls_node.bases]
        is_exc = any("Error" in b or "Exception" in b for b in bases)
        sym_kind = "exception" if is_exc else "class"
        container_kind = "exception_class" if is_exc else "class"
        metaclass_name = None
        for kw in cls_node.keywords:
            if kw.arg == "metaclass":
                metaclass_name = ast.unparse(kw.value)

        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden,
                start_line, start_col, end_line, end_col, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id;
            """,
            (
                parent_cid, parent_cid, cls_name, cls_qname, sym_kind, vis, provenance, is_hid,
                cls_node.lineno, cls_node.col_offset, cls_node.end_lineno, cls_node.end_col_offset,
                ast.get_docstring(cls_node),
            ),
        )
        row = cur.fetchone()
        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                VALUES (?, 'type', 0, 'meta');
                """,
                (sid,),
            )
            self.classes_found += 1

        cls_cid = self.cataloger.register_container(
            dist_id=dist_id,
            parent_id=parent_cid,
            container_kind=container_kind,
            qualified_name=cls_qname,
            short_name=cls_name,
            requires_import=1,
            visibility=vis,
            is_hidden=is_hid,
            docstring=ast.get_docstring(cls_node),
            module_origin_kind="class_body",
            base_classes=bases,
            mro_list=[cls_qname, *bases],
            metaclass_name=metaclass_name,
            start_line=cls_node.lineno,
            start_col=cls_node.col_offset,
            end_line=cls_node.end_lineno,
            end_col=cls_node.end_col_offset,
        )

        # Synthesize instance attributes from `__init__`, `__new__`, and `__post_init__`
        self._synthesize_init_attributes(cls_cid, cls_qname, cls_node)

        # Walk class body
        self._walk_container_statements(
            dist_id=dist_id,
            container_id=cls_cid,
            container_qname=cls_qname,
            current_pkg_parts=current_pkg_parts,
            stmts=cls_node.body,
            dunder_all=None,
            is_class_scope=True,
            provenance="ast_defined",
        )

    def _synthesize_init_attributes(self, cls_cid: int, cls_qname: str, cls_node: ast.ClassDef) -> None:
        """
        Scans constructor methods (`__init__`, `__new__`, `__post_init__`) for `self.<attr>`
        assignments, propagating parameter types from the constructor's parameters.
        """
        for item in cls_node.body:
            if isinstance(item, ast.FunctionDef) and item.name in ("__init__", "__new__", "__post_init__"):
                _, _, _, _, param_type_map = parse_ast_func_signature(item)

                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.Assign):
                        for tgt in stmt.targets:
                            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                                attr_name = tgt.attr
                                val_node = stmt.value
                                inferred_t = (
                                    param_type_map.get(val_node.id)
                                    if isinstance(val_node, ast.Name) and val_node.id in param_type_map
                                    else self._infer_ast_expr_type(val_node, param_type_map)
                                )
                                self._record_init_attr(
                                    cls_cid=cls_cid,
                                    cls_qname=cls_qname,
                                    attr_name=attr_name,
                                    type_expr=inferred_t,
                                    val_repr=ast.unparse(val_node),
                                    node=stmt,
                                )
                    elif isinstance(stmt, ast.AnnAssign):
                        if isinstance(stmt.target, ast.Attribute) and isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                            attr_name = stmt.target.attr
                            decl_t = ast.unparse(stmt.annotation)
                            val_repr = ast.unparse(stmt.value) if stmt.value is not None else None
                            self._record_init_attr(
                                cls_cid=cls_cid,
                                cls_qname=cls_qname,
                                attr_name=attr_name,
                                type_expr=decl_t,
                                val_repr=val_repr,
                                node=stmt,
                            )

    def _record_init_attr(
        self,
        *,
        cls_cid: int,
        cls_qname: str,
        attr_name: str,
        type_expr: str | None,
        val_repr: str | None,
        node: ast.AST,
    ) -> None:
        qname = f"{cls_qname}.{attr_name}"
        if attr_name.startswith("__") and not attr_name.endswith("__"):
            vis = "private_mangled"
            is_hid = 1
        elif attr_name.startswith("_"):
            vis = "hidden_internal"
            is_hid = 1
        else:
            vis = "public_implicit"
            is_hid = 0

        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden,
                start_line, start_col, end_line, end_col, docstring
            )
            VALUES (?, ?, ?, ?, 'property', ?, 'ast_init_attribute', ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id;
            """,
            (
                cls_cid, cls_cid, attr_name, qname, vis, is_hid,
                getattr(node, "lineno", None),
                getattr(node, "col_offset", None),
                getattr(node, "end_lineno", None),
                getattr(node, "end_col_offset", None),
            ),
        )
        row = cur.fetchone()
        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                INSERT INTO state_members (
                    symbol_id, declared_type_expr, runtime_type_name,
                    is_constant, is_mutable, literal_value_repr, access_mode
                )
                VALUES (?, ?, ?, 0, 1, ?, 'read_write');
                """,
                (sid, type_expr, type_expr or "object", val_repr),
            )
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, descriptor_kind, is_c_implemented)
                VALUES (?, 'instance_attribute', ?, 0);
                """,
                (sid, "private_mangled" if vis == "private_mangled" else None),
            )
            self.init_attrs_synthesized += 1

    def _harvest_ast_function_group(
        self,
        *,
        container_id: int,
        container_qname: str,
        func_name: str,
        def_tuples: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]],
        dunder_all: set[str] | None,
        is_class_scope: bool,
    ) -> None:
        defs = [t[0] for t in def_tuples]
        provenance = def_tuples[0][1]

        # Check property decorator
        if len(defs) == 1 and self._has_decorator(defs[0], "property"):
            ret_str = ast.unparse(defs[0].returns) if defs[0].returns else None
            vis, is_hid = classify_identifier_visibility(func_name, dunder_all)
            qname = f"{container_qname}.{func_name}"
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col, docstring
                )
                VALUES (?, ?, ?, ?, 'property', ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id;
                """,
                (
                    container_id, container_id, func_name, qname, vis, provenance, is_hid,
                    defs[0].lineno, defs[0].col_offset, defs[0].end_lineno, defs[0].end_col_offset,
                    ast.get_docstring(defs[0]),
                ),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                self.conn.execute(
                    """
                    INSERT INTO state_members (
                        symbol_id, declared_type_expr, runtime_type_name,
                        is_constant, is_mutable, literal_value_repr, access_mode
                    )
                    VALUES (?, ?, 'property', 0, 1, NULL, 'read_only');
                    """,
                    (sid, ret_str),
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, descriptor_kind, is_c_implemented)
                    VALUES (?, 'property', 'property', 0);
                    """,
                    (sid,),
                )
            return

        overload_defs = [d for d in defs if self._has_decorator(d, "overload")]
        impl_defs = [d for d in defs if not self._has_decorator(d, "overload")]
        impl_def = impl_defs[-1] if impl_defs else overload_defs[-1]
        is_overloaded = len(overload_defs) > 0

        vis, is_hid = classify_identifier_visibility(func_name, dunder_all)
        sym_kind = "constructor" if func_name in ("__init__", "__new__") else ("method" if is_class_scope else "function")
        qname = f"{container_qname}.{func_name}"
        dunder_cat = DUNDER_CATEGORIES.get(func_name)

        is_async = 1 if isinstance(impl_def, ast.AsyncFunctionDef) else 0
        is_gen = 1 if self._is_ast_generator_function(impl_def) else 0
        is_static = 1 if (not is_class_scope or self._has_decorator(impl_def, "staticmethod")) else 0
        is_cls_bound = 1 if self._has_decorator(impl_def, "classmethod") else 0

        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden,
                start_line, start_col, end_line, end_col, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id;
            """,
            (
                container_id, container_id, func_name, qname, sym_kind, vis, provenance, is_hid,
                impl_def.lineno, impl_def.col_offset, impl_def.end_lineno, impl_def.end_col_offset,
                ast.get_docstring(impl_def),
            ),
        )
        row = cur.fetchone()
        if not row:
            return
        sid = int(row[0])
        self.callables_found += 1

        primary_sig, primary_ret, primary_tparams, primary_params, _ = parse_ast_func_signature(impl_def)
        sig_source = "ast_overload_source" if is_overloaded else "ast_source"

        self.conn.execute(
            """
            INSERT INTO callables (
                symbol_id, is_async, is_generator, is_static, is_class_bound,
                has_overloads, overload_count, type_params_json,
                return_type_expr, raw_signature, signature_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                sid,
                is_async,
                is_gen,
                is_static,
                is_cls_bound,
                1 if is_overloaded else 0,
                len(overload_defs),
                json.dumps(primary_tparams) if primary_tparams else None,
                primary_ret,
                primary_sig,
                sig_source,
            ),
        )

        for p in primary_params:
            self.conn.execute(
                """
                INSERT INTO parameters (
                    callable_symbol_id, overload_id, ordinal, name, pass_kind,
                    type_expr, type_source, default_expr, is_optional
                )
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sid,
                    p["ordinal"],
                    p["name"],
                    p["pass_kind"],
                    p["type_expr"],
                    "ast_annotation" if p["type_expr"] else None,
                    p["default_expr"],
                    p["is_optional"],
                ),
            )

        if is_overloaded:
            for ov_idx, ov_def in enumerate(overload_defs):
                ov_sig, ov_ret, ov_tparams, ov_params, _ = parse_ast_func_signature(ov_def)
                cur_ov = self.conn.execute(
                    """
                    INSERT INTO callable_overloads (
                        callable_symbol_id, overload_ordinal, type_params_json,
                        return_type_expr, raw_signature
                    )
                    VALUES (?, ?, ?, ?, ?)
                    RETURNING overload_id;
                    """,
                    (sid, ov_idx, json.dumps(ov_tparams) if ov_tparams else None, ov_ret, ov_sig),
                )
                ov_id = int(cur_ov.fetchone()[0])
                for p in ov_params:
                    self.conn.execute(
                        """
                        INSERT INTO parameters (
                            callable_symbol_id, overload_id, ordinal, name, pass_kind,
                            type_expr, type_source, default_expr, is_optional
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 'ast_annotation', ?, ?);
                        """,
                        (sid, ov_id, p["ordinal"], p["name"], p["pass_kind"], p["type_expr"], p["default_expr"], p["is_optional"]),
                    )

        desc_kind = "staticmethod" if is_static and is_class_scope else ("classmethod" if is_cls_bound else "function")
        self.conn.execute(
            """
            INSERT INTO py_symbol_facets (
                symbol_id, py_runtime_type, descriptor_kind, is_c_implemented, dunder_category
            )
            VALUES (?, 'function', ?, 0, ?);
            """,
            (sid, desc_kind, dunder_cat),
        )

    def _insert_ast_state_or_alias(
        self,
        *,
        container_id: int,
        container_qname: str,
        name: str,
        symbol_kind: str,
        declared_type_expr: str | None,
        runtime_type_name: str,
        literal_repr: str | None,
        is_constant: int,
        is_mutable: int,
        dunder_all: set[str] | None,
        provenance: str,
        node: ast.AST,
    ) -> None:
        vis, is_hid = classify_identifier_visibility(name, dunder_all)
        qname = f"{container_qname}.{name}"
        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden,
                start_line, start_col, end_line, end_col, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id;
            """,
            (
                container_id, container_id, name, qname, symbol_kind, vis, provenance, is_hid,
                getattr(node, "lineno", None),
                getattr(node, "col_offset", None),
                getattr(node, "end_lineno", None),
                getattr(node, "end_col_offset", None),
            ),
        )
        row = cur.fetchone()
        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                INSERT INTO state_members (
                    symbol_id, declared_type_expr, runtime_type_name,
                    is_constant, is_mutable, literal_value_repr, access_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sid,
                    declared_type_expr,
                    runtime_type_name,
                    is_constant,
                    is_mutable,
                    literal_repr,
                    "read_only" if is_constant else "read_write",
                ),
            )
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented)
                VALUES (?, ?, 0);
                """,
                (sid, runtime_type_name),
            )

    @staticmethod
    def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, dec_name: str) -> bool:
        for dec in node.decorator_list:
            unparsed = ast.unparse(dec).strip()
            if unparsed == dec_name or unparsed.endswith(f".{dec_name}"):
                return True
        return False

    @classmethod
    def _is_ast_generator_function(cls, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Checks if a function body contains `yield` or `yield from` at its own lexical scope."""
        stack: list[ast.AST] = list(func_node.body)
        while stack:
            curr = stack.pop()
            if isinstance(curr, (ast.Yield, ast.YieldFrom)):
                return True
            if isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.extend(ast.iter_child_nodes(curr))
        return False

    @staticmethod
    def _infer_ast_expr_type(
        expr: ast.expr | None,
        param_type_map: dict[str, str] | None = None,
    ) -> str | None:
        if expr is None:
            return None
        if isinstance(expr, ast.Name) and param_type_map and expr.id in param_type_map:
            return param_type_map[expr.id]
        if isinstance(expr, ast.Constant):
            if expr.value is None:
                return "None"
            return type(expr.value).__name__
        if isinstance(expr, ast.List) or isinstance(expr, ast.ListComp):
            return "list"
        if isinstance(expr, ast.Dict) or isinstance(expr, ast.DictComp):
            return "dict"
        if isinstance(expr, ast.Set) or isinstance(expr, ast.SetComp):
            return "set"
        if isinstance(expr, ast.Tuple):
            return "tuple"
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                return expr.func.id
            if isinstance(expr.func, ast.Attribute):
                return ast.unparse(expr.func)
        return None


class WorkspaceASTHarvester:
    """Backwards-compatible wrapper delegating to `WorkspaceAstCataloger`."""

    def __init__(self, cataloger: Any, workspace_dir: Path) -> None:
        self.cataloger = cataloger
        self.workspace_dir = workspace_dir
        self.ws_cataloger = WorkspaceAstCataloger(cataloger)

    def harvest(self) -> int:
        return self.ws_cataloger.harvest_workspace(self.workspace_dir)
