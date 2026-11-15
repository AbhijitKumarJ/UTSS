"""
Central Spectrum Cataloger Engine for UTSS.
Discovers and records language environments, distributions, containers, symbols,
and facets into the dual-layer SQLite schema.
"""

from __future__ import annotations

import builtins
import importlib
import importlib.machinery
import importlib.metadata
import importlib.util
import inspect
import json
import keyword
import os
from pathlib import Path
import pkgutil
import platform
import sqlite3
import sys
import sysconfig
import types
from typing import Any

from utss.introspect import (
    DUNDER_CATEGORIES,
    IMPLICIT_MODULE_DUNDERS,
    classify_identifier_visibility,
    compute_file_sha256,
    extract_callable_signature,
    get_pure_builtins_without_site,
    safe_repr,
)
from utss.schema import init_db

# Modules in stdlib that trigger GUI windows, browsers, stdout poems, or heavy test suites on import
SIDE_EFFECT_STDLIB_MODULES: frozenset[str] = frozenset({
    "antigravity",
    "this",
    "idlelib",
    "tkinter",
    "turtle",
    "turtledemo",
    "test",
    "lib2to3",
    "ensurepip",
    "venv",
    "pydoc_data",
    "__hello__",
    "__phello__",
    "_xxsubinterpreters",
    "_xxinterpchannels",
    "_xxtestfuzz",
})


class PythonSpectrumCataloger:
    """Cataloger engine responsible for harvesting Strata 0, 1, 2, and 3."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.env_id: int = -1
        self.pure_builtin_names: set[str] = get_pure_builtins_without_site()

    def init_db(self, reset: bool = False) -> None:
        init_db(self.conn, reset=reset)

    def register_environment(self) -> int:
        """Snapshots the active Python runtime into the environments table."""
        vi = sys.version_info
        plat = f"{platform.system()}-{platform.machine()}"
        cur = self.conn.execute(
            """
            INSERT INTO environments (
                language, runtime_name, language_version,
                version_major, version_minor, version_micro,
                platform_triplet, sys_platform, executable_path
            )
            VALUES ('python', ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
            DO UPDATE SET captured_at = CURRENT_TIMESTAMP
            RETURNING env_id
            """,
            (
                platform.python_implementation(),
                platform.python_version(),
                vi.major,
                vi.minor,
                vi.micro,
                plat,
                sys.platform,
                sys.executable,
            ),
        )
        self.env_id = int(cur.fetchone()[0])
        self.conn.commit()
        return self.env_id

    def register_distribution(
        self, stratum: int, dist_name: str, dist_version: str, summary: str | None = None
    ) -> int:
        """Registers a logical distribution unit (Ambient, Stdlib, Third-Party, Workspace)."""
        if self.env_id == -1:
            self.register_environment()

        cur = self.conn.execute(
            """
            INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(env_id, stratum, dist_name, dist_version)
            DO UPDATE SET summary = COALESCE(excluded.summary, distributions.summary)
            RETURNING dist_id
            """,
            (self.env_id, stratum, dist_name, dist_version, summary),
        )
        return int(cur.fetchone()[0])

    def register_container(
        self,
        *,
        dist_id: int,
        parent_id: int | None,
        container_kind: str,
        qualified_name: str,
        short_name: str,
        requires_import: int,
        visibility: str,
        is_hidden: int,
        physical_path: str | None = None,
        docstring: str | None = None,
        module_origin_kind: str | None = None,
        dunder_all: list[str] | None = None,
        has_lazy_getattr: bool = False,
        base_classes: list[str] | None = None,
        mro_list: list[str] | None = None,
        metaclass_name: str | None = None,
        start_line: int | None = None,
        start_col: int | None = None,
        end_line: int | None = None,
        end_col: int | None = None,
    ) -> int:
        """Registers a container (ambient scope, package, module, class) and its Python facet."""
        sha = compute_file_sha256(physical_path)
        cur = self.conn.execute(
            """
            INSERT INTO containers (
                dist_id, parent_container_id, container_kind, qualified_name,
                short_name, requires_import, visibility, is_hidden,
                physical_path, sha256_hash, start_line, start_col, end_line, end_col, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dist_id, qualified_name) DO UPDATE SET
                physical_path = COALESCE(excluded.physical_path, containers.physical_path),
                start_line = COALESCE(excluded.start_line, containers.start_line),
                end_line = COALESCE(excluded.end_line, containers.end_line),
                docstring = COALESCE(excluded.docstring, containers.docstring)
            RETURNING container_id
            """,
            (
                dist_id,
                parent_id,
                container_kind,
                qualified_name,
                short_name,
                requires_import,
                visibility,
                is_hidden,
                physical_path,
                sha,
                start_line,
                start_col,
                end_line,
                end_col,
                docstring,
            ),
        )
        cid = int(cur.fetchone()[0])

        self.conn.execute(
            """
            INSERT INTO py_container_facets (
                container_id, module_origin_kind, has_dunder_all, dunder_all_json,
                has_lazy_getattr, base_classes_json, mro_json, metaclass_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(container_id) DO UPDATE SET
                module_origin_kind = COALESCE(excluded.module_origin_kind, py_container_facets.module_origin_kind)
            """,
            (
                cid,
                module_origin_kind,
                1 if dunder_all is not None else 0,
                json.dumps(dunder_all) if dunder_all is not None else None,
                1 if has_lazy_getattr else 0,
                json.dumps(base_classes) if base_classes is not None else None,
                json.dumps(mro_list) if mro_list is not None else None,
                metaclass_name,
            ),
        )
        return cid

    # ========================================================================
    # STRATUM 0: AMBIENT SCOPE (NO IMPORT REQUIRED)
    # ========================================================================

    def harvest_stratum_0_ambient(self) -> None:
        """Catalogs Stratum 0: Keywords, builtins, site-builtins, and implicit dunders."""
        py_ver = platform.python_version()
        dist_id = self.register_distribution(
            stratum=0,
            dist_name="<ambient>",
            dist_version=py_ver,
            summary="Unqualified Python ambient scope: keywords, builtins, site-builtins, and implicit module dunders.",
        )

        ambient_cid = self.register_container(
            dist_id=dist_id,
            parent_id=None,
            container_kind="ambient_scope",
            qualified_name="<ambient>",
            short_name="<ambient>",
            requires_import=0,
            visibility="public",
            is_hidden=0,
            docstring="Symbols and syntax constructs available in Python without any import statement.",
            module_origin_kind="ambient",
        )

        # 0A. Hard Keywords & Soft Keywords
        for kw in keyword.kwlist:
            self._insert_keyword_symbol(ambient_cid, kw, is_soft=False)
        for skw in getattr(keyword, "softkwlist", []):
            self._insert_keyword_symbol(ambient_cid, skw, is_soft=True)

        # 0B. Implicit Module-Level Dunders (__name__, __file__, __doc__, etc.)
        for d_name, d_type, d_doc in IMPLICIT_MODULE_DUNDERS:
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, 'variable', 'system_dunder', 'implicit_dunder', 0, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (ambient_cid, ambient_cid, d_name, f"<ambient>.{d_name}", d_doc),
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
                    VALUES (?, ?, ?, 0, 1, NULL, 'read_write')
                    """,
                    (sid, d_type, d_type),
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                    VALUES (?, 'implicit_module_dunder', 1, 'meta')
                    """,
                    (sid,),
                )

        # 0C & 0D. Everything inside `builtins`
        for name, obj in sorted(builtins.__dict__.items()):
            provenance = "defined_here" if name in self.pure_builtin_names else "site_injected"
            self._harvest_runtime_member(
                dist_id=dist_id,
                parent_cid=ambient_cid,
                parent_qname="<ambient>",
                module_name="builtins",
                name=name,
                obj=obj,
                dunder_all=None,
                requires_import=0,
                override_provenance=provenance,
            )

        self.conn.commit()

    def _insert_keyword_symbol(self, ambient_cid: int, kw: str, *, is_soft: bool) -> None:
        kind = "soft_keyword" if is_soft else "keyword"
        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden, docstring
            )
            VALUES (?, ?, ?, ?, ?, 'public_implicit', 'defined_here', 0, ?)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id
            """,
            (
                ambient_cid,
                ambient_cid,
                kw,
                f"<ambient>.{kw}",
                kind,
                f"Python {'soft ' if is_soft else ''}keyword `{kw}`.",
            ),
        )
        row = cur.fetchone()
        if row:
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented)
                VALUES (?, ?, 1)
                """,
                (int(row[0]), kind),
            )

    # ========================================================================
    # STRATUM 1: VERSIONED PYTHON INSTALLATION (STDLIB PUBLIC & HIDDEN)
    # ========================================================================

    def discover_stdlib_modules(self, include_submodules: bool = False) -> list[str]:
        """Discovers built-in C modules, sys.stdlib_module_names, and top-level `_` internal modules."""
        names: set[str] = set(sys.builtin_module_names)
        if hasattr(sys, "stdlib_module_names"):
            names.update(sys.stdlib_module_names)

        # Also scan stdlib and lib-dynload directories for private `_` C-accelerators or internal modules
        for path_key in ("stdlib", "platstdlib"):
            p_str = sysconfig.get_path(path_key)
            if p_str and Path(p_str).is_dir():
                for mod_info in pkgutil.iter_modules([p_str]):
                    names.add(mod_info.name)

        filtered = sorted(
            n for n in names
            if n not in SIDE_EFFECT_STDLIB_MODULES and not n.startswith("test.")
        )

        if not include_submodules:
            return filtered

        expanded: list[str] = []
        for mod_name in filtered:
            expanded.append(mod_name)
            try:
                spec = importlib.util.find_spec(mod_name)
                if spec and spec.submodule_search_locations:
                    for sub in pkgutil.walk_packages(spec.submodule_search_locations, prefix=f"{mod_name}."):
                        if not any(part in SIDE_EFFECT_STDLIB_MODULES for part in sub.name.split(".")):
                            expanded.append(sub.name)
            except Exception:
                continue
        return sorted(set(expanded))

    def harvest_stratum_1_stdlib(
        self, module_filter: set[str] | None = None, include_submodules: bool = False
    ) -> None:
        """Catalogs Stratum 1: Stdlib modules (both public facades and hidden C implementations)."""
        py_ver = platform.python_version()
        dist_id = self.register_distribution(
            stratum=1,
            dist_name="python-stdlib",
            dist_version=py_ver,
            summary=f"Standard library and compiled-in modules shipped with {platform.python_implementation()} {py_ver}.",
        )

        candidates = self.discover_stdlib_modules(include_submodules=include_submodules)
        if module_filter:
            candidates = [
                m for m in candidates
                if m in module_filter or m.split(".")[0] in module_filter
            ]

        for mod_name in candidates:
            self.harvest_module_by_name(dist_id=dist_id, mod_name=mod_name)
        self.conn.commit()

    # ========================================================================
    # STRATUM 2: ENVIRONMENT THIRD-PARTY PACKAGES
    # ========================================================================

    def harvest_stratum_2_third_party(self, target_packages: set[str] | None = None) -> None:
        """Catalogs Stratum 2: Installed third-party packages via importlib.metadata."""
        pkg_to_dists = importlib.metadata.packages_distributions()
        visited_dists: set[tuple[str, str]] = set()

        for dist in importlib.metadata.distributions():
            dist_name = dist.metadata["Name"] or "unknown"
            dist_ver = dist.version or "0.0.0"
            if (dist_name, dist_ver) in visited_dists:
                continue
            visited_dists.add((dist_name, dist_ver))

            summary = dist.metadata.get("Summary")
            dist_id = self.register_distribution(
                stratum=2,
                dist_name=dist_name,
                dist_version=dist_ver,
                summary=summary,
            )

            if target_packages is not None and len(target_packages) > 0:
                top_pkgs = [
                    pkg for pkg, d_names in pkg_to_dists.items()
                    if dist_name in d_names
                ]
                if dist_name not in target_packages and not any(p in target_packages for p in top_pkgs):
                    continue
                for pkg in sorted(set(top_pkgs)):
                    if pkg in target_packages or dist_name in target_packages:
                        self.harvest_module_by_name(dist_id=dist_id, mod_name=pkg)
            elif target_packages is None:
                # Harvest all installed top packages
                top_pkgs = [
                    pkg for pkg, d_names in pkg_to_dists.items()
                    if dist_name in d_names
                ]
                for pkg in sorted(set(top_pkgs)):
                    self.harvest_module_by_name(dist_id=dist_id, mod_name=pkg)

        self.conn.commit()

    # ========================================================================
    # STRATUM 3: WORKSPACE SOURCE FILES (AST PARSING WITHOUT EXECUTION)
    # ========================================================================

    def harvest_stratum_3_workspace(
        self,
        workspace_dir: str | Path = ".",
        *,
        project_name: str | None = None,
        project_version: str = "0.1.0-local",
    ) -> int:
        """Catalogs Stratum 3: Static workspace source files using AST without code execution."""
        from utss.workspace import WorkspaceAstCataloger
        harvester = WorkspaceAstCataloger(self)
        return harvester.harvest_workspace(
            Path(workspace_dir),
            project_name=project_name,
            project_version=project_version,
        )

    # ========================================================================
    # PASS 4: STATIC .pyi / TYPESHED OVERLAY
    # ========================================================================

    def apply_pyi_overlay(
        self,
        *,
        typeshed_dir: str | Path | None = None,
        use_demo_stubs: bool = False,
        module_filter: set[str] | None = None,
    ) -> None:
        """Enriches cataloged symbols with static .pyi Typeshed annotations and @overload sets."""
        from utss.overlay import StaticPyiOverlayCataloger
        overlay_engine = StaticPyiOverlayCataloger(self.conn)
        if use_demo_stubs:
            overlay_engine.overlay_embedded_demo_stubs()
        elif typeshed_dir:
            overlay_engine.overlay_from_directory(Path(typeshed_dir), module_filter=module_filter)
        else:
            dirs = overlay_engine.auto_discover_typeshed_dirs()
            for d in dirs:
                overlay_engine.overlay_from_directory(d, module_filter=module_filter)

    # ========================================================================
    # MODULE & RUNTIME MEMBER INTROSPECTION
    # ========================================================================

    def _classify_module_origin(self, mod_name: str, mod: types.ModuleType) -> tuple[str, str | None]:
        if mod_name in sys.builtin_module_names:
            return ("builtin_c", None)
        spec = getattr(mod, "__spec__", None)
        origin = getattr(spec, "origin", None) if spec else getattr(mod, "__file__", None)
        if origin == "frozen" or (spec and getattr(spec, "loader", None) and "Frozen" in type(spec.loader).__name__):
            return ("frozen", None)
        if origin == "built-in":
            return ("builtin_c", None)
        if spec and spec.submodule_search_locations and origin is None:
            return ("namespace_pkg", None)
        if isinstance(origin, str):
            for ext in importlib.machinery.EXTENSION_SUFFIXES:
                if origin.endswith(ext):
                    return ("c_extension", origin)
            return ("pure_python", origin)
        return ("unknown", None)

    def harvest_module_by_name(self, dist_id: int, mod_name: str) -> int | None:
        """Imports and catalogs a module, its members, class hierarchies, and cross-module re-exports."""
        if mod_name in SIDE_EFFECT_STDLIB_MODULES:
            return None
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            return None

        origin_kind, phys_path = self._classify_module_origin(mod_name, mod)
        is_pkg = hasattr(mod, "__path__")
        container_kind = "package" if is_pkg else "module"
        short_name = mod_name.rsplit(".", 1)[-1]
        vis, is_hid = classify_identifier_visibility(short_name)

        raw_all = getattr(mod, "__all__", None)
        dunder_all_list = [str(x) for x in raw_all] if isinstance(raw_all, (list, tuple, set, frozenset)) else None
        dunder_all_set = set(dunder_all_list) if dunder_all_list is not None else None
        has_lazy_getattr = "__getattr__" in mod.__dict__

        parent_cid: int | None = None
        if "." in mod_name:
            parent_name = mod_name.rsplit(".", 1)[0]
            row = self.conn.execute(
                "SELECT container_id FROM containers WHERE dist_id = ? AND qualified_name = ? LIMIT 1",
                (dist_id, parent_name),
            ).fetchone()
            if row:
                parent_cid = int(row[0])

        mod_cid = self.register_container(
            dist_id=dist_id,
            parent_id=parent_cid,
            container_kind=container_kind,
            qualified_name=mod_name,
            short_name=short_name,
            requires_import=1,
            visibility=vis,
            is_hidden=is_hid,
            physical_path=phys_path,
            docstring=inspect.getdoc(mod),
            module_origin_kind=origin_kind,
            dunder_all=dunder_all_list,
            has_lazy_getattr=has_lazy_getattr,
        )

        for attr_name, obj in sorted(mod.__dict__.items()):
            if attr_name in IMPLICIT_MODULE_DUNDERS or attr_name in ("__all__", "__path__"):
                continue

            # 1. Foreign imported module -> record as alias, not child definition
            if isinstance(obj, types.ModuleType):
                target_mod_name = getattr(obj, "__name__", attr_name)
                in_all = 1 if (dunder_all_set and attr_name in dunder_all_set) else 0
                self.conn.execute(
                    """
                    INSERT INTO symbol_aliases (
                        source_container_id, exposed_name, target_module_name,
                        target_symbol_name, alias_kind, is_in_dunder_all
                    )
                    VALUES (?, ?, ?, '<module>', 'imported_module_ref', ?)
                    ON CONFLICT(source_container_id, exposed_name) DO NOTHING
                    """,
                    (mod_cid, attr_name, target_mod_name, in_all),
                )
                continue

            # 2. Check provenance: defined here vs. re-exported vs. imported dependency
            obj_mod = getattr(obj, "__module__", None)
            if isinstance(obj_mod, str) and obj_mod != mod_name:
                in_all = dunder_all_set is not None and attr_name in dunder_all_set
                is_backing_c_mod = (
                    obj_mod.startswith(f"_{mod_name.split('.')[0]}")
                    or obj_mod.startswith(f"{mod_name}._")
                    or (mod_name == "os" and obj_mod in ("posix", "nt", "genericpath", "posixpath", "ntpath"))
                )
                alias_kind = (
                    "c_accelerator_reexport"
                    if is_backing_c_mod
                    else ("explicit_all_reexport" if in_all else "imported_symbol_ref")
                )
                self.conn.execute(
                    """
                    INSERT INTO symbol_aliases (
                        source_container_id, exposed_name, target_module_name,
                        target_symbol_name, alias_kind, is_in_dunder_all
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_container_id, exposed_name) DO NOTHING
                    """,
                    (
                        mod_cid,
                        attr_name,
                        obj_mod,
                        getattr(obj, "__name__", attr_name),
                        alias_kind,
                        1 if in_all else 0,
                    ),
                )
                if not in_all and not is_backing_c_mod:
                    continue
                provenance = "re_exported"
            else:
                provenance = "defined_here"

            self._harvest_runtime_member(
                dist_id=dist_id,
                parent_cid=mod_cid,
                parent_qname=mod_name,
                module_name=mod_name,
                name=attr_name,
                obj=obj,
                dunder_all=dunder_all_set,
                requires_import=1,
                override_provenance=provenance,
            )

        return mod_cid

    # ========================================================================
    # RUNTIME MEMBER INTROSPECTION (CLASSES, CALLABLES, CONSTANTS)
    # ========================================================================

    def _harvest_runtime_member(
        self,
        *,
        dist_id: int,
        parent_cid: int,
        parent_qname: str,
        module_name: str,
        name: str,
        obj: Any,
        dunder_all: set[str] | None,
        requires_import: int,
        override_provenance: str,
        is_inside_class: bool = False,
    ) -> None:
        vis, is_hid = classify_identifier_visibility(name, dunder_all)
        qname = f"{parent_qname}.{name}"
        py_type_name = type(obj).__name__
        dunder_cat = DUNDER_CATEGORIES.get(name)

        # Case A: Class / Type / Exception
        if inspect.isclass(obj):
            is_exc = issubclass(obj, BaseException)
            sym_kind = "exception" if is_exc else "class"
            container_kind = "exception_class" if is_exc else "class"

            bases = [f"{b.__module__}.{b.__qualname__}" for b in getattr(obj, "__bases__", ())]
            mro = [f"{c.__module__}.{c.__qualname__}" for c in getattr(obj, "__mro__", ())]

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid, inspect.getdoc(obj)),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sid, py_type_name, 0 if hasattr(obj, "__dict__") and "__module__" in obj.__dict__ else 1, dunder_cat),
                )
                raw_sig, sig_src, ret_expr, params = extract_callable_signature(obj)
                self._insert_callable_and_params(
                    sid,
                    is_async=0,
                    is_generator=0,
                    is_static=0,
                    is_class_bound=1,
                    return_type_expr=name,
                    raw_signature=raw_sig,
                    signature_source=sig_src,
                    params=params,
                )

            if is_inside_class:
                return

            cls_cid = self.register_container(
                dist_id=dist_id,
                parent_id=parent_cid,
                container_kind=container_kind,
                qualified_name=qname,
                short_name=name,
                requires_import=requires_import,
                visibility=vis,
                is_hidden=is_hid,
                docstring=inspect.getdoc(obj),
                module_origin_kind="class_body",
                base_classes=bases,
                mro_list=mro,
                metaclass_name=type(obj).__name__,
            )

            for m_name, m_obj in sorted(obj.__dict__.items()):
                if m_name in ("__dict__", "__weakref__", "__doc__", "__module__"):
                    continue
                self._harvest_runtime_member(
                    dist_id=dist_id,
                    parent_cid=cls_cid,
                    parent_qname=qname,
                    module_name=module_name,
                    name=m_name,
                    obj=m_obj,
                    dunder_all=None,
                    requires_import=requires_import,
                    override_provenance="defined_here",
                    is_inside_class=True,
                )
            return

        # Case B: Properties and Descriptors
        if isinstance(obj, property) or py_type_name in ("getset_descriptor", "member_descriptor", "DynamicClassAttribute"):
            acc_mode = "read_only"
            if isinstance(obj, property) and obj.fset is not None:
                acc_mode = "read_write_delete" if obj.fdel is not None else "read_write"
            elif py_type_name in ("getset_descriptor", "member_descriptor"):
                acc_mode = "read_write"

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, 'property', ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, vis, override_provenance, is_hid, inspect.getdoc(obj)),
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
                    VALUES (?, NULL, ?, 0, 1, NULL, ?)
                    """,
                    (sid, py_type_name, acc_mode),
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, descriptor_kind, is_c_implemented, dunder_category)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sid, py_type_name, py_type_name, 0 if isinstance(obj, property) else 1, dunder_cat),
                )
            return

        # Unwrap staticmethod / classmethod
        is_static = 0 if is_inside_class else 1
        is_class_bound = 0
        descriptor_kind: str | None = None
        underlying_obj = obj
        if isinstance(obj, staticmethod):
            is_static = 1
            descriptor_kind = "staticmethod"
            underlying_obj = obj.__func__
        elif isinstance(obj, classmethod):
            is_static = 0
            is_class_bound = 1
            descriptor_kind = "classmethod"
            underlying_obj = obj.__func__
        elif py_type_name == "classmethod_descriptor":
            is_class_bound = 1
            descriptor_kind = "classmethod_descriptor"

        # Case C: Functions, Methods, and Callables
        if callable(underlying_obj) or py_type_name in (
            "method_descriptor",
            "wrapper_descriptor",
            "builtin_function_or_method",
            "classmethod_descriptor",
        ):
            sym_kind = "constructor" if name in ("__init__", "__new__") else ("method" if is_inside_class else "function")
            is_async = 1 if inspect.iscoroutinefunction(underlying_obj) or inspect.isasyncgenfunction(underlying_obj) else 0
            is_gen = 1 if inspect.isgeneratorfunction(underlying_obj) or inspect.isasyncgenfunction(underlying_obj) else 0
            code_obj = getattr(underlying_obj, "__code__", None)
            co_flags = getattr(code_obj, "co_flags", None)
            is_c_impl = 1 if code_obj is None else 0

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid, inspect.getdoc(underlying_obj)),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                raw_sig, sig_src, ret_expr, params = extract_callable_signature(underlying_obj)
                self._insert_callable_and_params(
                    sid,
                    is_async=is_async,
                    is_generator=is_gen,
                    is_static=is_static,
                    is_class_bound=is_class_bound,
                    return_type_expr=ret_expr,
                    raw_signature=raw_sig,
                    signature_source=sig_src,
                    params=params,
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (
                        symbol_id, py_runtime_type, descriptor_kind,
                        is_c_implemented, co_flags, dunder_category
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sid, py_type_name, descriptor_kind or py_type_name, is_c_impl, co_flags, dunder_cat),
                )
            return

        # Case D: Constants, Sentinels, and Variables
        is_const = 1 if (name.isupper() or name in ("True", "False", "None", "Ellipsis", "NotImplemented", "__debug__")) else 0
        is_mut = 0 if isinstance(obj, (int, float, str, bytes, tuple, frozenset, bool)) or obj is None else 1
        sym_kind = "constant" if is_const else "variable"

        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id
            """,
            (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid),
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
                VALUES (?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    py_type_name,
                    is_const,
                    is_mut,
                    safe_repr(obj),
                    "read_only" if is_const else "read_write",
                ),
            )
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                VALUES (?, ?, 1, ?)
                """,
                (sid, py_type_name, dunder_cat),
            )

    def _insert_callable_and_params(
        self,
        symbol_id: int,
        *,
        is_async: int,
        is_generator: int,
        is_static: int,
        is_class_bound: int,
        return_type_expr: str | None,
        raw_signature: str | None,
        signature_source: str,
        params: list[dict[str, Any]],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO callables (
                symbol_id, is_async, is_generator, is_static, is_class_bound,
                return_type_expr, raw_signature, signature_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO NOTHING
            """,
            (symbol_id, is_async, is_generator, is_static, is_class_bound, return_type_expr, raw_signature, signature_source),
        )
        for p in params:
            self.conn.execute(
                """
                INSERT INTO parameters (
                    callable_symbol_id, overload_id, ordinal, name, pass_kind,
                    type_expr, type_source, default_expr, is_optional
                )
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol_id,
                    p["ordinal"],
                    p["name"],
                    p["pass_kind"],
                    p["type_expr"],
                    p.get("type_source", "runtime_annotation" if p["type_expr"] is not None else None),
                    p["default_expr"],
                    p["is_optional"],
                ),
            )
