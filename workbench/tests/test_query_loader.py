import pytest
from pathlib import Path
from server.query_loader import QueryLoader

def test_parse_frontmatter_and_sql(tmp_path):
    sql_file = tmp_path / "test_query.sql"
    sql_file.write_text("""/*---
id: test_01
title: "Test Lesson"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Basic"
sequence: 1
category: "Basics"
pedagogical_rationale: "Explains basic test."
guided_experiments:
  - "Experiment 1"
---*/
SELECT 1 AS test;
""")
    loader = QueryLoader(queries_dir=tmp_path)
    q = loader.load_query_file(sql_file)
    assert q["id"] == "test_01"
    assert q["title"] == "Test Lesson"
    assert q["target_language"] == "python"
    assert q["suite"] == "tutoring"
    assert q["level"] == "Basic"
    assert q["sequence"] == 1
    assert q["category"] == "Basics"
    assert q["pedagogical_rationale"] == "Explains basic test."
    assert q["guided_experiments"] == ["Experiment 1"]
    assert q["lab_challenge"] is None
    assert q["sql"].strip() == "SELECT 1 AS test;"

def test_parse_frontmatter_with_lab_challenge(tmp_path):
    sql_file = tmp_path / "lab_query.sql"
    sql_file.write_text("""/*---
id: lab_01
title: "Lab Lesson"
target_language: "python"
suite: "tutoring"
lab_challenge:
  objective: "Count items"
  starter_sql: "SELECT 1;"
  solution_sql: "SELECT 1 AS count;"
  expected_columns:
    - count
  min_rows: 1
  xp_reward: 100
---*/
SELECT 1;
""")
    loader = QueryLoader(queries_dir=tmp_path)
    q = loader.load_query_file(sql_file)
    assert q["lab_challenge"] is not None
    assert q["lab_challenge"]["objective"] == "Count items"
    assert q["lab_challenge"]["xp_reward"] == 100
    assert q["lab_challenge"]["expected_columns"] == ["count"]

def test_get_all_queries_and_tree(tmp_path):
    # Setup mock directory hierarchy
    py_dir = tmp_path / "python" / "tutoring"
    py_dir.mkdir(parents=True)
    comp_dir = tmp_path / "comparative"
    comp_dir.mkdir(parents=True)

    (py_dir / "01_first.sql").write_text("""/*---
id: py_01
title: "First"
target_language: "python"
suite: "tutoring"
level: "Basic"
sequence: 1
category: "Intro"
pedagogical_rationale: "Rationale 1"
guided_experiments: ["Exp A"]
---*/
SELECT 'first';
""")
    (py_dir / "02_second.sql").write_text("""/*---
id: py_02
title: "Second"
target_language: "python"
suite: "tutoring"
level: "Intermediate"
sequence: 2
category: "Objects"
pedagogical_rationale: "Rationale 2"
guided_experiments: ["Exp B"]
---*/
SELECT 'second';
""")
    (comp_dir / "cross_summary.sql").write_text("""/*---
id: comp_01
title: "Cross Language"
target_language: "all"
suite: "comparative"
level: "Basic"
sequence: 1
category: "Comparative"
pedagogical_rationale: "Rationale cross"
guided_experiments: ["Exp Cross"]
---*/
SELECT 'cross';
""")

    loader = QueryLoader(queries_dir=tmp_path)
    all_queries = loader.get_all_queries()
    assert len(all_queries) == 3

    q = loader.get_query_by_id("py_02")
    assert q is not None
    assert q["title"] == "Second"

    # Test tree structure
    tree = loader.get_queries_tree(language="python", suite="tutoring")
    assert "tutoring" in tree
    assert "Basic" in tree["tutoring"]
    assert "Intermediate" in tree["tutoring"]
    assert len(tree["tutoring"]["Basic"]) == 1
    assert tree["tutoring"]["Basic"][0]["id"] == "py_01"
