#!/usr/bin/env python3
"""
UTSS Phase 3.3: Block & Function-Level AST Transpiler Engine
===========================================================
Recursively parses Python AST and lowers data structures, control flow (loops,
branching, function signatures, error handling, and resource scopes) into
idiomatic C#, Rust, TypeScript, C++, and Go code using empirical signatures
from `utss_universal_bridge.db`.
"""

from __future__ import annotations

import ast
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

TARGET_LANGUAGES: Tuple[str, ...] = ("csharp", "rust", "typescript", "cpp", "go")

PYTHON_TYPE_TO_CONCEPT: Dict[str, str] = {
    "int": "primitive.int64",
    "float": "primitive.float64",
    "str": "primitive.string_utf8",
    "bool": "primitive.bool",
    "bytes": "primitive.byte_sequence",
    "list": "collection.dynamic_array",
    "dict": "collection.hash_map",
    "set": "collection.hash_set",
    "Optional": "control_flow.option_maybe",
    "ValueError": "exception.argument_null",
    "TypeError": "exception.argument_null",
    "KeyError": "exception.key_not_found",
    "IndexError": "exception.index_out_of_bounds",
    "FileNotFoundError": "exception.io_error",
    "IOError": "exception.io_error",
    "Exception": "exception.io_error",
}

PYTHON_OP_TO_CANONICAL: Dict[Tuple[str, str], str] = {
    # dynamic_array
    ("collection.dynamic_array", "append"): "append",
    ("collection.dynamic_array", "pop"): "pop",
    ("collection.dynamic_array", "clear"): "clear",
    ("collection.dynamic_array", "len"): "len",
    ("collection.dynamic_array", "__contains__"): "contains",
    # hash_map
    ("collection.hash_map", "get"): "get",
    ("collection.hash_map", "clear"): "clear",
    ("collection.hash_map", "len"): "len",
    ("collection.hash_map", "__contains__"): "contains_key",
    # hash_set
    ("collection.hash_set", "add"): "add",
    ("collection.hash_set", "remove"): "remove",
    ("collection.hash_set", "discard"): "remove",
    ("collection.hash_set", "clear"): "clear",
    ("collection.hash_set", "len"): "len",
    ("collection.hash_set", "__contains__"): "contains",
    # fifo_queue
    ("collection.fifo_queue", "append"): "enqueue",
    ("collection.fifo_queue", "popleft"): "dequeue",
    ("collection.fifo_queue", "clear"): "clear",
    ("collection.fifo_queue", "len"): "len",
    # string_utf8
    ("primitive.string_utf8", "lower"): "to_lowercase",
    ("primitive.string_utf8", "upper"): "to_uppercase",
    ("primitive.string_utf8", "strip"): "trim",
    ("primitive.string_utf8", "startswith"): "starts_with",
    ("primitive.string_utf8", "endswith"): "ends_with",
    ("primitive.string_utf8", "replace"): "replace",
    ("primitive.string_utf8", "split"): "split",
    ("primitive.string_utf8", "len"): "len",
    ("primitive.string_utf8", "__contains__"): "contains",
    # file_handle
    ("io.file_handle", "read"): "read",
    ("io.file_handle", "write"): "write",
    ("io.file_handle", "flush"): "flush",
    ("io.file_handle", "close"): "close",
}


@dataclass
class ProvenanceRecord:
    construct: str
    concept_key: str
    target_language: str
    resolved_target: str
    verification_status: str
    catalog_container_id: Optional[int] = None
    catalog_symbol_id: Optional[int] = None
    catalog_signature: Optional[str] = None
    receiver_pass_kind: Optional[str] = None


@dataclass
class ResolvedType:
    concept_key: str
    target_language: str
    rendered_type: str
    memory_model: str
    nullability_model: str
    required_imports: List[str] = field(default_factory=list)
    provenance: List[ProvenanceRecord] = field(default_factory=list)


@dataclass
class TargetSynthesisOutput:
    language: str
    imports: List[str]
    statements: List[str]
    source_code: str
    provenance_trace: List[ProvenanceRecord]


class BridgeCatalogRepository:
    """Read-only caching repository over `utss_universal_bridge.db`."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._type_cache: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}
        self._op_cache: Dict[Tuple[str, str, str], Optional[Dict[str, Any]]] = {}
        self._proto_cache: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}
        self._concept_cache: Dict[str, Optional[int]] = {}

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Universal bridge database not found: {self.db_path}")
            self._conn = sqlite3.connect(f"file:{self.db_path.resolve()}?mode=ro", uri=True)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get_concept_id(self, concept_key: str) -> Optional[int]:
        if concept_key not in self._concept_cache:
            conn = self._get_conn()
            row = conn.execute("SELECT concept_id FROM universal_concepts WHERE concept_key = ? LIMIT 1;", (concept_key,)).fetchone()
            self._concept_cache[concept_key] = row[0] if row else None
        return self._concept_cache[concept_key]

    def get_type_mapping(self, concept_key: str, language: str) -> Optional[Dict[str, Any]]:
        cache_key = (concept_key, language)
        if cache_key not in self._type_cache:
            cid = self.get_concept_id(concept_key)
            if cid is None:
                self._type_cache[cache_key] = None
            else:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT * FROM universal_type_mappings WHERE concept_id = ? AND language = ? LIMIT 1;",
                    (cid, language),
                ).fetchone()
                self._type_cache[cache_key] = dict(row) if row else None
        return self._type_cache[cache_key]

    def get_operation_mapping(self, concept_key: str, canonical_op: str, language: str) -> Optional[Dict[str, Any]]:
        cache_key = (concept_key, canonical_op, language)
        if cache_key not in self._op_cache:
            cid = self.get_concept_id(concept_key)
            if cid is None:
                self._op_cache[cache_key] = None
            else:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT * FROM universal_operation_mappings WHERE concept_id = ? AND canonical_op = ? AND language = ? LIMIT 1;",
                    (cid, canonical_op, language),
                ).fetchone()
                self._op_cache[cache_key] = dict(row) if row else None
        return self._op_cache[cache_key]

    def get_protocol_mapping(self, concept_key: str, language: str) -> Optional[Dict[str, Any]]:
        cache_key = (concept_key, language)
        if cache_key not in self._proto_cache:
            cid = self.get_concept_id(concept_key)
            if cid is None:
                self._proto_cache[cache_key] = None
            else:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT * FROM universal_protocol_mappings WHERE concept_id = ? AND language = ? LIMIT 1;",
                    (cid, language),
                ).fetchone()
                self._proto_cache[cache_key] = dict(row) if row else None
        return self._proto_cache[cache_key]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class BridgeTranspiler:
    """Translates Python AST into C#, Rust, TypeScript, C++, and Go."""

    def __init__(self, repo: BridgeCatalogRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------------
    # Stage 1: Recursive Type Resolution
    # ------------------------------------------------------------------------
    def resolve_type_node(self, node: Optional[ast.AST], target_lang: str) -> ResolvedType:
        if node is None:
            return self._fallback_type(target_lang, "void")

        # Identifier (`int`, `str`, `list`, `dict`)
        if isinstance(node, ast.Name):
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(node.id, "primitive.int64")
            return self._instantiate_type_template(concept_key, [], target_lang, raw_name=node.id)

        # Attribute (`io.BytesIO`)
        if isinstance(node, ast.Attribute):
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(node.attr, "primitive.int64")
            return self._instantiate_type_template(concept_key, [], target_lang, raw_name=node.attr)

        # PEP 604 Union (`T | None`) -> control_flow.option_maybe
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_is_none = isinstance(node.left, ast.Constant) and node.left.value is None
            right_is_none = isinstance(node.right, ast.Constant) and node.right.value is None
            if left_is_none or right_is_none:
                inner_node = node.right if left_is_none else node.left
                inner_res = self.resolve_type_node(inner_node, target_lang)
                return self._instantiate_type_template("control_flow.option_maybe", [inner_res], target_lang, raw_name="Optional")

        # Generic subscript (`list[int]`, `dict[str, int]`)
        if isinstance(node, ast.Subscript):
            base_name = node.value.id if isinstance(node.value, ast.Name) else "list"
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(base_name, "collection.dynamic_array")

            if isinstance(node.slice, ast.Tuple):
                arg_nodes = list(node.slice.elts)
            else:
                arg_nodes = [node.slice]

            resolved_args = [self.resolve_type_node(arg, target_lang) for arg in arg_nodes]
            return self._instantiate_type_template(concept_key, resolved_args, target_lang, raw_name=base_name)

        return self._fallback_type(target_lang, "var")

    def _fallback_type(self, lang: str, label: str) -> ResolvedType:
        type_str = {
            "csharp": "var",
            "rust": "auto",
            "typescript": "any",
            "cpp": "auto",
            "go": "any",
        }.get(lang, "var")
        return ResolvedType(
            concept_key="primitive.int64",
            target_language=lang,
            rendered_type=type_str,
            memory_model="unknown",
            nullability_model="unknown",
        )

    def _instantiate_type_template(
        self,
        concept_key: str,
        type_args: List[ResolvedType],
        target_lang: str,
        raw_name: str,
    ) -> ResolvedType:
        mapping = self.repo.get_type_mapping(concept_key, target_lang)
        if not mapping:
            return ResolvedType(
                concept_key=concept_key,
                target_language=target_lang,
                rendered_type=raw_name,
                memory_model="unknown",
                nullability_model="unknown",
            )

        template: str = mapping["type_syntax_template"]
        rendered = template
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []

        if mapping.get("required_import"):
            imports.append(mapping["required_import"])

        # Map {T} or {K}, {V} placeholders
        if len(type_args) == 1:
            rendered = rendered.replace("{T}", type_args[0].rendered_type)
            rendered = rendered.replace("{T0}", type_args[0].rendered_type)
            imports.extend(type_args[0].required_imports)
            prov.extend(type_args[0].provenance)
        elif len(type_args) >= 2:
            rendered = rendered.replace("{K}", type_args[0].rendered_type)
            rendered = rendered.replace("{V}", type_args[1].rendered_type)
            rendered = rendered.replace("{T0}", type_args[0].rendered_type)
            rendered = rendered.replace("{T1}", type_args[1].rendered_type)
            for arg in type_args:
                imports.extend(arg.required_imports)
                prov.extend(arg.provenance)

        # Fallback generic default
        rendered = rendered.replace("{T}", "long").replace("{K}", "string").replace("{V}", "long")

        prov.append(
            ProvenanceRecord(
                construct=f"type:{raw_name}",
                concept_key=concept_key,
                target_language=target_lang,
                resolved_target=mapping.get("resolved_qualified_name") or mapping.get("target_qualified_name") or raw_name,
                verification_status=mapping.get("verification_status", "verified"),
                catalog_container_id=mapping.get("catalog_container_id"),
                catalog_symbol_id=mapping.get("catalog_symbol_id"),
            )
        )

        return ResolvedType(
            concept_key=concept_key,
            target_language=target_lang,
            rendered_type=rendered,
            memory_model=mapping.get("memory_model", "value"),
            nullability_model=mapping.get("nullability_model", "non_nullable"),
            required_imports=imports,
            provenance=prov,
        )

    # ------------------------------------------------------------------------
    # Stage 2: Module, Block & Statement Lowering
    # ------------------------------------------------------------------------
    def transpile_module(self, python_code: str, target_lang: str) -> TargetSynthesisOutput:
        tree = ast.parse(python_code)
        env_types: Dict[str, ResolvedType] = {}
        imports: List[str] = []
        statements: List[str] = []
        provenance: List[ProvenanceRecord] = []

        for stmt in tree.body:
            lines, stmt_imports, stmt_prov = self._lower_stmt(stmt, target_lang, env_types)
            statements.extend(lines)
            imports.extend(stmt_imports)
            provenance.extend(stmt_prov)

        dedup_imports = list(dict.fromkeys(imp for imp in imports if imp))
        header = self._format_imports(dedup_imports, target_lang)
        body_str = "\n".join(statements)
        full_code = f"{header}\n\n{body_str}".strip() if header else body_str

        return TargetSynthesisOutput(
            language=target_lang,
            imports=dedup_imports,
            statements=statements,
            source_code=full_code,
            provenance_trace=provenance,
        )

    def _lower_stmt(
        self,
        stmt: ast.stmt,
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []

        # 1. Annotated Variable Declaration (`items: list[int] = []`)
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            var_name = stmt.target.id
            res_type = self.resolve_type_node(stmt.annotation, lang)
            env_types[var_name] = res_type
            imports.extend(res_type.required_imports)
            prov.extend(res_type.provenance)

            init_expr = self._render_initializer(res_type, stmt.value, lang, env_types)
            decl_line = self._format_var_decl(var_name, res_type.rendered_type, init_expr, lang)
            return [decl_line], imports, prov

        # 2. Assignment (`target = value` or `receiver[key] = value`)
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]

            # Subscript assignment: `scores["alice"] = 100`
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                receiver = target.value.id
                key_expr = self._render_expr(target.slice, lang, env_types, imports, prov)
                val_expr = self._render_expr(stmt.value, lang, env_types, imports, prov)

                if lang in ("csharp", "typescript", "cpp", "go"):
                    line = f"{receiver}[{key_expr}] = {val_expr};" if lang != "go" else f"{receiver}[{key_expr}] = {val_expr}"
                else:  # rust
                    line = f"{receiver}.insert({key_expr}, {val_expr});"
                return [line], imports, prov

            # Attribute assignment: `self.count = self.count + 1`
            if isinstance(target, ast.Attribute):
                target_str = self._render_expr(target, lang, env_types, imports, prov)
                rhs = self._render_expr(stmt.value, lang, env_types, imports, prov)
                return [self._terminate_stmt(f"{target_str} = {rhs}", lang)], imports, prov

            # Untyped variable assignment: `n = len(items)`
            if isinstance(target, ast.Name):
                var_name = target.id
                rhs = self._render_expr(stmt.value, lang, env_types, imports, prov)
                return [self._format_untyped_assign(var_name, rhs, lang)], imports, prov

        # 3. Standalone Expression Statement (`items.append(42)`)
        if isinstance(stmt, ast.Expr):
            expr_str = self._render_expr(stmt.value, lang, env_types, imports, prov)
            return [self._terminate_stmt(expr_str, lang)], imports, prov

        # 4. For Loop (`for item in items:`)
        if isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name):
            var_name = stmt.target.id
            iter_expr = self._render_expr(stmt.iter, lang, env_types, imports, prov)

            body_lines: List[str] = []
            for child in stmt.body:
                c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                body_lines.extend(c_lines)
                imports.extend(c_imp)
                prov.extend(c_prov)

            indented_body = [f"    {line}" for line in body_lines]

            if lang == "csharp":
                return [f"foreach (var {var_name} in {iter_expr})", "{"] + indented_body + ["}"], imports, prov
            if lang == "rust":
                return [f"for {var_name} in {iter_expr} {{"] + indented_body + ["}"], imports, prov
            if lang == "typescript":
                return [f"for (const {var_name} of {iter_expr}) {{"] + indented_body + ["}"], imports, prov
            if lang == "cpp":
                return [f"for (const auto& {var_name} : {iter_expr}) {{"] + indented_body + ["}"], imports, prov
            # Go
            return [f"for _, {var_name} := range {iter_expr} {{"] + indented_body + ["}"], imports, prov

        # 5. While Loop (`while cond:`)
        if isinstance(stmt, ast.While):
            cond_expr = self._render_expr(stmt.test, lang, env_types, imports, prov)
            body_lines = []
            for child in stmt.body:
                c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                body_lines.extend(c_lines)
                imports.extend(c_imp)
                prov.extend(c_prov)
            indented_body = [f"    {line}" for line in body_lines]

            if lang == "go":
                return [f"for {cond_expr} {{"] + indented_body + ["}"], imports, prov
            if lang in ("csharp", "typescript", "cpp"):
                return [f"while ({cond_expr}) {{"] + indented_body + ["}"], imports, prov
            return [f"while {cond_expr} {{"] + indented_body + ["}"], imports, prov

        # 6. If / Else Branching
        if isinstance(stmt, ast.If):
            cond_expr = self._render_expr(stmt.test, lang, env_types, imports, prov)
            body_lines = []
            for child in stmt.body:
                c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                body_lines.extend(c_lines)
                imports.extend(c_imp)
                prov.extend(c_prov)
            indented_body = [f"    {line}" for line in body_lines]

            else_lines = []
            for child in stmt.orelse:
                c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                else_lines.extend(c_lines)
                imports.extend(c_imp)
                prov.extend(c_prov)

            header_cond = f"if ({cond_expr}) {{" if lang in ("csharp", "typescript", "cpp") else f"if {cond_expr} {{"
            out_lines = [header_cond] + indented_body + ["}"]

            if else_lines:
                out_lines += ["else {"] + [f"    {line}" for line in else_lines] + ["}"]
            return out_lines, imports, prov

        # 7. Function Definition (`def foo(x: int) -> int:`)
        if isinstance(stmt, ast.FunctionDef):
            fn_name = stmt.name
            ret_type = self.resolve_type_node(stmt.returns, lang)
            imports.extend(ret_type.required_imports)
            prov.extend(ret_type.provenance)

            # Lower parameters
            params: List[str] = []
            for arg in stmt.args.args:
                p_name = arg.arg
                p_type = self.resolve_type_node(arg.annotation, lang)
                env_types[p_name] = p_type
                imports.extend(p_type.required_imports)
                prov.extend(p_type.provenance)

                if lang == "go":
                    params.append(f"{p_name} {p_type.rendered_type}")
                elif lang == "typescript":
                    params.append(f"{p_name}: {p_type.rendered_type}")
                else:  # csharp, cpp, rust
                    if lang == "rust":
                        params.append(f"{p_name}: {p_type.rendered_type}")
                    else:
                        params.append(f"{p_type.rendered_type} {p_name}")

            body_lines = []
            for child in stmt.body:
                c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                body_lines.extend(c_lines)
                imports.extend(c_imp)
                prov.extend(c_prov)
            indented_body = [f"    {line}" for line in body_lines]

            params_str = ", ".join(params)
            ret_str = ret_type.rendered_type

            if lang == "csharp":
                cs_name = self._to_pascal(fn_name) if fn_name else "Method"
                sig = f"public static {ret_str} {cs_name}({params_str}) {{"
            elif lang == "rust":
                sig = f"pub fn {fn_name}({params_str}) -> {ret_str} {{"
            elif lang == "typescript":
                sig = f"export function {fn_name}({params_str}): {ret_str} {{"
            elif lang == "cpp":
                sig = f"{ret_str} {fn_name}({params_str}) {{"
            else:  # go
                go_name = self._to_pascal(fn_name) if fn_name else "Func"
                sig = f"func {go_name}({params_str}) {ret_str} {{"

            return [sig] + indented_body + ["}"], imports, prov

        # 8. Class Definition (`class User: ...`)
        if isinstance(stmt, ast.ClassDef):
            return self._lower_class(stmt, lang, env_types)

        # 9. Return Statement (`return val`)
        if isinstance(stmt, ast.Return):
            val_expr = self._render_expr(stmt.value, lang, env_types, imports, prov) if stmt.value else ""
            line = f"return {val_expr}" if val_expr else "return"
            return [self._terminate_stmt(line, lang)], imports, prov

        # 10. Context Manager (`with open("file.txt") as f:`)
        if isinstance(stmt, ast.With) and stmt.items:
            return self._lower_with_protocol(stmt, lang, env_types)

        # 11. Exception Raising (`raise ValueError("msg")`)
        if isinstance(stmt, ast.Raise) and stmt.exc is not None:
            return self._lower_raise_exception(stmt.exc, lang, env_types)

        # 12. Try / Except / Finally (`try: ... except: ... finally: ...`)
        if isinstance(stmt, ast.Try):
            return self._lower_try(stmt, lang, env_types)

        if isinstance(stmt, ast.Pass):
            return [], imports, prov
        if isinstance(stmt, ast.Break):
            return [self._terminate_stmt("break", lang)], imports, prov
        if isinstance(stmt, ast.Continue):
            return [self._terminate_stmt("continue", lang)], imports, prov

        return [f"// [unhandled AST construct: {type(stmt).__name__}]"], imports, prov

    # ------------------------------------------------------------------------
    # Stage 3: Expression Lowering
    # ------------------------------------------------------------------------
    def _render_expr(
        self,
        expr: Optional[ast.AST],
        lang: str,
        env_types: Dict[str, ResolvedType],
        imports: List[str],
        prov: List[ProvenanceRecord],
    ) -> str:
        if expr is None:
            return ""

        # Literals
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, str):
                if lang == "rust":
                    return f'String::from("{expr.value}")'
                return f'"{expr.value}"'
            if isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            if expr.value is None:
                return {"csharp": "null", "rust": "None", "typescript": "null", "cpp": "nullptr", "go": "nil"}.get(lang, "null")
            return str(expr.value)

        # Identifiers
        if isinstance(expr, ast.Name):
            return expr.id

        # Attribute Access (`self.field` / `obj.field`)
        if isinstance(expr, ast.Attribute):
            val_str = self._render_expr(expr.value, lang, env_types, imports, prov)
            attr = expr.attr
            if val_str == "self":
                if lang == "csharp":
                    return f"this.{self._to_pascal(attr)}"
                if lang == "typescript":
                    return f"this.{attr}"
                if lang == "cpp":
                    return f"this->{attr}"
                if lang == "rust":
                    return f"self.{attr}"
                return f"self.{self._to_pascal(attr)}"
            if lang in ("csharp", "go"):
                return f"{val_str}.{self._to_pascal(attr)}"
            return f"{val_str}.{attr}"

        # Binary Operations (`a + b`, `a * b`)
        if isinstance(expr, ast.BinOp):
            left = self._render_expr(expr.left, lang, env_types, imports, prov)
            right = self._render_expr(expr.right, lang, env_types, imports, prov)
            op_sym = {
                ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%"
            }.get(type(expr.op), "+")
            return f"{left} {op_sym} {right}"

        # Boolean Operators (`a and b`, `a or b`)
        if isinstance(expr, ast.BoolOp):
            vals = [self._render_expr(v, lang, env_types, imports, prov) for v in expr.values]
            op_sym = " && " if isinstance(expr.op, ast.And) else " || "
            return op_sym.join(vals)

        # Comparison (`a > b`, `a in items`)
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1:
            left = self._render_expr(expr.left, lang, env_types, imports, prov)
            comp = self._render_expr(expr.comparators[0], lang, env_types, imports, prov)
            op = expr.ops[0]

            if isinstance(op, ast.In):
                # Membership `x in items`
                rec_type = env_types.get(comp)
                ckey = rec_type.concept_key if rec_type else "collection.dynamic_array"
                canon_op = "contains_key" if "map" in ckey else "contains"
                return self._lower_operation(ckey, canon_op, comp, [left], lang, prov)

            op_sym = {
                ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="
            }.get(type(op), "==")
            return f"{left} {op_sym} {comp}"

        # Function Calls & Builtins
        if isinstance(expr, ast.Call):
            args = [self._render_expr(a, lang, env_types, imports, prov) for a in expr.args]

            # Constructor instantiation for user-defined classes
            if isinstance(expr.func, ast.Name) and expr.func.id in env_types and env_types[expr.func.id].concept_key == "user_type":
                c_name = env_types[expr.func.id].rendered_type
                joined_args = ", ".join(args)
                if lang == "csharp":
                    return f"new {c_name}({joined_args})"
                if lang == "rust":
                    return f"{c_name}::new({joined_args})"
                if lang == "typescript":
                    return f"new {c_name}({joined_args})"
                if lang == "cpp":
                    return f"{c_name}{{{joined_args}}}"
                if lang == "go":
                    return f"New{c_name}({joined_args})"

            # `len(items)` -> canonical_op 'len'
            if isinstance(expr.func, ast.Name) and expr.func.id == "len" and len(args) == 1:
                rec_name = args[0]
                rec_type = env_types.get(rec_name)
                ckey = rec_type.concept_key if rec_type else "collection.dynamic_array"
                return self._lower_operation(ckey, "len", rec_name, [], lang, prov, imports)

            # Method calls: `receiver.method(arg0, ...)`
            if isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name):
                rec_name = expr.func.value.id
                method_name = expr.func.attr
                rec_type = env_types.get(rec_name)
                ckey = rec_type.concept_key if rec_type else "collection.dynamic_array"
                canon_op = PYTHON_OP_TO_CANONICAL.get((ckey, method_name), method_name)
                return self._lower_operation(ckey, canon_op, rec_name, args, lang, prov, imports)

            # Fallback direct call
            func_name = ast.unparse(expr.func)
            return f"{func_name}({', '.join(args)})"

        return ast.unparse(expr)

    def _lower_operation(
        self,
        concept_key: str,
        canonical_op: str,
        receiver_expr: str,
        arg_exprs: List[str],
        lang: str,
        prov: List[ProvenanceRecord],
        imports: Optional[List[str]] = None,
    ) -> str:
        op_map = self.repo.get_operation_mapping(concept_key, canonical_op, lang)
        if not op_map:
            # Fallback syntax
            if canonical_op == "len":
                if lang == "csharp": return f"{receiver_expr}.Count"
                if lang == "rust": return f"{receiver_expr}.len()"
                if lang == "typescript": return f"{receiver_expr}.length"
                if lang == "cpp": return f"{receiver_expr}.size()"
                if lang == "go": return f"len({receiver_expr})"
            joined = ", ".join(arg_exprs)
            return f"{receiver_expr}.{canonical_op}({joined})"

        rendered = op_map["call_syntax_template"]
        rendered = rendered.replace("{receiver}", receiver_expr).replace("{self}", receiver_expr)
        if arg_exprs:
            rendered = rendered.replace("{item}", arg_exprs[0])
            rendered = rendered.replace("{key}", arg_exprs[0])
            rendered = rendered.replace("{val}", arg_exprs[1] if len(arg_exprs) > 1 else arg_exprs[0])
            for idx, a in enumerate(arg_exprs):
                rendered = rendered.replace(f"{{arg{idx}}}", a)

        if imports is not None:
            if lang == "go" and "strings." in rendered and "strings" not in imports:
                imports.append("strings")
            if lang == "csharp" and "hash_set" in concept_key and "System.Collections.Generic" not in imports:
                imports.append("System.Collections.Generic")

        prov.append(
            ProvenanceRecord(
                construct=f"op:{concept_key}.{canonical_op}",
                concept_key=concept_key,
                target_language=lang,
                resolved_target=op_map.get("verified_qualified_name") or op_map.get("target_symbol_name") or canonical_op,
                verification_status=op_map.get("verification_status", "verified"),
                catalog_symbol_id=op_map.get("catalog_symbol_id"),
                catalog_signature=op_map.get("verified_raw_signature"),
                receiver_pass_kind=op_map.get("receiver_pass_kind"),
            )
        )
        return rendered

    # ------------------------------------------------------------------------
    # Stage 3.5: Class & Method Lowering
    # ------------------------------------------------------------------------
    @staticmethod
    def _to_pascal(s: str) -> str:
        return "".join(p.capitalize() for p in s.split("_") if p)

    def _lower_class(
        self,
        stmt: ast.ClassDef,
        lang: str,
        env_types: Dict[str, ResolvedType]
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []
        class_name = stmt.name
        pascal_name = self._to_pascal(class_name)

        # 1. Collect fields and methods
        fields: List[Tuple[str, ResolvedType]] = []
        methods: List[ast.FunctionDef] = []

        for item in stmt.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                f_name = item.target.id
                f_type = self.resolve_type_node(item.annotation, lang)
                fields.append((f_name, f_type))
                imports.extend(f_type.required_imports)
                prov.extend(f_type.provenance)
            elif isinstance(item, ast.FunctionDef):
                methods.append(item)

        # Register class type in environment
        env_types[class_name] = ResolvedType(
            concept_key="user_type",
            target_language=lang,
            rendered_type=pascal_name,
            memory_model="ref_gc" if lang in ("csharp", "typescript", "go") else "owned_heap",
            nullability_model="nullable_ref" if lang in ("csharp", "typescript", "go") else "value_default"
        )

        lines: List[str] = []

        if lang == "csharp":
            lines.append(f"public class {pascal_name}")
            lines.append("{")
            for f_name, f_type in fields:
                p_name = self._to_pascal(f_name)
                lines.append(f"    public {f_type.rendered_type} {p_name} {{ get; set; }}")

            if fields:
                ctor_params = ", ".join(f"{f_type.rendered_type} {f_name}" for f_name, f_type in fields)
                lines.append("")
                lines.append(f"    public {pascal_name}({ctor_params})")
                lines.append("    {")
                for f_name, _ in fields:
                    p_name = self._to_pascal(f_name)
                    lines.append(f"        this.{p_name} = {f_name};")
                lines.append("    }")

            for m in methods:
                m_lines, m_imp, m_prov = self._lower_class_method(m, lang, env_types, pascal_name)
                imports.extend(m_imp)
                prov.extend(m_prov)
                lines.append("")
                lines.extend([f"    {l}" for l in m_lines])

            lines.append("}")

        elif lang == "rust":
            lines.append(f"pub struct {pascal_name} {{")
            for f_name, f_type in fields:
                lines.append(f"    pub {f_name}: {f_type.rendered_type},")
            lines.append("}")
            lines.append("")
            lines.append(f"impl {pascal_name} {{")
            if fields:
                ctor_params = ", ".join(f"{f_name}: {f_type.rendered_type}" for f_name, f_type in fields)
                ctor_inits = ", ".join(f_name for f_name, _ in fields)
                lines.append(f"    pub fn new({ctor_params}) -> Self {{")
                lines.append(f"        Self {{ {ctor_inits} }}")
                lines.append("    }")

            for m in methods:
                m_lines, m_imp, m_prov = self._lower_class_method(m, lang, env_types, pascal_name)
                imports.extend(m_imp)
                prov.extend(m_prov)
                lines.append("")
                lines.extend([f"    {l}" for l in m_lines])

            lines.append("}")

        elif lang == "typescript":
            lines.append(f"export class {pascal_name} {{")
            for f_name, f_type in fields:
                lines.append(f"    {f_name}: {f_type.rendered_type};")

            if fields:
                ctor_params = ", ".join(f"{f_name}: {f_type.rendered_type}" for f_name, f_type in fields)
                lines.append("")
                lines.append(f"    constructor({ctor_params}) {{")
                for f_name, _ in fields:
                    lines.append(f"        this.{f_name} = {f_name};")
                lines.append("    }")

            for m in methods:
                m_lines, m_imp, m_prov = self._lower_class_method(m, lang, env_types, pascal_name)
                imports.extend(m_imp)
                prov.extend(m_prov)
                lines.append("")
                lines.extend([f"    {l}" for l in m_lines])

            lines.append("}")

        elif lang == "cpp":
            lines.append(f"struct {pascal_name} {{")
            for f_name, f_type in fields:
                lines.append(f"    {f_type.rendered_type} {f_name};")

            if fields:
                ctor_params = ", ".join(f"{f_type.rendered_type} {f_name}" for f_name, f_type in fields)
                init_list = ", ".join(f"{f_name}({f_name})" for f_name, _ in fields)
                lines.append("")
                lines.append(f"    {pascal_name}({ctor_params}) : {init_list} {{}}")

            for m in methods:
                m_lines, m_imp, m_prov = self._lower_class_method(m, lang, env_types, pascal_name)
                imports.extend(m_imp)
                prov.extend(m_prov)
                lines.append("")
                lines.extend([f"    {l}" for l in m_lines])

            lines.append("};")

        else:  # go
            lines.append(f"type {pascal_name} struct {{")
            for f_name, f_type in fields:
                p_name = self._to_pascal(f_name)
                lines.append(f"    {p_name} {f_type.rendered_type}")
            lines.append("}")

            if fields:
                ctor_params = ", ".join(f"{f_name} {f_type.rendered_type}" for f_name, f_type in fields)
                lines.append("")
                lines.append(f"func New{pascal_name}({ctor_params}) *{pascal_name} {{")
                lines.append(f"    return &{pascal_name}{{")
                for f_name, _ in fields:
                    p_name = self._to_pascal(f_name)
                    lines.append(f"        {p_name}: {f_name},")
                lines.append("    }")
                lines.append("}")

            for m in methods:
                m_lines, m_imp, m_prov = self._lower_class_method(m, lang, env_types, pascal_name)
                imports.extend(m_imp)
                prov.extend(m_prov)
                lines.append("")
                lines.extend(m_lines)

        prov.append(ProvenanceRecord(
            construct="class",
            concept_key="user_type",
            target_language=lang,
            resolved_target=pascal_name,
            verification_status="verified_ast"
        ))

        return lines, imports, prov

    def _lower_class_method(
        self,
        stmt: ast.FunctionDef,
        lang: str,
        env_types: Dict[str, ResolvedType],
        class_name: str
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []
        fn_name = stmt.name
        ret_type = self.resolve_type_node(stmt.returns, lang)
        imports.extend(ret_type.required_imports)
        prov.extend(ret_type.provenance)

        method_args = [arg for arg in stmt.args.args if arg.arg != "self"]
        params: List[str] = []

        local_env = dict(env_types)
        for arg in method_args:
            p_name = arg.arg
            p_type = self.resolve_type_node(arg.annotation, lang)
            local_env[p_name] = p_type
            imports.extend(p_type.required_imports)
            prov.extend(p_type.provenance)

            if lang == "go":
                params.append(f"{p_name} {p_type.rendered_type}")
            elif lang == "typescript":
                params.append(f"{p_name}: {p_type.rendered_type}")
            elif lang == "rust":
                params.append(f"{p_name}: {p_type.rendered_type}")
            else:  # csharp, cpp
                params.append(f"{p_type.rendered_type} {p_name}")

        body_lines: List[str] = []
        for child in stmt.body:
            c_lines, c_imp, c_prov = self._lower_stmt(child, lang, local_env)
            body_lines.extend(c_lines)
            imports.extend(c_imp)
            prov.extend(c_prov)

        indented_body = [f"    {line}" for line in body_lines]
        ret_str = ret_type.rendered_type

        if lang == "csharp":
            cs_name = self._to_pascal(fn_name)
            params_str = ", ".join(params)
            sig = f"public {ret_str} {cs_name}({params_str}) {{"
            return [sig] + indented_body + ["}"], imports, prov

        if lang == "rust":
            rust_params = ["&mut self"] + params if params else ["&mut self"]
            params_str = ", ".join(rust_params)
            sig = f"pub fn {fn_name}({params_str}) -> {ret_str} {{"
            return [sig] + indented_body + ["}"], imports, prov

        if lang == "typescript":
            params_str = ", ".join(params)
            sig = f"public {fn_name}({params_str}): {ret_str} {{"
            return [sig] + indented_body + ["}"], imports, prov

        if lang == "cpp":
            params_str = ", ".join(params)
            sig = f"{ret_str} {fn_name}({params_str}) {{"
            return [sig] + indented_body + ["}"], imports, prov

        # Go receiver method: func (self *User) Method(params) ret
        go_name = self._to_pascal(fn_name)
        params_str = ", ".join(params)
        sig = f"func (self *{class_name}) {go_name}({params_str}) {ret_str} {{"
        return [sig] + indented_body + ["}"], imports, prov

    # ------------------------------------------------------------------------
    # Stage 4: Context Manager & Exception Lowering
    # ------------------------------------------------------------------------
    def _lower_with_protocol(
        self,
        stmt: ast.With,
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []

        item = stmt.items[0]
        handle_name = item.optional_vars.id if isinstance(item.optional_vars, ast.Name) else "stream"
        file_type = self._instantiate_type_template("io.file_handle", [], lang, raw_name="FileHandle")
        env_types[handle_name] = file_type
        imports.extend(file_type.required_imports)
        prov.extend(file_type.provenance)

        path_arg = '"data.txt"'
        if isinstance(item.context_expr, ast.Call) and item.context_expr.args:
            first_arg = item.context_expr.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                path_arg = f'"{first_arg.value}"'

        body_lines: List[str] = []
        for child in stmt.body:
            c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
            body_lines.extend(c_lines)
            imports.extend(c_imp)
            prov.extend(c_prov)
        indented_body = [f"    {line}" for line in body_lines]

        if lang == "csharp":
            imports.append("System.IO")
            return [f"using (var {handle_name} = File.OpenRead({path_arg}))", "{"] + indented_body + ["}"], imports, prov
        if lang == "rust":
            imports.append("std::fs::File")
            return [f"{{ // RAII Drop scope (core::ops::Drop)", f"    let mut {handle_name} = std::fs::File::open({path_arg})?;"] + indented_body + ["}"], imports, prov
        if lang == "go":
            imports.append("os")
            return [f"{handle_name}, err := os.Open({path_arg})", "if err != nil { return err }", f"defer {handle_name}.Close()"] + body_lines, imports, prov
        if lang == "cpp":
            imports.append("<fstream>")
            return [f"{{ // RAII destructor scope", f"    std::ifstream {handle_name}({path_arg});"] + indented_body + ["}"], imports, prov
        # TypeScript
        return [f"using {handle_name} = openFile({path_arg});"] + body_lines, imports, prov

    def _lower_raise_exception(
        self,
        exc_node: ast.AST,
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        exc_name = "ValueError"
        msg_arg = '"error"'
        if isinstance(exc_node, ast.Call) and isinstance(exc_node.func, ast.Name):
            exc_name = exc_node.func.id
            if exc_node.args and isinstance(exc_node.args[0], ast.Constant):
                msg_arg = f'"{exc_node.args[0].value}"'
        elif isinstance(exc_node, ast.Name):
            exc_name = exc_node.id

        concept_key = PYTHON_TYPE_TO_CONCEPT.get(exc_name, "exception.argument_null")
        res_exc = self._instantiate_type_template(concept_key, [], lang, raw_name=exc_name)

        if lang == "csharp":
            line = f"throw new {res_exc.rendered_type}({msg_arg});"
        elif lang == "rust":
            line = f"return Err({res_exc.rendered_type}::from({msg_arg}));"
        elif lang == "typescript":
            line = f"throw new {res_exc.rendered_type}({msg_arg});"
        elif lang == "cpp":
            imports = ["<stdexcept>"]
            line = f"throw {res_exc.rendered_type}({msg_arg});"
            return [line], imports, res_exc.provenance
        else:  # go
            imports = ["fmt"]
            line = f"return fmt.Errorf(\"%w: %s\", {res_exc.rendered_type}, {msg_arg})"
            return [line], imports, res_exc.provenance

        return [line], res_exc.required_imports, res_exc.provenance

    def _lower_try(
        self,
        stmt: ast.Try,
        lang: str,
        env_types: Dict[str, ResolvedType]
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []

        # Try body
        try_lines: List[str] = []
        for child in stmt.body:
            c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
            try_lines.extend(c_lines)
            imports.extend(c_imp)
            prov.extend(c_prov)

        indented_try = [f"    {l}" for l in try_lines]

        # Finally body
        finally_lines: List[str] = []
        for child in stmt.finalbody:
            f_lines, f_imp, f_prov = self._lower_stmt(child, lang, env_types)
            finally_lines.extend(f_lines)
            imports.extend(f_imp)
            prov.extend(f_prov)

        indented_finally = [f"    {l}" for l in finally_lines]

        lines: List[str] = []

        if lang == "csharp":
            lines.append("try")
            lines.append("{")
            lines.extend(indented_try)
            lines.append("}")

            for handler in stmt.handlers:
                h_lines: List[str] = []
                for child in handler.body:
                    c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                    h_lines.extend(c_lines)
                    imports.extend(c_imp)
                    prov.extend(c_prov)

                err_var = handler.name or "ex"
                exc_type_name = "Exception"
                if isinstance(handler.type, ast.Name):
                    raw_name = handler.type.id
                    concept = PYTHON_TYPE_TO_CONCEPT.get(raw_name, "exception.argument_null")
                    res = self._instantiate_type_template(concept, [], "csharp", raw_name=raw_name)
                    exc_type_name = res.rendered_type
                    imports.extend(res.required_imports)
                    prov.extend(res.provenance)

                lines.append(f"catch ({exc_type_name} {err_var})")
                lines.append("{")
                lines.extend([f"    {l}" for l in h_lines])
                lines.append("}")

            if stmt.finalbody:
                lines.append("finally")
                lines.append("{")
                lines.extend(indented_finally)
                lines.append("}")

        elif lang == "typescript":
            lines.append("try {")
            lines.extend(indented_try)
            lines.append("}")

            for handler in stmt.handlers:
                h_lines = []
                for child in handler.body:
                    c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                    h_lines.extend(c_lines)
                    imports.extend(c_imp)
                    prov.extend(c_prov)

                err_var = handler.name or "err"
                lines.append(f"catch ({err_var}) {{")
                lines.extend([f"    {l}" for l in h_lines])
                lines.append("}")

            if stmt.finalbody:
                lines.append("finally {")
                lines.extend(indented_finally)
                lines.append("}")

        elif lang == "cpp":
            imports.append("<stdexcept>")
            lines.append("try {")
            lines.extend(indented_try)
            lines.append("}")

            for handler in stmt.handlers:
                h_lines = []
                for child in handler.body:
                    c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                    h_lines.extend(c_lines)
                    imports.extend(c_imp)
                    prov.extend(c_prov)

                err_var = handler.name or "err"
                lines.append(f"catch (const std::exception& {err_var}) {{")
                lines.extend([f"    {l}" for l in h_lines])
                lines.append("}")

            if stmt.finalbody:
                lines.append("// Finally cleanup:")
                lines.extend(finally_lines)

        elif lang == "rust":
            lines.append("// Lowered try/catch error recovery via std::panic::catch_unwind")
            lines.append("let _catch_res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {")
            lines.extend(indented_try)
            lines.append("}));")

            if stmt.handlers:
                handler = stmt.handlers[0]
                h_lines = []
                for child in handler.body:
                    c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                    h_lines.extend(c_lines)
                    imports.extend(c_imp)
                    prov.extend(c_prov)

                err_var = handler.name or "_err"
                lines.append(f"if let Err({err_var}) = _catch_res {{")
                lines.extend([f"    {l}" for l in h_lines])
                lines.append("}")

            if stmt.finalbody:
                lines.extend(finally_lines)

        else:  # go
            lines.append("func() {")
            lines.append("    defer func() {")
            lines.append("        if r := recover(); r != nil {")
            if stmt.handlers:
                handler = stmt.handlers[0]
                h_lines = []
                for child in handler.body:
                    c_lines, c_imp, c_prov = self._lower_stmt(child, lang, env_types)
                    h_lines.extend(c_lines)
                    imports.extend(c_imp)
                    prov.extend(c_prov)
                lines.extend([f"            {l}" for l in h_lines])
            lines.append("        }")
            if stmt.finalbody:
                lines.extend([f"        {l}" for l in finally_lines])
            lines.append("    }()")
            lines.extend(indented_try)
            lines.append("}()")

        prov.append(ProvenanceRecord(
            construct="try_except",
            concept_key="exception.error_handling",
            target_language=lang,
            resolved_target="try_catch" if lang in ("csharp", "typescript", "cpp") else "panic_recovery",
            verification_status="verified_ast"
        ))

        return lines, imports, prov

    # ------------------------------------------------------------------------
    # Stage 5: Target Syntax Formatting
    # ------------------------------------------------------------------------
    def _render_initializer(
        self,
        res_type: ResolvedType,
        init_node: Optional[ast.AST],
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> str:
        ckey = res_type.concept_key
        t_str = res_type.rendered_type

        if isinstance(init_node, (ast.List, ast.Dict, ast.Set)) or init_node is None:
            if "dynamic_array" in ckey or "sequence" in ckey:
                return {
                    "csharp": f"new {t_str}()",
                    "rust": "Vec::new()",
                    "typescript": "[]",
                    "cpp": "{}",
                    "go": f"{t_str}{{}}",
                }[lang]
            if "hash_map" in ckey or "map" in ckey:
                return {
                    "csharp": f"new {t_str}()",
                    "rust": f"HashMap::new()",
                    "typescript": f"new {t_str}()",
                    "cpp": "{}",
                    "go": f"make({t_str})",
                }[lang]
            if "hash_set" in ckey or "set" in ckey:
                return {
                    "csharp": f"new {t_str}()",
                    "rust": "HashSet::new()",
                    "typescript": f"new {t_str}()",
                    "cpp": "{}",
                    "go": f"make({t_str})",
                }[lang]

        return self._render_expr(init_node, lang, env_types, [], [])

    @staticmethod
    def _format_var_decl(name: str, rendered_type: str, init_expr: str, lang: str) -> str:
        if lang == "csharp":
            return f"{rendered_type} {name} = {init_expr};"
        if lang == "rust":
            return f"let mut {name}: {rendered_type} = {init_expr};"
        if lang == "typescript":
            return f"const {name}: {rendered_type} = {init_expr};"
        if lang == "cpp":
            return f"{rendered_type} {name} = {init_expr};"
        return f"var {name} {rendered_type} = {init_expr}"

    @staticmethod
    def _format_untyped_assign(name: str, rhs: str, lang: str) -> str:
        if lang == "csharp":
            return f"var {name} = {rhs};"
        if lang == "rust":
            return f"let {name} = {rhs};"
        if lang == "typescript":
            return f"const {name} = {rhs};"
        if lang == "cpp":
            return f"auto {name} = {rhs};"
        return f"{name} := {rhs}"

    @staticmethod
    def _terminate_stmt(expr_str: str, lang: str) -> str:
        if lang in ("csharp", "rust", "typescript", "cpp") and not expr_str.endswith(";"):
            return f"{expr_str};"
        return expr_str

    @staticmethod
    def _format_imports(imports: List[str], lang: str) -> str:
        if not imports:
            return ""
        if lang == "csharp":
            return "\n".join(f"using {imp};" for imp in imports)
        if lang == "rust":
            return "\n".join(f"use {imp};" for imp in imports)
        if lang == "cpp":
            return "\n".join(f"#include {imp}" if imp.startswith("<") or imp.startswith('"') else f"#include <{imp}>" for imp in imports)
        if lang == "go":
            return "\n".join(f'import "{imp}"' for imp in imports)
        return ""
