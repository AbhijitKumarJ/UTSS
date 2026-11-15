#!/usr/bin/env python3
"""
UTSS Phase 4: Custom Transpilation Rule Playground & Empirical Impedance Tester
================================================================================
Allows developers and students to define custom type mappings, operation templates,
and memory models, overlay them dynamically on top of the catalog, and evaluate
the resulting code for cross-language impedance, memory safety, and syntax correctness.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.analysis.bridge_transpiler import (
    BridgeCatalogRepository,
    BridgeTranspiler,
    TargetSynthesisOutput,
)
from server.config import Config


class CustomOverlayCatalogRepository(BridgeCatalogRepository):
    """
    Subclass of BridgeCatalogRepository that dynamically overlays
    in-memory custom type and operation templates before falling back to SQLite.
    """

    def __init__(self, db_path: Path, custom_rule: Dict[str, Any]) -> None:
        super().__init__(db_path)
        self.custom_rule = custom_rule
        self.target_lang = custom_rule.get("target_language", "rust").lower()
        self.base_concept = custom_rule.get("base_concept_key", "collection.dynamic_array")

    def get_type_mapping(self, concept_key: str, language: str) -> Optional[Dict[str, Any]]:
        if concept_key == self.base_concept and language == self.target_lang:
            return {
                "mapping_id": -99,
                "concept_id": 9999,
                "language": self.target_lang,
                "target_qualified_name": self.custom_rule.get("target_type_name", "CustomType"),
                "fallback_candidates_json": "[]",
                "type_syntax_template": self.custom_rule.get("type_syntax_template", "CustomType<{T}>"),
                "required_import": self.custom_rule.get("required_import"),
                "memory_model": self.custom_rule.get("memory_model", "owned_heap"),
                "nullability_model": self.custom_rule.get("nullability_model", "value_default"),
                "catalog_container_id": None,
                "catalog_symbol_id": None,
                "resolved_qualified_name": self.custom_rule.get("target_type_name"),
                "verified_stratum": 1,
                "verified_requires_import": 1 if self.custom_rule.get("required_import") else 0,
                "verification_status": "custom_override",
                "layer2_facet_json": "{}",
                "notes": "User-defined custom rule override",
            }
        return super().get_type_mapping(concept_key, language)

    def get_operation_mapping(self, concept_key: str, canonical_op: str, language: str) -> Optional[Dict[str, Any]]:
        custom_ops = self.custom_rule.get("custom_operations", {})
        if (
            concept_key == self.base_concept
            and language == self.target_lang
            and canonical_op in custom_ops
        ):
            call_tmpl = custom_ops[canonical_op]
            return {
                "op_mapping_id": -99,
                "concept_id": 9999,
                "canonical_op": canonical_op,
                "language": self.target_lang,
                "target_method_name": canonical_op,
                "target_receiver_passing": "mut_ref",
                "call_syntax_template": call_tmpl,
                "is_polymorphic": 0,
                "requires_intermediate_binding": 0,
                "verification_status": "custom_override",
                "notes": "User-defined custom operation override",
            }
        return super().get_operation_mapping(concept_key, canonical_op, language)


def evaluate_empirical_impedance(
    custom_rule: Dict[str, Any],
    emitted_code: str,
    target_lang: str,
    syntax_error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes an empirical impedance score (0-100) and diagnostic breakdown across:
    1. Memory Model Safety (30 pts)
    2. Mutability Contract (25 pts)
    3. Import Resolution (20 pts)
    4. Template Arity & Placeholder Integrity (25 pts)
    """
    if syntax_error:
        return {
            "impedance_score": 0,
            "impedance_risk": "HIGH",
            "score_factors": {
                "memory_safety": 0,
                "mutability_contract": 0,
                "import_resolution": 0,
                "template_integrity": 0,
            },
            "diagnostics": [
                f"Syntax parsing failure: {syntax_error}"
            ],
        }

    diagnostics: List[str] = []
    score_mem = 30
    score_mut = 25
    score_imp = 20
    score_tmpl = 25

    mem_model = custom_rule.get("memory_model", "owned_heap")
    type_tmpl = custom_rule.get("type_syntax_template", "")
    req_imp = custom_rule.get("required_import")
    custom_ops = custom_rule.get("custom_operations", {})

    # 1. Template Placeholder Integrity (25 pts)
    # Check type template for unclosed brackets or invalid syntax
    if "{" in type_tmpl and "}" not in type_tmpl:
        score_tmpl -= 15
        diagnostics.append("Type template has unclosed placeholder brackets '{'.")
    elif not type_tmpl.strip():
        score_tmpl -= 20
        diagnostics.append("Type template is empty.")

    for op_name, op_tmpl in custom_ops.items():
        if "{receiver}" not in op_tmpl and "." not in op_tmpl:
            score_tmpl -= 8
            diagnostics.append(f"Operation '{op_name}' does not reference '{{receiver}}'.")
        # Check for unclosed braces
        if op_tmpl.count("{") != op_tmpl.count("}"):
            score_tmpl -= 10
            diagnostics.append(f"Operation '{op_name}' has mismatched brace count.")

    score_tmpl = max(0, score_tmpl)

    # 2. Import Resolution (20 pts)
    if target_lang in ("csharp", "rust", "cpp") and not req_imp:
        if "." in custom_rule.get("target_type_name", "") or "::" in custom_rule.get("target_type_name", ""):
            score_imp -= 5
            diagnostics.append("Non-primitive custom type specified without explicit namespace import.")
    if req_imp and req_imp not in emitted_code:
        score_imp -= 10
        diagnostics.append(f"Specified import '{req_imp}' was not found in emitted source header.")
    score_imp = max(0, score_imp)

    # 3. Memory Model Safety (30 pts)
    if target_lang == "rust":
        if mem_model == "ref_gc":
            score_mem -= 15
            diagnostics.append("Rust does not possess a garbage collector; 'ref_gc' requires Rc<RefCell<T>> or Arc<Mutex<T>> wrapping.")
        elif mem_model == "slice_header":
            score_mem -= 5
            diagnostics.append("Slice headers in Rust require lifetime annotations ('&'a [T]') when passed across stack frames.")
    elif target_lang == "go":
        if mem_model == "owned_heap":
            score_mem -= 5
            diagnostics.append("Go runtime relies on escape analysis rather than compile-time affine ownership; owned_heap semantics are managed via garbage collection.")
    elif target_lang in ("typescript", "csharp"):
        if mem_model == "owned_heap":
            score_mem -= 8
            diagnostics.append(f"{target_lang.title()} runtime uses garbage collection; compile-time ownership tracking cannot be enforced natively.")

    score_mem = max(0, score_mem)

    # 4. Mutability Contract (25 pts)
    if target_lang == "rust":
        if "let mut" in emitted_code:
            score_mut = 25
        elif any(op in emitted_code for op in custom_ops.values()):
            # mutating calls on immutable binding
            if "let " in emitted_code and "let mut" not in emitted_code:
                score_mut -= 10
                diagnostics.append("Receiver may be declared immutable ('let') while custom operation mutates container.")
    elif target_lang == "typescript":
        if "const " in emitted_code:
            score_mut = 25

    score_mut = max(0, score_mut)

    total_score = score_mem + score_mut + score_imp + score_tmpl

    if total_score >= 85:
        risk = "LOW"
    elif total_score >= 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    if not diagnostics:
        diagnostics.append("Optimal syntactic and semantic alignment: zero impedance detected.")

    return {
        "impedance_score": total_score,
        "impedance_risk": risk,
        "score_factors": {
            "memory_safety": score_mem,
            "mutability_contract": score_mut,
            "import_resolution": score_imp,
            "template_integrity": score_tmpl,
        },
        "diagnostics": diagnostics,
    }


def test_custom_rule(
    python_code: str,
    target_language: str,
    custom_rule: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Overlays custom rule on `utss_universal_bridge.db`, transpiles the Python snippet,
    and runs the empirical impedance evaluator.
    """
    repo = CustomOverlayCatalogRepository(
        Config.DBS_DIR / "utss_universal_bridge.db",
        custom_rule,
    )
    try:
        transpiler = BridgeTranspiler(repo)
        syntax_err: Optional[str] = None
        emitted_code = ""
        imports: List[str] = []
        try:
            output: TargetSynthesisOutput = transpiler.transpile_module(python_code, target_language)
            emitted_code = output.source_code
            imports = output.imports
        except SyntaxError as se:
            syntax_err = f"SyntaxError at line {se.lineno}: {se.msg}"
        except Exception as ex:
            syntax_err = str(ex)

        eval_result = evaluate_empirical_impedance(
            custom_rule,
            emitted_code,
            target_language,
            syntax_error=syntax_err,
        )

        return {
            "rule_name": custom_rule.get("rule_name", "CustomRule"),
            "target_language": target_language,
            "source_python": python_code,
            "emitted_code": emitted_code,
            "injected_imports": imports,
            "impedance_score": eval_result["impedance_score"],
            "impedance_risk": eval_result["impedance_risk"],
            "score_factors": eval_result["score_factors"],
            "diagnostics": eval_result["diagnostics"],
        }
    finally:
        repo.close()
