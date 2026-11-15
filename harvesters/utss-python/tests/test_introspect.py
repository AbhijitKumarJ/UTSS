import inspect
import sys
from pathlib import Path
import pytest
from utss.introspect import (
    classify_identifier_visibility,
    safe_repr,
    compute_file_sha256,
    get_pure_builtins_without_site,
    extract_callable_signature,
    DUNDER_CATEGORIES,
    IMPLICIT_MODULE_DUNDERS,
)


def test_classify_identifier_visibility():
    assert classify_identifier_visibility("__init__") == ("system_dunder", 0)
    assert classify_identifier_visibility("__mangled") == ("private_mangled", 1)
    assert classify_identifier_visibility("_hidden") == ("hidden_internal", 1)
    assert classify_identifier_visibility("normal") == ("public_implicit", 0)
    assert classify_identifier_visibility("exported", dunder_all={"exported"}) == ("exported_all", 0)
    assert classify_identifier_visibility("unlisted", dunder_all={"exported"}) == ("public_implicit", 0)


def test_safe_repr():
    assert safe_repr(42) == "42"
    assert safe_repr("hello") == "'hello'"
    assert safe_repr(None) == "None"
    assert safe_repr(Ellipsis) == "Ellipsis"
    long_str = "a" * 200
    r = safe_repr(long_str, max_len=50)
    assert len(r) <= 50
    assert r.endswith("...'") or r.endswith("...")


def test_compute_file_sha256(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("utss test content")
    sha = compute_file_sha256(str(f))
    assert sha is not None
    assert len(sha) == 64
    assert compute_file_sha256(None) is None
    assert compute_file_sha256("/nonexistent/file/path") is None


def test_pure_builtins_differential():
    pure = get_pure_builtins_without_site()
    assert "len" in pure
    assert "open" in pure
    assert "int" in pure
    # site-injected symbols should not be in pure builtins when python -S runs
    assert "help" not in pure or "quit" not in pure


def test_extract_callable_signature_regular_function():
    def demo_func(a: int, b: str = "default", *args: float, c: bool = True, **kwargs) -> str:
        """Demo docstring."""
        return "result"

    sig_str, sig_source, ret_type, params = extract_callable_signature(demo_func)
    assert sig_str is not None
    assert sig_source == "inspect_signature"
    assert ret_type == "str"
    assert len(params) == 5
    assert params[0]["name"] == "a"
    assert params[0]["pass_kind"] == "positional_or_keyword"
    assert params[0]["is_optional"] == 0
    assert params[1]["name"] == "b"
    assert params[1]["default_expr"] == "'default'"
    assert params[1]["is_optional"] == 1
    assert params[2]["name"] == "args"
    assert params[2]["pass_kind"] == "var_positional"
    assert params[3]["name"] == "c"
    assert params[3]["pass_kind"] == "keyword_only"
    assert params[4]["name"] == "kwargs"
    assert params[4]["pass_kind"] == "var_keyword"


def test_extract_callable_signature_c_builtin():
    import math
    sig_str, sig_source, ret_type, params = extract_callable_signature(math.sin)
    assert sig_str is not None
    assert sig_source in ("text_signature", "inspect_signature", "docstring_first_line")


from unittest.mock import patch

def test_extract_callable_signature_resilient_to_symbolic_eval_error():
    class DummyCallable:
        __doc__ = "broken(x=SYMBOLIC_CONSTANT)\nA broken function."
        __text_signature__ = None
        def __call__(self, *args, **kwargs):
            pass

    dummy = DummyCallable()
    with patch("inspect.signature", side_effect=AttributeError("Symbolic constant eval failure")):
        sig_str, sig_source, ret_type, params = extract_callable_signature(dummy)
        assert sig_str == "broken(x=SYMBOLIC_CONSTANT)"
        assert sig_source == "docstring_first_line"
