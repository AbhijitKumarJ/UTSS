import pytest
from pathlib import Path
from server.config import Config
from server.analysis.bridge_transpiler import BridgeCatalogRepository, BridgeTranspiler, TARGET_LANGUAGES

BRIDGE_DB = Config.DBS_DIR / "utss_universal_bridge.db"

@pytest.fixture(scope="module")
def transpiler():
    repo = BridgeCatalogRepository(BRIDGE_DB)
    t = BridgeTranspiler(repo)
    yield t
    repo.close()

def test_transpile_collections_and_operations(transpiler):
    py_code = """
items: list[int] = []
items.append(42)
n = len(items)
scores: dict[str, int] = {}
scores["alice"] = 100
"""
    for lang in TARGET_LANGUAGES:
        out = transpiler.transpile_module(py_code, lang)
        assert out.language == lang
        assert len(out.statements) >= 3
        assert len(out.provenance_trace) > 0

    # Specific language checks
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "List<long> items = new List<long>();" in cs or "List<long> items = new();" in cs or "items.Add(42)" in cs
    assert "scores.Add" in cs or 'scores["alice"] = 100' in cs or "scores[" in cs

    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "items.push(42)" in rust
    assert "items.len()" in rust

    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "items.push(42)" in ts
    assert "items.length" in ts

    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "items.push_back(42)" in cpp or "push_back" in cpp
    assert "items.size()" in cpp

    go = transpiler.transpile_module(py_code, "go").source_code
    assert "append(items, 42)" in go
    assert "len(items)" in go

def test_transpile_control_flow_and_functions(transpiler):
    py_code = """
def double_val(x: int) -> int:
    return x * 2

items: list[int] = []
for item in items:
    if item > 0:
        total = total + item
    else:
        total = total - item
"""
    # C# control flow and method
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "foreach (var item in items)" in cs or "foreach" in cs
    assert "if (item > 0)" in cs or "if" in cs
    assert "double_val" in cs or "DoubleVal" in cs

    # Rust control flow and function
    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "for item in items" in rust
    assert "fn double_val" in rust

    # TypeScript control flow and function
    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "for (const item of items)" in ts
    assert "function double_val" in ts

    # Go control flow and function
    go = transpiler.transpile_module(py_code, "go").source_code
    assert "for _, item := range items" in go
    assert "func double_val" in go or "func DoubleVal" in go

    # C++ control flow
    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "for (const auto& item : items)" in cpp or "for (auto item : items)" in cpp

def test_transpile_context_manager_and_exceptions(transpiler):
    py_code = """
with open("test.txt") as f:
    data = f.read(1024)

raise ValueError("invalid value")
"""
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "using" in cs
    assert "throw new" in cs

    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "std::fs::File" in rust or "open" in rust
    assert "Err(" in rust or "return Err" in rust

    go = transpiler.transpile_module(py_code, "go").source_code
    assert "defer" in go or "Close()" in go
    assert "return fmt.Errorf" in go or "errors.New" in go

def test_api_bridge_transpile_valid():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    py_code = """
items: list[int] = []
items.append(42)
count = len(items)
"""
    res = client.post("/api/bridge/transpile", json={"python_code": py_code})
    assert res.status_code == 200
    data = res.json()
    assert "source_python" in data
    assert "targets" in data
    targets = data["targets"]
    assert "rust" in targets
    assert "csharp" in targets
    assert "typescript" in targets
    assert "cpp" in targets
    assert "go" in targets

    rust_out = targets["rust"]
    assert "items.push(42)" in rust_out["source_code"]
    assert len(rust_out["provenance_trace"]) > 0

def test_api_bridge_transpile_syntax_error():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    res = client.post("/api/bridge/transpile", json={"python_code": "def broken(:"})
    assert res.status_code == 400
    assert "SyntaxError" in res.json()["detail"]

def test_transpile_class_and_dataclass(transpiler):
    py_code = """
class User:
    id: int
    name: str
    is_active: bool
"""
    # C#
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "public class User" in cs
    assert "public long Id { get; set; }" in cs
    assert "public string Name { get; set; }" in cs
    assert "public bool IsActive { get; set; }" in cs
    assert "public User(" in cs

    # Rust
    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "pub struct User {" in rust
    assert "pub id: i64," in rust
    assert "pub name: String," in rust
    assert "pub is_active: bool," in rust
    assert "impl User {" in rust
    assert "pub fn new(" in rust

    # TypeScript
    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "export class User {" in ts
    assert "id: bigint;" in ts or "id: number;" in ts
    assert "name: string;" in ts
    assert "is_active: boolean;" in ts
    assert "constructor(" in ts

    # C++
    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "struct User {" in cpp
    assert "long long id;" in cpp or "int64_t id;" in cpp
    assert "std::string name;" in cpp
    assert "bool is_active;" in cpp
    assert "User(" in cpp

    # Go
    go = transpiler.transpile_module(py_code, "go").source_code
    assert "type User struct {" in go
    assert "Id int64" in go
    assert "Name string" in go
    assert "IsActive bool" in go
    assert "func NewUser(" in go

def test_transpile_class_with_methods_and_attributes(transpiler):
    py_code = """
class Counter:
    count: int

    def increment(self, step: int) -> int:
        self.count = self.count + step
        return self.count
"""
    # C#
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "public class Counter" in cs
    assert "public long Increment(" in cs
    assert "this.Count = this.Count + step" in cs or "Count = Count + step" in cs

    # Rust
    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "pub struct Counter" in rust
    assert "pub fn increment(&mut self, step: i64) -> i64" in rust
    assert "self.count = self.count + step" in rust

    # TypeScript
    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "export class Counter" in ts
    assert "public increment(" in ts
    assert "this.count = this.count + step" in ts

    # C++
    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "struct Counter" in cpp
    assert "increment(" in cpp
    assert "this->count = this->count + step" in cpp

    # Go
    go = transpiler.transpile_module(py_code, "go").source_code
    assert "type Counter struct" in go
    assert "func (self *Counter) Increment(" in go
    assert "self.Count = self.Count + step" in go

def test_transpile_try_except_finally(transpiler):
    py_code = """
try:
    items: list[int] = []
    val: int = items[0]
except IndexError as err:
    val: int = -1
finally:
    items.clear()
"""
    # C#
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "try" in cs
    assert "catch" in cs
    assert "finally" in cs
    assert "items.Clear();" in cs

    # TypeScript
    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "try {" in ts
    assert "catch" in ts
    assert "finally {" in ts
    assert "items.length = 0;" in ts

    # C++
    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "try {" in cpp
    assert "catch" in cpp
    assert "items.clear();" in cpp

    # Rust
    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "catch_unwind" in rust or "items.clear();" in rust

    # Go
    go = transpiler.transpile_module(py_code, "go").source_code
    assert "defer" in go or "items = items[:0]" in go

def test_transpile_string_and_set_operations(transpiler):
    py_code = """
s: str = "hello world"
upper_s = s.upper()

seen: set[str] = set()
seen.add("item1")
"""
    # C#
    cs = transpiler.transpile_module(py_code, "csharp").source_code
    assert "ToUpperInvariant" in cs
    assert "seen.Add(" in cs

    # Rust
    rust = transpiler.transpile_module(py_code, "rust").source_code
    assert "to_uppercase()" in rust
    assert "seen.insert(" in rust

    # TypeScript
    ts = transpiler.transpile_module(py_code, "typescript").source_code
    assert "toUpperCase()" in ts
    assert "seen.add(" in ts

    # Go
    go = transpiler.transpile_module(py_code, "go").source_code
    assert "strings.ToUpper" in go
    assert '"strings"' in go

    # C++
    cpp = transpiler.transpile_module(py_code, "cpp").source_code
    assert "seen.insert(" in cpp





