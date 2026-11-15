import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_export_rust_project_archive():
    py_code = """
items: list[int] = []
items.append(42)
count = len(items)
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "rust", "project_name": "test_rust_app"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment; filename=\"test_rust_app_rust.zip\"" in response.headers["content-disposition"]

    # Verify ZIP contents
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "Cargo.toml" in namelist
    assert "src/main.rs" in namelist
    assert "README.md" in namelist
    assert ".gitignore" in namelist

    cargo_content = zf.read("Cargo.toml").decode("utf-8")
    assert 'name = "test_rust_app"' in cargo_content
    assert "edition = \"2021\"" in cargo_content

    main_rs = zf.read("src/main.rs").decode("utf-8")
    assert "fn main()" in main_rs
    assert "items.push(42)" in main_rs


def test_export_csharp_project_archive():
    py_code = """
scores: dict[str, int] = {}
scores["alice"] = 100
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "csharp", "project_name": "TestCSharpApp"},
    )
    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "TestCSharpApp.csproj" in namelist
    assert "Program.cs" in namelist
    assert "README.md" in namelist

    csproj = zf.read("TestCSharpApp.csproj").decode("utf-8")
    assert '<Project Sdk="Microsoft.NET.Sdk">' in csproj

    program_cs = zf.read("Program.cs").decode("utf-8")
    assert "using System.Collections.Generic;" in program_cs
    assert 'scores["alice"] = 100;' in program_cs


def test_export_go_project_archive():
    py_code = """
ids: list[int] = []
ids.append(999)
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "go", "project_name": "test_go_app"},
    )
    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "go.mod" in namelist
    assert "main.go" in namelist

    go_mod = zf.read("go.mod").decode("utf-8")
    assert "module test_go_app" in go_mod

    main_go = zf.read("main.go").decode("utf-8")
    assert "package main" in main_go
    assert "func main()" in main_go


def test_export_typescript_project_archive():
    py_code = """
def greet(name: str) -> str:
    return name

msg = greet("World")
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "typescript", "project_name": "test-ts-app"},
    )
    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "package.json" in namelist
    assert "tsconfig.json" in namelist
    assert "src/index.ts" in namelist

    pkg = zf.read("package.json").decode("utf-8")
    assert '"name": "test-ts-app"' in pkg
    assert '"typescript"' in pkg


def test_export_cpp_project_archive():
    py_code = """
items: list[int] = []
items.append(10)
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "cpp", "project_name": "test_cpp_app"},
    )
    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "CMakeLists.txt" in namelist
    assert "main.cpp" in namelist

    cmake = zf.read("CMakeLists.txt").decode("utf-8")
    assert "project(test_cpp_app CXX)" in cmake

    main_cpp = zf.read("main.cpp").decode("utf-8")
    assert "#include <vector>" in main_cpp
    assert "int main()" in main_cpp


def test_export_all_bundle_project_archive():
    py_code = """
items: list[int] = []
items.append(42)
"""
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": py_code, "target": "all", "project_name": "my_suite"},
    )
    assert response.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    namelist = zf.namelist()
    assert "rust/Cargo.toml" in namelist
    assert "rust/src/main.rs" in namelist
    assert "csharp/my_suite_csharp.csproj" in namelist
    assert "csharp/Program.cs" in namelist
    assert "go/go.mod" in namelist
    assert "go/main.go" in namelist
    assert "typescript/package.json" in namelist
    assert "typescript/src/index.ts" in namelist
    assert "cpp/CMakeLists.txt" in namelist
    assert "cpp/main.cpp" in namelist
    assert "README.md" in namelist
    assert "Makefile" in namelist


def test_export_empty_code_returns_400():
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": "   ", "target": "rust"},
    )
    assert response.status_code == 400


def test_export_invalid_target_returns_400():
    response = client.post(
        "/api/bridge/export-project",
        json={"python_code": "x = 1", "target": "unknown_lang"},
    )
    assert response.status_code == 400
