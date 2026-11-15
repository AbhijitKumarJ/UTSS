import ast
from typing import Any
from server.config import Config
from server.analysis.bridge_transpiler import BridgeCatalogRepository, BridgeTranspiler, TARGET_LANGUAGES

# AST Node categories to display in the flow visualizer
STATEMENT_NODES = {
    "Module",
    "ClassDef",
    "FunctionDef",
    "AsyncFunctionDef",
    "Assign",
    "AnnAssign",
    "AugAssign",
    "For",
    "While",
    "If",
    "Try",
    "ExceptHandler",
    "With",
    "Return",
    "Expr",
    "Raise",
    "Assert",
    "Pass",
    "Break",
    "Continue"
}

EXPRESSION_NODES = {
    "Call",
    "Attribute",
    "Subscript",
    "BinOp",
    "Compare",
    "List",
    "Dict",
    "Set"
}

ALLOWED_NODES = STATEMENT_NODES | EXPRESSION_NODES

class AstFlowBuilder:
    """Builds a structured hierarchical flow graph and lowering preview from a Python AST."""

    def __init__(self, python_code: str):
        self.code = python_code
        self.lines = python_code.splitlines()
        self.node_counter = 0
        self.max_depth = 0
        self.concepts_detected: set[str] = set()
        bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
        self.repo = BridgeCatalogRepository(bridge_db) if bridge_db.exists() else None
        self.transpiler = BridgeTranspiler(self.repo) if self.repo else None

    def close(self):
        if self.repo:
            self.repo.close()

    def _extract_source(self, start_line: int | None, end_line: int | None) -> str:
        if not start_line or start_line < 1 or start_line > len(self.lines):
            return ""
        end = end_line if end_line and end_line <= len(self.lines) else start_line
        selected = self.lines[start_line - 1:end]
        return "\n".join(selected)

    def _infer_ir_concept(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.ClassDef):
            self.concepts_detected.add("user_type")
            return "user_type"
        elif isinstance(node, (ast.Try, ast.ExceptHandler)):
            self.concepts_detected.add("exception.try_catch")
            return "exception.try_catch"
        elif isinstance(node, ast.For):
            self.concepts_detected.add("control_flow.for_loop")
            return "control_flow.for_loop"
        elif isinstance(node, ast.While):
            self.concepts_detected.add("control_flow.while_loop")
            return "control_flow.while_loop"
        elif isinstance(node, ast.If):
            self.concepts_detected.add("control_flow.conditional")
            return "control_flow.conditional"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                op_name = node.func.attr
                if op_name in ("append", "push", "pop", "insert"):
                    self.concepts_detected.add("collection.dynamic_array")
                    return "collection.dynamic_array"
                elif op_name in ("add", "remove", "discard"):
                    self.concepts_detected.add("collection.hash_set")
                    return "collection.hash_set"
                elif op_name in ("keys", "values", "items", "get"):
                    self.concepts_detected.add("collection.hash_map")
                    return "collection.hash_map"
                elif op_name in ("startswith", "endswith", "lower", "upper", "strip", "split", "replace"):
                    self.concepts_detected.add("primitive.string_utf8")
                    return "primitive.string_utf8"
            elif isinstance(node.func, ast.Name):
                if node.func.id == "len":
                    self.concepts_detected.add("collection.len")
                    return "collection.len"
                elif node.func.id in ("print", "input"):
                    self.concepts_detected.add("io.standard_streams")
                    return "io.standard_streams"
        return None

    def _generate_node_label(self, node: ast.AST) -> str:
        ntype = node.__class__.__name__
        try:
            if isinstance(node, ast.Module):
                return "Module (Compilation Unit)"
            elif isinstance(node, ast.ClassDef):
                bases = f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else ""
                return f"class {node.name}{bases}"
            elif isinstance(node, ast.FunctionDef):
                ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                args = ", ".join(a.arg for a in node.args.args)
                return f"def {node.name}({args}){ret}"
            elif isinstance(node, ast.Assign):
                targets = ", ".join(ast.unparse(t) for t in node.targets)
                return f"{targets} = ..."
            elif isinstance(node, ast.AnnAssign):
                target = ast.unparse(node.target)
                ann = ast.unparse(node.annotation)
                return f"{target}: {ann} = ..."
            elif isinstance(node, ast.For):
                return f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}:"
            elif isinstance(node, ast.While):
                return f"while {ast.unparse(node.test)}:"
            elif isinstance(node, ast.If):
                return f"if {ast.unparse(node.test)}:"
            elif isinstance(node, ast.Try):
                return "try: ... except: ..."
            elif isinstance(node, ast.ExceptHandler):
                ex_name = ast.unparse(node.type) if node.type else "Exception"
                name = f" as {node.name}" if node.name else ""
                return f"except {ex_name}{name}:"
            elif isinstance(node, ast.Return):
                val = f" {ast.unparse(node.value)}" if node.value else ""
                return f"return{val}"
            elif isinstance(node, ast.Call):
                return f"call: {ast.unparse(node.func)}(...)"
            elif isinstance(node, ast.Expr):
                return ast.unparse(node.value)[:60]
            else:
                unparsed = ast.unparse(node)
                return unparsed[:50] if len(unparsed) <= 50 else f"{unparsed[:47]}..."
        except Exception:
            return ntype

    def _generate_lowering_previews(self, node: ast.AST) -> dict[str, str]:
        """Synthesizes isolated multi-language code snippets for the given AST node."""
        if isinstance(node, ast.Module) or not self.transpiler:
            return {}
        try:
            synthetic_code = ""
            if isinstance(node, ast.stmt):
                synthetic_module = ast.Module(body=[node], type_ignores=[])
                synthetic_code = ast.unparse(synthetic_module)
            elif isinstance(node, ast.expr):
                synthetic_module = ast.Module(body=[ast.Expr(value=node)], type_ignores=[])
                synthetic_code = ast.unparse(synthetic_module)

            if not synthetic_code.strip():
                return {}

            previews: dict[str, str] = {}
            for lang in ("csharp", "rust", "typescript", "cpp", "go"):
                try:
                    out = self.transpiler.transpile_module(synthetic_code, lang)
                    if out and out.source_code:
                        previews[lang] = out.source_code.strip()
                except Exception:
                    pass
            return previews
        except Exception:
            return {}

    def _visit(self, node: ast.AST, depth: int = 1) -> dict[str, Any] | None:
        ntype = node.__class__.__name__
        if ntype not in ALLOWED_NODES:
            # If this node is not directly in allowed, try to visit its children directly
            return None

        self.node_counter += 1
        current_id = f"ast_node_{self.node_counter}"
        if depth > self.max_depth:
            self.max_depth = depth

        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", start_line)
        col_offset = getattr(node, "col_offset", None)

        label = self._generate_node_label(node)
        ir_concept = self._infer_ir_concept(node)
        source_snippet = self._extract_source(start_line, end_line)
        lowering_previews = self._generate_lowering_previews(node)

        # Recurse children
        children = []
        for child in ast.iter_child_nodes(node):
            c_res = self._visit(child, depth + 1)
            if c_res:
                children.append(c_res)
            else:
                # If child was skipped (e.g. arguments or load/store), check its descendants
                for grandchild in ast.iter_child_nodes(child):
                    gc_res = self._visit(grandchild, depth + 1)
                    if gc_res:
                        children.append(gc_res)

        return {
            "id": current_id,
            "node_type": ntype,
            "label": label,
            "line_start": start_line,
            "line_end": end_line,
            "col_offset": col_offset,
            "ir_concept": ir_concept,
            "source_snippet": source_snippet,
            "lowering_previews": lowering_previews,
            "children": children
        }

    def build(self) -> dict[str, Any]:
        parsed = ast.parse(self.code)
        root = self._visit(parsed, depth=1)
        return {
            "root": root,
            "node_count": self.node_counter,
            "max_depth": self.max_depth,
            "concepts_detected": sorted(list(self.concepts_detected))
        }

def build_ast_flow(python_code: str) -> dict[str, Any]:
    """Generates the AST flow graph and lowering previews for the given Python code."""
    builder = AstFlowBuilder(python_code)
    try:
        return builder.build()
    finally:
        builder.close()
