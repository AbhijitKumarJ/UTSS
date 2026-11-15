import sqlite3
from pathlib import Path
import pytest
from utss.cli import main


def test_cli_harvest_and_report(tmp_path: Path, capsys: pytest.CaptureFixture):
    db_file = tmp_path / "cli_catalog.db"

    # Harvest ambient + small stdlib subset
    exit_code = main([
        "harvest",
        "--db", str(db_file),
        "--stdlib-modules", "sys", "math",
        "--reset",
    ])
    assert exit_code == 0
    assert db_file.exists()

    # Verify tables in database
    conn = sqlite3.connect(str(db_file))
    count = conn.execute("SELECT COUNT(*) FROM symbols;").fetchone()[0]
    assert count > 100
    conn.close()

    # Report command
    report_code = main(["report", "--db", str(db_file)])
    assert report_code == 0
    captured = capsys.readouterr()
    assert "PYTHON SPECTRUM CATALOG SUMMARY" in captured.out
    assert "Runtime" in captured.out


def test_cli_query_commands(tmp_path: Path, capsys: pytest.CaptureFixture):
    db_file = tmp_path / "query_catalog.db"
    main([
        "harvest",
        "--db", str(db_file),
        "--stdlib-modules", "sys", "io", "_io",
        "--reset",
    ])

    # Query ambient
    code_amb = main(["query", "--db", str(db_file), "--ambient"])
    assert code_amb == 0
    captured = capsys.readouterr()
    assert "<ambient>" in captured.out

    # Query module
    code_mod = main(["query", "--db", str(db_file), "--module", "sys"])
    assert code_mod == 0
    captured = capsys.readouterr()
    assert "Module 'sys'" in captured.out

    # Query C-accelerators
    code_acc = main(["query", "--db", str(db_file), "--c-accelerators"])
    assert code_acc == 0
    captured = capsys.readouterr()
    assert "C-Accelerator Re-Exports" in captured.out


def test_cli_overlay_and_overload_queries(tmp_path: Path, capsys: pytest.CaptureFixture):
    db_file = tmp_path / "overlay_catalog.db"

    # Harvest with embedded demo stubs enabled
    exit_code = main([
        "harvest",
        "--db", str(db_file),
        "--stdlib-modules", "sys", "os", "json",
        "--demo-stubs",
        "--reset",
    ])
    assert exit_code == 0

    # Query overloads
    code_ov = main(["query", "--db", str(db_file), "--overloads"])
    assert code_ov == 0
    captured = capsys.readouterr()
    assert "Polymorphic @overload Sets" in captured.out
    assert "open" in captured.out or "max" in captured.out

    # Query pyi-enriched
    code_en = main(["query", "--db", str(db_file), "--pyi-enriched"])
    assert code_en == 0
    captured = capsys.readouterr()
    assert "Static .pyi Enriched Callables" in captured.out

    # Test overlay subcommand explicitly
    db_plain = tmp_path / "plain_catalog.db"
    main([
        "harvest",
        "--db", str(db_plain),
        "--stdlib-modules", "sys",
        "--reset",
    ])
    overlay_code = main(["overlay", "--db", str(db_plain), "--demo-stubs"])
    assert overlay_code == 0
    captured = capsys.readouterr()
    assert "Applied embedded demo stubs" in captured.out


def test_cli_demo_workspace_and_workspace_queries(tmp_path: Path, capsys: pytest.CaptureFixture):
    db_file = tmp_path / "ws_catalog.db"

    # Harvest with embedded demo stubs and demo workspace
    exit_code = main([
        "harvest",
        "--db", str(db_file),
        "--stdlib-modules", "sys", "os", "json",
        "--demo-stubs",
        "--demo-workspace",
        "--reset",
    ])
    assert exit_code == 0

    # Query workspace symbols
    code_sym = main(["query", "--db", str(db_file), "--workspace-symbols"])
    assert code_sym == 0
    captured = capsys.readouterr()
    assert "Stratum 3 Workspace Symbols" in captured.out
    assert "subtotal" in captured.out

    # Query workspace generators
    code_gen = main(["query", "--db", str(db_file), "--workspace-generators"])
    assert code_gen == 0
    captured = capsys.readouterr()
    assert "Stratum 3 Generators & Coroutines" in captured.out
    assert "stream_orders" in captured.out

    # Query workspace imports
    code_imp = main(["query", "--db", str(db_file), "--workspace-imports"])
    assert code_imp == 0
    captured = capsys.readouterr()
    assert "Stratum 3 Workspace Import & Re-Export Graph" in captured.out
    assert "commerce_engine" in captured.out

