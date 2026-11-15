import pytest
from tools.utss_comparative_analysis import run_comparative_analysis, generate_markdown_report

def test_run_comparative_analysis_recommended():
    data = run_comparative_analysis(variant="recommended")
    assert "languages" in data
    assert set(data["languages"]) == {"python", "csharp", "cpp", "go", "rust", "typescript"}

    assert "symbol_census" in data
    assert len(data["symbol_census"]) == 6

    assert "mutability_matrix" in data
    assert len(data["mutability_matrix"]) >= 5

    assert "parameter_passing" in data
    assert len(data["parameter_passing"]) >= 5

    assert "overloading_metrics" in data
    assert len(data["overloading_metrics"]) == 6

    assert "error_handling" in data
    assert len(data["error_handling"]) == 6

    assert "pairwise_impedance" in data
    matrix = data["pairwise_impedance"]
    assert len(matrix) == 6
    for lang in data["languages"]:
        assert matrix[lang][lang] == 0.0
    # Python to Rust should have notable impedance due to borrow checker, no overloads, error handling
    assert matrix["python"]["rust"] > 0.3

def test_generate_markdown_report():
    data = run_comparative_analysis(variant="recommended")
    md = generate_markdown_report(data)
    assert "# Empirical Transpiler Impedance & Cross-Language Parity Report" in md
    assert "## 1. Multi-Language Symbol Census" in md
    assert "## 2. Mutability & State Safety" in md
    assert "## 3. Parameter Passing Conventions" in md
    assert "## 4. Function Overloading & Multiplicity" in md
    assert "## 5. Error Handling Paradigms" in md
    assert "## 6. Pairwise Transpiler Impedance Matrix" in md
    assert "| Source \\ Target |" in md
