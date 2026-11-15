"""
Introspection, visibility classification, and signature extraction helpers.
Designed for 100% fidelity without crashing on Python 3.13 C-extension edge cases.
"""

from __future__ import annotations

import builtins
import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Categorization of system dunders for Python facet metadata
DUNDER_CATEGORIES: dict[str, str] = {
    "__new__": "lifecycle",
    "__init__": "lifecycle",
    "__del__": "lifecycle",
    "__init_subclass__": "meta",
    "__class_getitem__": "meta",
    "__mro_entries__": "meta",
    "__prepare__": "meta",
    "__repr__": "representation",
    "__str__": "representation",
    "__bytes__": "representation",
    "__format__": "representation",
    "__lt__": "comparison",
    "__le__": "comparison",
    "__eq__": "comparison",
    "__ne__": "comparison",
    "__gt__": "comparison",
    "__ge__": "comparison",
    "__hash__": "comparison",
    "__bool__": "comparison",
    "__getattr__": "attribute_access",
    "__getattribute__": "attribute_access",
    "__setattr__": "attribute_access",
    "__delattr__": "attribute_access",
    "__dir__": "attribute_access",
    "__get__": "descriptor",
    "__set__": "descriptor",
    "__delete__": "descriptor",
    "__set_name__": "descriptor",
    "__call__": "callable",
    "__len__": "container",
    "__length_hint__": "container",
    "__getitem__": "container",
    "__setitem__": "container",
    "__delitem__": "container",
    "__missing__": "container",
    "__iter__": "container",
    "__reversed__": "container",
    "__contains__": "container",
    "__enter__": "context_manager",
    "__exit__": "context_manager",
    "__await__": "async",
    "__aiter__": "async",
    "__anext__": "async",
    "__aenter__": "async",
    "__aexit__": "async",
    "__add__": "numeric",
    "__sub__": "numeric",
    "__mul__": "numeric",
    "__matmul__": "numeric",
    "__truediv__": "numeric",
    "__floordiv__": "numeric",
    "__mod__": "numeric",
    "__divmod__": "numeric",
    "__pow__": "numeric",
    "__lshift__": "numeric",
    "__rshift__": "numeric",
    "__and__": "numeric",
    "__xor__": "numeric",
    "__or__": "numeric",
    "__neg__": "numeric",
    "__pos__": "numeric",
    "__abs__": "numeric",
    "__invert__": "numeric",
    "__int__": "numeric",
    "__float__": "numeric",
    "__complex__": "numeric",
    "__index__": "numeric",
    "__round__": "numeric",
    "__trunc__": "numeric",
    "__floor__": "numeric",
    "__ceil__": "numeric",
}

# Implicit module-level dunders available in any Python file without import
IMPLICIT_MODULE_DUNDERS: tuple[tuple[str, str, str], ...] = (
    ("__name__", "str", "Module runtime name ('__main__' when executed directly, or dotted module name)."),
    ("__doc__", "str | None", "Module top-level docstring literal, or None if absent."),
    ("__package__", "str | None", "Parent package name used to resolve relative imports."),
    ("__loader__", "Loader | None", "The importlib Loader object that loaded this module."),
    ("__spec__", "ModuleSpec | None", "The importlib ModuleSpec describing module import state and origin."),
    ("__file__", "str | None", "Filesystem path from which module was loaded (absent on some C modules)."),
    ("__cached__", "str | None", "Filesystem path to compiled bytecode (.pyc) file."),
    ("__builtins__", "dict[str, Any] | module", "Reference to ambient builtins module or its dictionary."),
    ("__annotations__", "dict[str, Any]", "Module-level variable type annotations dictionary."),
)


def classify_identifier_visibility(name: str, dunder_all: set[str] | None = None) -> tuple[str, int]:
    """
    Classifies a symbol name into visibility tier and hidden flag:
    Returns (visibility_tier, is_hidden_int).
    Tiers: 'system_dunder', 'private_mangled', 'hidden_internal', 'exported_all', 'public_implicit'
    """
    if name.startswith("__") and name.endswith("__") and len(name) > 4:
        return ("system_dunder", 0)
    if name.startswith("__") and not name.endswith("__"):
        return ("private_mangled", 1)
    if name.startswith("_"):
        return ("hidden_internal", 1)
    if dunder_all is not None:
        if name in dunder_all:
            return ("exported_all", 0)
        return ("public_implicit", 0)
    return ("public_implicit", 0)


def safe_repr(val: Any, max_len: int = 160) -> str | None:
    """Produces a deterministic, bounded string representation for constants and variables."""
    try:
        if (
            isinstance(val, (int, float, bool, str, bytes, complex))
            or val is None
            or val is Ellipsis
            or val is NotImplemented
        ):
            r = repr(val)
            return r if len(r) <= max_len else r[: max_len - 3] + "..."
        return f"<{type(val).__name__}>"
    except Exception:
        return "<unrepresentable>"


def compute_file_sha256(path_str: str | None) -> str | None:
    """Computes SHA-256 hash of a file path, returning None if unreadable or absent."""
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def get_pure_builtins_without_site() -> set[str]:
    """Runs `python -S` in a clean subprocess to separate pure builtins from `site`-injected ones."""
    try:
        out = subprocess.check_output(
            [sys.executable, "-S", "-c", "import builtins, json; print(json.dumps(list(builtins.__dict__.keys())))"],
            text=True,
            timeout=5,
        )
        return set(json.loads(out.strip()))
    except Exception:
        # Fallback if subprocess fails
        site_injected = {"help", "quit", "exit", "copyright", "credits", "license"}
        return set(builtins.__dict__.keys()) - site_injected


def extract_callable_signature(obj: Any) -> tuple[str | None, str, str | None, list[dict[str, Any]]]:
    """
    Extracts (raw_signature, signature_source, return_type_expr, parameters_list)
    from Python functions, methods, C builtins, or docstrings.
    Resilient to Python 3.13 C-extension default parameter symbolic evaluation errors.
    """
    params_list: list[dict[str, Any]] = []
    try:
        sig = inspect.signature(obj)
        ret_expr = None
        if sig.return_annotation is not inspect.Signature.empty:
            ret_expr = (
                sig.return_annotation
                if isinstance(sig.return_annotation, str)
                else getattr(sig.return_annotation, "__name__", str(sig.return_annotation))
            )

        for idx, (_, param) in enumerate(sig.parameters.items()):
            kind_map = {
                inspect.Parameter.POSITIONAL_ONLY: "positional_only",
                inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
                inspect.Parameter.VAR_POSITIONAL: "var_positional",
                inspect.Parameter.KEYWORD_ONLY: "keyword_only",
                inspect.Parameter.VAR_KEYWORD: "var_keyword",
            }
            ann_str = None
            if param.annotation is not inspect.Parameter.empty:
                ann_str = (
                    param.annotation
                    if isinstance(param.annotation, str)
                    else getattr(param.annotation, "__name__", str(param.annotation))
                )
            def_str = None
            is_opt = 0
            if param.default is not inspect.Parameter.empty:
                def_str = safe_repr(param.default, 80)
                is_opt = 1
            elif param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                is_opt = 1

            params_list.append({
                "ordinal": idx,
                "name": param.name,
                "pass_kind": kind_map.get(param.kind, "positional_or_keyword"),
                "type_expr": ann_str,
                "default_expr": def_str,
                "is_optional": is_opt,
            })

        source = "text_signature" if getattr(obj, "__text_signature__", None) else "inspect_signature"
        return (str(sig), source, ret_expr, params_list)
    except (ValueError, TypeError, AttributeError, NameError, Exception):
        # Fallback 1: __text_signature__ on C builtins
        text_sig = getattr(obj, "__text_signature__", None)
        if isinstance(text_sig, str) and text_sig.strip():
            return (text_sig.strip(), "text_signature", None, [])

        # Fallback 2: First line of docstring if structured as `name(...)`
        doc = getattr(obj, "__doc__", None)
        if isinstance(doc, str) and doc.strip():
            first_line = doc.strip().splitlines()[0].strip()
            if "(" in first_line and ")" in first_line:
                return (first_line, "docstring_first_line", None, [])

        return (None, "unknown", None, [])
