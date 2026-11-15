"""
Pass 4: Static .pyi (Typeshed) AST Overlay Engine for UTSS.
Enriches runtime symbols with static type annotations, handles polymorphic @overload sets,
restores erased generic types on module/class variables, and evaluates static
sys.version_info / sys.platform guards without code execution.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

from utss.introspect import classify_identifier_visibility

# Embedded mini-typeshed stubs for zero-dependency testability and immediate verification.
# Derived from and modeled on typeshed definitions (https://github.com/python/typeshed),
# licensed under the Apache License, Version 2.0 (Copyright (c) Typeshed Contributors).
EMBEDDED_DEMO_STUBS: dict[str, str] = {
    "builtins": """
from typing import Any, Callable, Iterable, Iterator, Sequence, Sized, TypeVar, overload
import io

_T = TypeVar("_T")

def len(obj: Sized, /) -> int: ...
def print(*values: object, sep: str | None = " ", end: str | None = "\\n", file: io.TextIOBase | None = None, flush: bool = False) -> None: ...
def iter(iterable: Iterable[_T], /) -> Iterator[_T]: ...

@overload
def open(
    file: str | bytes | int,
    mode: str = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> io.TextIOWrapper: ...
@overload
def open(
    file: str | bytes | int,
    mode: str,
    buffering: int = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> io.BufferedRandom | io.BufferedReader | io.BufferedWriter: ...

@overload
def max(arg1: _T, arg2: _T, *_args: _T, key: Callable[[_T], Any] | None = None) -> _T: ...
@overload
def max(iterable: Iterable[_T], *, key: Callable[[_T], Any] | None = None) -> _T: ...
@overload
def max(iterable: Iterable[_T], *, key: Callable[[_T], Any] | None = None, default: _T) -> _T: ...

class str(Sequence[str]):
    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]: ...
    def join(self, iterable: Iterable[str], /) -> str: ...
    def replace(self, old: str, new: str, count: int = -1, /) -> str: ...
""",
    "sys": """
import sys
from typing import Any, NoReturn, TextIO

argv: list[str]
executable: str
platform: str
version: str
version_info: tuple[int, int, int, str, int]
modules: dict[str, Any]
path: list[str]
stdin: TextIO
stdout: TextIO
stderr: TextIO

def exit(status: str | int | None = None, /) -> NoReturn: ...
def getrecursionlimit() -> int: ...
def setrecursionlimit(limit: int, /) -> None: ...
def _getframe(depth: int = 0, /) -> Any: ...

if sys.version_info >= (3, 12):
    def getunicodeinternedsize(*, _only_immortal: bool = False) -> int: ...
""",
    "os": """
from typing import Any, Callable, Iterator, Mapping, MutableMapping, overload

environ: MutableMapping[str, str]
sep: str
linesep: str
name: str

def getcwd() -> str: ...
def listdir(path: str | bytes | None = None) -> list[str]: ...
def makedirs(name: str | bytes, mode: int = 0o777, exist_ok: bool = False) -> None: ...
def walk(
    top: str,
    topdown: bool = True,
    onerror: Callable[[OSError], object] | None = None,
    followlinks: bool = False,
) -> Iterator[tuple[str, list[str], list[str]]]: ...

@overload
def getenv(key: str) -> str | None: ...
@overload
def getenv(key: str, default: str) -> str: ...
""",
    "json": """
from typing import Any, Callable, IO

def dumps(
    obj: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    default: Callable[[Any], Any] | None = None,
    sort_keys: bool = False,
) -> str: ...

def loads(
    s: str | bytes | bytearray,
    *,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
    parse_float: Callable[[str], Any] | None = None,
    parse_int: Callable[[str], Any] | None = None,
    parse_constant: Callable[[str], Any] | None = None,
    strict: bool = True,
) -> Any: ...
""",
}


# ============================================================================
# STATIC GUARD EVALUATION (sys.version_info & sys.platform)
# ============================================================================

def eval_static_guard(
    test: ast.expr, py_version: tuple[int, int], sys_platform: str
) -> bool | None:
    """Evaluates `sys.version_info >= (3, 12)` and `sys.platform == 'linux'` AST expressions."""
    if isinstance(test, ast.BoolOp):
        vals = [eval_static_guard(v, py_version, sys_platform) for v in test.values]
        if isinstance(test.op, ast.And):
            if any(v is False for v in vals):
                return False
            if all(v is True for v in vals):
                return True
            return None
        if isinstance(test.op, ast.Or):
            if any(v is True for v in vals):
                return True
            if all(v is False for v in vals):
                return False
            return None

    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = eval_static_guard(test.operand, py_version, sys_platform)
        return (not inner) if inner is not None else None

    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        left_s = ast.unparse(test.left).strip()
        op = test.ops[0]
        right_node = test.comparators[0]

        if left_s in ("sys.version_info", "version_info") and isinstance(right_node, ast.Tuple):
            try:
                ver_tuple = tuple(int(ast.literal_eval(elt)) for elt in right_node.elts[:2])
                lhs = py_version[: len(ver_tuple)]
                return _apply_cmp(lhs, op, ver_tuple)
            except Exception:
                return None

        if (
            left_s in ("sys.platform", "platform")
            and isinstance(right_node, ast.Constant)
            and isinstance(right_node.value, str)
        ):
            return _apply_cmp(sys_platform, op, right_node.value)

    return None


def _apply_cmp(lhs: Any, op: ast.cmpop, rhs: Any) -> bool | None:
    if isinstance(op, ast.GtE):
        return bool(lhs >= rhs)
    if isinstance(op, ast.Gt):
        return bool(lhs > rhs)
    if isinstance(op, ast.LtE):
        return bool(lhs <= rhs)
    if isinstance(op, ast.Lt):
        return bool(lhs < rhs)
    if isinstance(op, ast.Eq):
        return bool(lhs == rhs)
    if isinstance(op, ast.NotEq):
        return bool(lhs != rhs)
    return None


def flatten_active_statements(
    stmts: list[ast.stmt], py_version: tuple[int, int], sys_platform: str
) -> list[ast.stmt]:
    """Prunes dead AST branches and flattens active branches based on static guards."""
    out: list[ast.stmt] = []
    for stmt in stmts:
        if isinstance(stmt, ast.If):
            branch_val = eval_static_guard(stmt.test, py_version, sys_platform)
            if branch_val is True:
                out.extend(flatten_active_statements(stmt.body, py_version, sys_platform))
            elif branch_val is False:
                out.extend(flatten_active_statements(stmt.orelse, py_version, sys_platform))
            else:
                out.extend(flatten_active_statements(stmt.body, py_version, sys_platform))
        else:
            out.append(stmt)
    return out


# ============================================================================
# PASS 4: STATIC .pyi (TYPESHED) AST OVERLAY CATALOGER
# ============================================================================

class StaticPyiOverlayCataloger:
    """
    Overlays static type signatures, `@overload` variants, and generic variable annotations
    from `.pyi` stub files (Typeshed or embedded stubs) onto the runtime catalog.
    Never imports or executes code; uses pure Python `ast` analysis + static branch evaluation.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        row = conn.execute("SELECT version_major, version_minor, sys_platform FROM environments LIMIT 1;").fetchone()
        if row:
            self.py_version: tuple[int, int] = (int(row[0]), int(row[1]))
            self.sys_platform: str = str(row[2])
        else:
            self.py_version = (sys.version_info.major, sys.version_info.minor)
            self.sys_platform = sys.platform

        self.enriched_callables: int = 0
        self.inserted_overloads: int = 0
        self.enriched_state_members: int = 0
        self.stub_only_symbols: int = 0

    @staticmethod
    def auto_discover_typeshed_dirs() -> list[Path]:
        """Searches installed site-packages (mypy, pyright, typeshed_client) for stdlib .pyi directories."""
        found: list[Path] = []
        for site_dir in sys.path:
            if not site_dir:
                continue
            base = Path(site_dir)
            candidates = [
                base / "mypy" / "typeshed" / "stdlib",
                base / "typeshed_client" / "typeshed",
                base / "pyright" / "dist" / "typeshed-fallback" / "stdlib",
            ]
            for c in candidates:
                if c.is_dir() and (c / "builtins.pyi").is_file():
                    found.append(c)
        return found

    def resolve_stub_file(self, typeshed_root: Path, mod_name: str) -> Path | None:
        """Resolves a dotted module name to its `.pyi` file inside a typeshed root."""
        stdlib_dir = typeshed_root / "stdlib" if (typeshed_root / "stdlib").is_dir() else typeshed_root
        parts = mod_name.split(".")
        rel_file = stdlib_dir.joinpath(*parts).with_suffix(".pyi")
        if rel_file.is_file():
            return rel_file
        rel_init = stdlib_dir.joinpath(*parts, "__init__.pyi")
        if rel_init.is_file():
            return rel_init
        stubs_dir = typeshed_root / "stubs"
        if stubs_dir.is_dir():
            for pkg_dir in stubs_dir.iterdir():
                cand_file = pkg_dir.joinpath(*parts).with_suffix(".pyi")
                if cand_file.is_file():
                    return cand_file
                cand_init = pkg_dir.joinpath(*parts, "__init__.pyi")
                if cand_init.is_file():
                    return cand_init
        return None

    def overlay_from_directory(self, typeshed_root: Path, module_filter: set[str] | None = None) -> None:
        """Applies `.pyi` overlays for `<ambient>` (`builtins.pyi`) and harvested modules in the DB."""
        rows = self.conn.execute(
            """
            SELECT container_id, qualified_name
            FROM containers
            WHERE container_kind IN ('ambient_scope', 'module', 'package');
            """
        ).fetchall()

        for cid, qname in rows:
            lookup_mod = "builtins" if qname == "<ambient>" else qname
            if module_filter and lookup_mod != "builtins" and lookup_mod not in module_filter:
                continue
            stub_path = self.resolve_stub_file(typeshed_root, lookup_mod)
            if stub_path is not None:
                try:
                    source = stub_path.read_text(encoding="utf-8", errors="replace")
                    self.overlay_stub_source(
                        container_id=int(cid),
                        container_qname=qname,
                        stub_source=source,
                        stub_path_str=str(stub_path),
                    )
                except Exception:
                    continue
        self.conn.commit()

    def overlay_embedded_demo_stubs(self) -> None:
        """Overlays the built-in EMBEDDED_DEMO_STUBS (builtins, sys, os, json) for clean-room environments."""
        for mod_key, stub_src in EMBEDDED_DEMO_STUBS.items():
            qname = "<ambient>" if mod_key == "builtins" else mod_key
            row = self.conn.execute(
                "SELECT container_id FROM containers WHERE qualified_name = ? LIMIT 1;",
                (qname,),
            ).fetchone()
            if row:
                self.overlay_stub_source(
                    container_id=int(row[0]),
                    container_qname=qname,
                    stub_source=stub_src,
                    stub_path_str=f"<embedded-typeshed:{mod_key}.pyi>",
                )
        self.conn.commit()

    def overlay_stub_source(
        self,
        *,
        container_id: int,
        container_qname: str,
        stub_source: str,
        stub_path_str: str,
    ) -> None:
        tree = ast.parse(stub_source, filename=stub_path_str)
        self.conn.execute(
            "UPDATE containers SET stub_path = ? WHERE container_id = ?;",
            (stub_path_str, container_id),
        )
        active_stmts = flatten_active_statements(tree.body, self.py_version, self.sys_platform)
        self._apply_statements_to_container(container_id, container_qname, active_stmts, is_class_scope=False)

    def _apply_statements_to_container(
        self,
        container_id: int,
        container_qname: str,
        stmts: list[ast.stmt],
        *,
        is_class_scope: bool,
    ) -> None:
        # Group functions by name so multiple `@overload` defs for the same callable are processed together
        func_groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}

        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_groups.setdefault(stmt.name, []).append(stmt)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                self._overlay_ann_assign(container_id, container_qname, stmt, is_class_scope=is_class_scope)
            elif isinstance(stmt, ast.ClassDef):
                self._overlay_class_def(container_id, container_qname, stmt)

        for func_name, defs in func_groups.items():
            self._overlay_callable_group(container_id, container_qname, func_name, defs, is_class_scope=is_class_scope)

    def _overlay_ann_assign(
        self,
        container_id: int,
        container_qname: str,
        stmt: ast.AnnAssign,
        *,
        is_class_scope: bool,
    ) -> None:
        assert isinstance(stmt.target, ast.Name)
        var_name = stmt.target.id
        type_str = ast.unparse(stmt.annotation)

        row = self.conn.execute(
            "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1;",
            (container_id, var_name),
        ).fetchone()

        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                UPDATE state_members
                SET declared_type_expr = ?
                WHERE symbol_id = ?;
                """,
                (type_str, sid),
            )
            self.conn.execute(
                "UPDATE symbols SET provenance = 'pyi_enriched' WHERE symbol_id = ? AND provenance = 'defined_here';",
                (sid,),
            )
            self.enriched_state_members += 1
        else:
            vis, is_hid = classify_identifier_visibility(var_name)
            sym_kind = "property" if is_class_scope else ("constant" if var_name.isupper() else "variable")
            qname = f"{container_qname}.{var_name}"
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub_only', ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id;
                """,
                (
                    container_id,
                    container_id,
                    var_name,
                    qname,
                    sym_kind,
                    vis,
                    is_hid,
                    getattr(stmt, "lineno", None),
                    getattr(stmt, "col_offset", None),
                    getattr(stmt, "end_lineno", None),
                    getattr(stmt, "end_col_offset", None),
                ),
            )
            res = cur.fetchone()
            if res:
                sid = int(res[0])
                self.conn.execute(
                    """
                    INSERT INTO state_members (
                        symbol_id, declared_type_expr, runtime_type_name,
                        is_constant, is_mutable, literal_value_repr, access_mode
                    )
                    VALUES (?, ?, '<pyi_static>', ?, ?, NULL, 'read_write');
                    """,
                    (sid, type_str, 1 if var_name.isupper() else 0, 0 if var_name.isupper() else 1),
                )
                self.stub_only_symbols += 1

    def _overlay_class_def(self, parent_cid: int, parent_qname: str, cls_node: ast.ClassDef) -> None:
        cls_qname = f"{parent_qname}.{cls_node.name}"
        row = self.conn.execute(
            "SELECT container_id FROM containers WHERE qualified_name = ? LIMIT 1;",
            (cls_qname,),
        ).fetchone()
        if not row:
            return
        cls_cid = int(row[0])
        active_body = flatten_active_statements(cls_node.body, self.py_version, self.sys_platform)
        self._apply_statements_to_container(cls_cid, cls_qname, active_body, is_class_scope=True)

    def _overlay_callable_group(
        self,
        container_id: int,
        container_qname: str,
        func_name: str,
        defs: list[ast.FunctionDef | ast.AsyncFunctionDef],
        *,
        is_class_scope: bool,
    ) -> None:
        # Check if `@property` decorator is present on a single def
        if len(defs) == 1 and self._has_decorator(defs[0], "property"):
            ret_str = ast.unparse(defs[0].returns) if defs[0].returns else "Any"
            row = self.conn.execute(
                "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1;",
                (container_id, func_name),
            ).fetchone()
            if row:
                self.conn.execute(
                    "UPDATE state_members SET declared_type_expr = ? WHERE symbol_id = ?;",
                    (ret_str, int(row[0])),
                )
                self.enriched_state_members += 1
            return

        row = self.conn.execute(
            "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1;",
            (container_id, func_name),
        ).fetchone()

        first_def = defs[0]
        is_async = 1 if isinstance(first_def, ast.AsyncFunctionDef) else 0
        is_static = 1 if (not is_class_scope or self._has_decorator(first_def, "staticmethod")) else 0
        is_cls_bound = 1 if self._has_decorator(first_def, "classmethod") else 0

        if row:
            sid = int(row[0])
            self.conn.execute(
                "UPDATE symbols SET provenance = 'pyi_enriched' WHERE symbol_id = ? AND provenance = 'defined_here';",
                (sid,),
            )
        else:
            vis, is_hid = classify_identifier_visibility(func_name)
            sym_kind = "constructor" if func_name in ("__init__", "__new__") else ("method" if is_class_scope else "function")
            qname = f"{container_qname}.{func_name}"
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub_only', ?, ?, ?, ?, ?, ?)
                RETURNING symbol_id;
                """,
                (
                    container_id,
                    container_id,
                    func_name,
                    qname,
                    sym_kind,
                    vis,
                    is_hid,
                    getattr(first_def, "lineno", None),
                    getattr(first_def, "col_offset", None),
                    getattr(first_def, "end_lineno", None),
                    getattr(first_def, "end_col_offset", None),
                    ast.get_docstring(first_def),
                ),
            )
            sid = int(cur.fetchone()[0])
            self.stub_only_symbols += 1

        overload_defs = [d for d in defs if self._has_decorator(d, "overload")]
        target_defs = overload_defs if len(overload_defs) > 0 else [defs[-1]]
        is_overloaded = len(overload_defs) > 0

        primary_sig, primary_ret, primary_tparams, primary_params = self._parse_ast_func_signature(target_defs[0])
        if is_overloaded:
            unique_rets: list[str] = []
            for d in overload_defs:
                _, r_str, _, _ = self._parse_ast_func_signature(d)
                if r_str and r_str not in unique_rets:
                    unique_rets.append(r_str)
            primary_ret = " | ".join(unique_rets) if unique_rets else primary_ret

        sig_source = "pyi_overload_overlay" if is_overloaded else "pyi_stub_overlay"

        self.conn.execute(
            """
            INSERT INTO callables (
                symbol_id, is_async, is_generator, is_static, is_class_bound,
                has_overloads, overload_count, type_params_json,
                return_type_expr, raw_signature, signature_source
            )
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO UPDATE SET
                has_overloads = excluded.has_overloads,
                overload_count = excluded.overload_count,
                type_params_json = COALESCE(excluded.type_params_json, callables.type_params_json),
                return_type_expr = COALESCE(excluded.return_type_expr, callables.return_type_expr),
                raw_signature = excluded.raw_signature,
                signature_source = excluded.signature_source;
            """,
            (
                sid,
                is_async,
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

        # Replace untyped primary parameters with rich .pyi primary parameters
        self.conn.execute(
            "DELETE FROM parameters WHERE callable_symbol_id = ? AND overload_id IS NULL;",
            (sid,),
        )
        for p in primary_params:
            self.conn.execute(
                """
                INSERT INTO parameters (
                    callable_symbol_id, overload_id, ordinal, name, pass_kind,
                    type_expr, type_source, default_expr, is_optional
                )
                VALUES (?, NULL, ?, ?, ?, ?, 'pyi_stub', ?, ?);
                """,
                (
                    sid,
                    p["ordinal"],
                    p["name"],
                    p["pass_kind"],
                    p["type_expr"],
                    p["default_expr"],
                    p["is_optional"],
                ),
            )

        # Record @overload variants in callable_overloads + parameters
        if is_overloaded:
            self.conn.execute("DELETE FROM callable_overloads WHERE callable_symbol_id = ?;", (sid,))
            for ov_idx, ov_def in enumerate(overload_defs):
                ov_sig, ov_ret, ov_tparams, ov_params = self._parse_ast_func_signature(ov_def)
                cur = self.conn.execute(
                    """
                    INSERT INTO callable_overloads (
                        callable_symbol_id, overload_ordinal, type_params_json,
                        return_type_expr, raw_signature
                    )
                    VALUES (?, ?, ?, ?, ?)
                    RETURNING overload_id;
                    """,
                    (
                        sid,
                        ov_idx,
                        json.dumps(ov_tparams) if ov_tparams else None,
                        ov_ret,
                        ov_sig,
                    ),
                )
                ov_id = int(cur.fetchone()[0])
                self.inserted_overloads += 1

                for p in ov_params:
                    self.conn.execute(
                        """
                        INSERT INTO parameters (
                            callable_symbol_id, overload_id, ordinal, name, pass_kind,
                            type_expr, type_source, default_expr, is_optional
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub', ?, ?);
                        """,
                        (
                            sid,
                            ov_id,
                            p["ordinal"],
                            p["name"],
                            p["pass_kind"],
                            p["type_expr"],
                            p["default_expr"],
                            p["is_optional"],
                        ),
                    )

        self.enriched_callables += 1

    @staticmethod
    def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, dec_name: str) -> bool:
        for dec in node.decorator_list:
            unparsed = ast.unparse(dec).strip()
            if unparsed == dec_name or unparsed.endswith(f".{dec_name}"):
                return True
        return False

    @staticmethod
    def _parse_ast_func_signature(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> tuple[str, str | None, list[str], list[dict[str, Any]]]:
        """Extracts (raw_signature, return_type_expr, type_params, params_list) from an AST FunctionDef."""
        args = node.args
        params: list[dict[str, Any]] = []
        ordinal = 0

        # Positional only
        posonly = args.posonlyargs
        posonly_defaults = [None] * (len(posonly) - len(args.defaults[: max(0, len(posonly))]))
        for i, a in enumerate(posonly):
            t_expr = ast.unparse(a.annotation) if a.annotation else None
            params.append({
                "ordinal": ordinal,
                "name": a.arg,
                "pass_kind": "positional_only",
                "type_expr": t_expr,
                "default_expr": None,
                "is_optional": 0,
            })
            ordinal += 1

        # Positional or keyword
        reg_args = args.args
        num_defaults = len(args.defaults)
        default_offset = len(reg_args) - num_defaults
        for i, a in enumerate(reg_args):
            t_expr = ast.unparse(a.annotation) if a.annotation else None
            def_expr = None
            is_opt = 0
            if i >= default_offset and default_offset >= 0:
                def_node = args.defaults[i - default_offset]
                def_expr = ast.unparse(def_node)
                is_opt = 1

            params.append({
                "ordinal": ordinal,
                "name": a.arg,
                "pass_kind": "positional_or_keyword",
                "type_expr": t_expr,
                "default_expr": def_expr,
                "is_optional": is_opt,
            })
            ordinal += 1

        # Varargs (*args)
        if args.vararg:
            t_expr = ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
            params.append({
                "ordinal": ordinal,
                "name": args.vararg.arg,
                "pass_kind": "var_positional",
                "type_expr": t_expr,
                "default_expr": None,
                "is_optional": 1,
            })
            ordinal += 1

        # Keyword only
        for i, a in enumerate(args.kwonlyargs):
            t_expr = ast.unparse(a.annotation) if a.annotation else None
            def_node = args.kw_defaults[i]
            def_expr = ast.unparse(def_node) if def_node is not None else None
            params.append({
                "ordinal": ordinal,
                "name": a.arg,
                "pass_kind": "keyword_only",
                "type_expr": t_expr,
                "default_expr": def_expr,
                "is_optional": 1 if def_expr is not None else 0,
            })
            ordinal += 1

        # Kwargs (**kwargs)
        if args.kwarg:
            t_expr = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
            params.append({
                "ordinal": ordinal,
                "name": args.kwarg.arg,
                "pass_kind": "var_keyword",
                "type_expr": t_expr,
                "default_expr": None,
                "is_optional": 1,
            })
            ordinal += 1

        ret_expr = ast.unparse(node.returns) if node.returns else None

        # Build raw signature string
        param_strs = []
        for p in params:
            s = p["name"]
            if p["type_expr"]:
                s += f": {p['type_expr']}"
            if p["default_expr"]:
                s += f" = {p['default_expr']}"
            param_strs.append(s)
        raw_sig = f"({', '.join(param_strs)})"
        if ret_expr:
            raw_sig += f" -> {ret_expr}"

        type_params: list[str] = []
        if hasattr(node, "type_params") and node.type_params:
            type_params = [p.name for p in node.type_params]

        return (raw_sig, ret_expr, type_params, params)
