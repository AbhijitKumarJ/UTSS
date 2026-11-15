import ast
from dataclasses import asdict
from typing import Any
from server.config import Config
from server.analysis.bridge_transpiler import BridgeCatalogRepository, BridgeTranspiler, TARGET_LANGUAGES

def run_compiler_pipeline(python_code: str, target_language: str = "rust") -> dict[str, Any]:
    """Executes and records the 4 classical compilation passes from Python source to target language."""
    target_lang = target_language.lower().strip()
    if target_lang not in TARGET_LANGUAGES:
        target_lang = "rust"

    # ------------------------------------------------------------------------
    # Pass 1: Frontend AST Parsing & Syntax Tree Normalization
    # ------------------------------------------------------------------------
    tree = ast.parse(python_code)
    all_nodes = list(ast.walk(tree))
    total_nodes = len(all_nodes)
    top_level_stmts = len(tree.body)

    stmt_kinds = {}
    for stmt in tree.body:
        k = stmt.__class__.__name__
        stmt_kinds[k] = stmt_kinds.get(k, 0) + 1

    try:
        ast_formatted_dump = ast.dump(tree, indent=2)
    except Exception:
        ast_formatted_dump = ast.dump(tree)

    pass_1 = {
        "pass_id": "pass_1_frontend",
        "name": "Pass 1: AST Parsing & Syntax Tree Normalization",
        "stage": "Frontend",
        "status": "success",
        "summary": f"Successfully parsed Python syntax tree with {total_nodes} total AST nodes across {top_level_stmts} top-level statements.",
        "metrics": {
            "total_ast_nodes": total_nodes,
            "top_level_statements": top_level_stmts,
            "statement_breakdown": stmt_kinds
        },
        "artifacts": {
            "ast_dump": ast_formatted_dump
        }
    }

    # ------------------------------------------------------------------------
    # Pass 2: Semantic Analysis & Symbol Environment Binding
    # ------------------------------------------------------------------------
    symbol_table: list[dict[str, Any]] = []
    user_classes: dict[str, dict[str, Any]] = {}
    user_functions: list[str] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            user_classes[stmt.name] = {
                "name": stmt.name,
                "bases": [ast.unparse(b) for b in stmt.bases],
                "methods": [m.name for m in stmt.body if isinstance(m, ast.FunctionDef)],
                "attributes": []
            }
            symbol_table.append({
                "identifier": stmt.name,
                "symbol_kind": "class",
                "inferred_type": stmt.name,
                "concept_key": "user_type",
                "scope": "module",
                "line": getattr(stmt, "lineno", None)
            })
            for m in stmt.body:
                if isinstance(m, ast.FunctionDef):
                    symbol_table.append({
                        "identifier": f"{stmt.name}::{m.name}",
                        "symbol_kind": "method",
                        "inferred_type": "callable",
                        "concept_key": "user_method",
                        "scope": f"class {stmt.name}",
                        "line": getattr(m, "lineno", None)
                    })
        elif isinstance(stmt, ast.FunctionDef):
            user_functions.append(stmt.name)
            ret_type = ast.unparse(stmt.returns) if stmt.returns else "void"
            symbol_table.append({
                "identifier": stmt.name,
                "symbol_kind": "function",
                "inferred_type": f"callable -> {ret_type}",
                "concept_key": "user_function",
                "scope": "module",
                "line": getattr(stmt, "lineno", None)
            })
        elif isinstance(stmt, ast.AnnAssign):
            var_name = ast.unparse(stmt.target)
            ann_type = ast.unparse(stmt.annotation)
            concept = "user_variable"
            if "list" in ann_type:
                concept = "collection.dynamic_array"
            elif "dict" in ann_type:
                concept = "collection.hash_map"
            elif "set" in ann_type:
                concept = "collection.hash_set"
            elif "str" in ann_type:
                concept = "primitive.string_utf8"
            elif "int" in ann_type:
                concept = "primitive.int64"
            elif "bool" in ann_type:
                concept = "primitive.bool"

            symbol_table.append({
                "identifier": var_name,
                "symbol_kind": "variable",
                "inferred_type": ann_type,
                "concept_key": concept,
                "scope": "local",
                "line": getattr(stmt, "lineno", None)
            })
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                var_name = ast.unparse(t)
                inferred = "unknown"
                concept = "user_variable"
                if isinstance(stmt.value, ast.List):
                    inferred = "list[Any]"
                    concept = "collection.dynamic_array"
                elif isinstance(stmt.value, ast.Dict):
                    inferred = "dict[Any, Any]"
                    concept = "collection.hash_map"
                elif isinstance(stmt.value, ast.Set):
                    inferred = "set[Any]"
                    concept = "collection.hash_set"
                elif isinstance(stmt.value, ast.Constant):
                    if isinstance(stmt.value.value, str):
                        inferred = "str"
                        concept = "primitive.string_utf8"
                    elif isinstance(stmt.value.value, bool):
                        inferred = "bool"
                        concept = "primitive.bool"
                    elif isinstance(stmt.value.value, int):
                        inferred = "int"
                        concept = "primitive.int64"
                elif isinstance(stmt.value, ast.Call):
                    func_name = ast.unparse(stmt.value.func)
                    if func_name in user_classes:
                        inferred = func_name
                        concept = "user_type"

                symbol_table.append({
                    "identifier": var_name,
                    "symbol_kind": "variable",
                    "inferred_type": inferred,
                    "concept_key": concept,
                    "scope": "local",
                    "line": getattr(stmt, "lineno", None)
                })

    pass_2 = {
        "pass_id": "pass_2_semantic",
        "name": "Pass 2: Type Inference & Symbol Environment Binding",
        "stage": "Semantic Analysis",
        "status": "success",
        "summary": f"Bound {len(symbol_table)} symbols into environment table with {len(user_classes)} user-defined types.",
        "metrics": {
            "total_symbols": len(symbol_table),
            "user_classes_count": len(user_classes),
            "user_functions_count": len(user_functions)
        },
        "artifacts": {
            "symbol_table": symbol_table
        }
    }

    # ------------------------------------------------------------------------
    # Pass 3: Middle-End IR & Memory Model / Mutability Binding
    # ------------------------------------------------------------------------
    # Mutability inference: check which identifiers are mutated
    mutated_identifiers: set[str] = set()
    for node in all_nodes:
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            mutated_identifiers.add(node.target.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("append", "push", "pop", "insert", "add", "remove", "clear", "update"):
                if isinstance(node.func.value, ast.Name):
                    mutated_identifiers.add(node.func.value.id)

    target_memory_models = {
        "rust": "owned_heap_or_stack",
        "csharp": "managed_gc_heap",
        "typescript": "v8_gc_heap",
        "cpp": "raii_value_or_pointer",
        "go": "escape_analyzed_heap"
    }

    target_receiver_pass_kinds = {
        "rust": "mut_ref" if mutated_identifiers else "ref",
        "csharp": "mut_ref",
        "typescript": "mut_ref",
        "cpp": "mut_ref",
        "go": "slice_header_or_pointer"
    }

    required_imports = []
    has_list = any("list" in s.get("inferred_type", "") for s in symbol_table)
    has_dict = any("dict" in s.get("inferred_type", "") for s in symbol_table)
    has_set = any("set" in s.get("inferred_type", "") for s in symbol_table)

    if target_lang == "rust":
        if has_dict:
            required_imports.append("std::collections::HashMap")
        if has_set:
            required_imports.append("std::collections::HashSet")
        if has_list:
            required_imports.append("alloc::vec::Vec")
    elif target_lang == "csharp":
        if has_list or has_dict or has_set:
            required_imports.append("System.Collections.Generic")
    elif target_lang == "go":
        # Check string ops
        has_string_ops = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("startswith", "endswith", "lower", "upper", "split", "replace") for n in all_nodes)
        if has_string_ops:
            required_imports.append("strings")
    elif target_lang == "cpp":
        if has_list:
            required_imports.append("<vector>")
        if has_dict:
            required_imports.append("<unordered_map>")
        if has_set:
            required_imports.append("<unordered_set>")
        required_imports.append("<iostream>")

    mutability_map = {}
    for s in symbol_table:
        if s["symbol_kind"] == "variable":
            is_mut = s["identifier"] in mutated_identifiers
            mutability_map[s["identifier"]] = {
                "mutated": is_mut,
                "binding_declaration": {
                    "rust": "let mut" if is_mut else "let",
                    "typescript": "let" if is_mut else "const",
                    "csharp": "var",
                    "go": ":=",
                    "cpp": "auto"
                }.get(target_lang, "var")
            }

    impedance_notes = []
    if target_lang == "rust":
        for var, info in mutability_map.items():
            if info["mutated"]:
                impedance_notes.append(f"Identifier '{var}' mutated via in-place operations: Synthesizing 'let mut {var}' in Rust.")
    elif target_lang == "go":
        if has_list:
            impedance_notes.append("Python dynamic array lowered to Go slice header: operations (e.g. append) re-bind slice values.")

    pass_3 = {
        "pass_id": "pass_3_ir_memory",
        "name": f"Pass 3: IR Normalization & Memory Model Binding ({target_lang.upper()})",
        "stage": "Middle-End (IR)",
        "status": "success",
        "summary": f"Resolved memory model: '{target_memory_models.get(target_lang)}' with {len(mutated_identifiers)} mutated identifiers.",
        "metrics": {
            "target_memory_model": target_memory_models.get(target_lang, "value_default"),
            "receiver_pass_kind": target_receiver_pass_kinds.get(target_lang, "mut_ref"),
            "mutated_symbols_count": len(mutated_identifiers),
            "required_imports_count": len(required_imports)
        },
        "artifacts": {
            "mutability_map": mutability_map,
            "required_imports": required_imports,
            "impedance_notes": impedance_notes
        }
    }

    # ------------------------------------------------------------------------
    # Pass 4: Backend Emission & Provenance Generation
    # ------------------------------------------------------------------------
    bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
    repo = BridgeCatalogRepository(bridge_db) if bridge_db.exists() else None
    transpiler = BridgeTranspiler(repo) if repo else None

    emitted_code = ""
    provenance_records = []
    if transpiler:
        try:
            out = transpiler.transpile_module(python_code, target_lang)
            emitted_code = out.source_code
            provenance_records = [asdict(r) for r in out.provenance_trace]
        finally:
            if repo:
                repo.close()

    pass_4 = {
        "pass_id": "pass_4_codegen",
        "name": f"Pass 4: Multi-Target Code Synthesis & Provenance ({target_lang.upper()})",
        "stage": "Backend (Emission)",
        "status": "success",
        "summary": f"Synthesized {len(emitted_code.splitlines())} lines of {target_lang.upper()} source code with {len(provenance_records)} provenance traces.",
        "metrics": {
            "emitted_lines": len(emitted_code.splitlines()),
            "provenance_trace_count": len(provenance_records)
        },
        "artifacts": {
            "emitted_code": emitted_code,
            "provenance_records": provenance_records
        }
    }

    return {
        "source_code": python_code,
        "target_language": target_lang,
        "passes": [pass_1, pass_2, pass_3, pass_4]
    }
