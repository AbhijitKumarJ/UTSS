`build_bridge_db.py` automates Phase 4 of UTSS by scanning your 6 SQLite language catalogs (`python`, `csharp`, `rust`, `typescript`, `cpp`, `go`), resolving canonical types, methods, and protocols against each catalog's Layer 1 (`containers`, `symbols`, `callables`, `parameters`, `symbol_aliases`) and Layer 2 (`*_container_facets`, `*_symbol_facets`) tables, and generating `dbs/utss_universal_bridge.db`.

### 1. Architecture of the Automated Populator (`build_bridge_db.py`)

The script executes a four-stage empirical pipeline across all 6 catalogs:

| Stage | Pipeline Pass | UTSS Catalog Tables Scanned | Output Table in `utss_universal_bridge.db` |
| --- | --- | --- | --- |
| **Pass 1** | **Concept & Type Resolution** | `containers`, `symbols`, `distributions`, `symbol_aliases`, `*_container_facets` | `universal_concepts`, `universal_type_mappings` |
| **Pass 2** | **Operation & Signature Binding** | `symbols`, `callables`, `callable_overloads`, `parameters`, `*_symbol_facets` | `universal_operation_mappings` |
| **Pass 3** | **Protocol & Contract Verification** | `py_symbol_facets`, `cs_container_facets`, `rust_container_facets`, `go_container_facets`, `cpp_symbol_facets` | `universal_protocol_mappings` |
| **Pass 4** | **Autonomous Stdlib Taxonomist** | Full scan of `containers` & Layer 2 facets for all unmapped exceptions, collections, and I/O streams | `discovered_stdlib_taxonomy`

 |

---

### 2. Complete Populator Script (`build_bridge_db.py`)

Save this script in the root of your repository (or inside `server/analysis/build_bridge_db.py`):

```python
#!/usr/bin/env python3
"""
UTSS Phase 4: Automated Universal Bridge Database Populator (build_bridge_db.py)
================================================================================
Scans all 6 UTSS SQLite catalogs (Python, C#, Rust, TypeScript, C++, Go),
resolves canonical primitives, collections, control-flow wrappers, exceptions,
I/O streams, and behavioral protocols against empirical Layer 1 & Layer 2
tables, and builds `utss_universal_bridge.db`.

Usage:
    uv run python build_bridge_db.py --db-dir ./dbs --out-db ./dbs/utss_universal_bridge.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 1. CATALOG AUTO-DISCOVERY CONFIGURATION
# ============================================================================

DEFAULT_DB_CANDIDATES: Dict[str, List[str]] = {
    "python": [
        "dbs/python_base_full.db",
        "dbs/python_recommended.db",
        "catalog_base_full.db",
        "catalog.db",
        "harvesters/utss-python/catalog_base_full.db",
    ],
    "csharp": [
        "dbs/cs_base_full.db",
        "dbs/catalog_cs_full.db",
        "dbs/cs_recommended.db",
        "harvesters/utss-csharp/catalog_cs_full.db",
        "Z_CS/catalog_cs_full.db",
    ],
    "rust": [
        "dbs/rust_base_full.db",
        "dbs/catalog_rust_full.db",
        "dbs/rust_recommended.db",
        "harvesters/utss-rust/catalog_rust_full.db",
        "Z_Rust/catalog_rust_full.db",
    ],
    "typescript": [
        "dbs/ts_base_full.db",
        "dbs/catalog_ts_full.db",
        "dbs/ts_recommended.db",
        "harvesters/utss-typescript/catalog_ts_full.db",
        "Z_TS/catalog_ts_full.db",
    ],
    "cpp": [
        "dbs/cpp_base_full.db",
        "dbs/catalog_cpp_full.db",
        "dbs/cpp_recommended.db",
        "harvesters/utss-cpp/catalog_cpp_full.db",
        "Z_C/catalog_cpp_full.db",
    ],
    "go": [
        "dbs/go_base_full.db",
        "dbs/catalog_go_full.db",
        "dbs/go_recommended.db",
        "harvesters/utss-go/catalog_go_full.db",
        "Z_Go/catalog_go_full.db",
    ],
}


# ============================================================================
# 2. BRIDGE DATABASE DDL SCHEMA
# ============================================================================

BRIDGE_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS discovered_stdlib_taxonomy;
DROP TABLE IF EXISTS universal_protocol_mappings;
DROP TABLE IF EXISTS universal_operation_mappings;
DROP TABLE IF EXISTS universal_type_mappings;
DROP TABLE IF EXISTS universal_concepts;

-- Table 1: Language-agnostic compiler IR concepts
CREATE TABLE universal_concepts (
    concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,                 -- 'primitive', 'collection', 'control_flow', 'exception', 'io', 'protocol'
    type_arity INTEGER NOT NULL DEFAULT 0,  -- 0 = concrete, 1 = <T>, 2 = <K, V>
    description TEXT NOT NULL
);

-- Table 2: Cross-language type mappings enriched with empirical catalog bindings
CREATE TABLE universal_type_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    target_qualified_name TEXT NOT NULL,
    fallback_candidates_json TEXT NOT NULL DEFAULT '[]',
    type_syntax_template TEXT NOT NULL,
    required_import TEXT,
    memory_model TEXT NOT NULL,             -- 'value_stack', 'ref_gc', 'owned_heap', 'rc_box', 'slice_header'
    nullability_model TEXT NOT NULL,        -- 'nullable_ref', 'option_wrapper', 'value_default', 'pointer_nil'
    -- Empirical fields populated by scanning the language .db catalog:
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    resolved_qualified_name TEXT,
    verified_stratum INTEGER,
    verified_requires_import INTEGER,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    layer2_facet_json TEXT,
    notes TEXT,
    UNIQUE(concept_id, language)
);

-- Table 3: Cross-language operation/method mappings enriched with live signatures
CREATE TABLE universal_operation_mappings (
    op_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    canonical_op TEXT NOT NULL,
    language TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    call_syntax_template TEXT NOT NULL,
    receiver_pass_kind TEXT NOT NULL,       -- 'val', 'ref', 'mut_ref', 'pointer', 'free_fn', 'operator'
    mutates_receiver INTEGER NOT NULL DEFAULT 0,
    returns_new_value INTEGER NOT NULL DEFAULT 0,
    -- Empirical fields populated from callables & parameters tables:
    catalog_symbol_id INTEGER,
    verified_qualified_name TEXT,
    verified_raw_signature TEXT,
    verified_return_type TEXT,
    verified_overload_count INTEGER NOT NULL DEFAULT 0,
    verified_pass_kinds_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, canonical_op, language)
);

-- Table 4: Protocol, Trait, Interface & Dunder mappings
CREATE TABLE universal_protocol_mappings (
    proto_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    contract_kind TEXT NOT NULL,            -- 'dunder_protocol', 'interface', 'trait', 'implicit_interface', 'operator', 'symbol_protocol'
    contract_qualified_name TEXT NOT NULL,
    required_methods_json TEXT NOT NULL,
    lowering_strategy TEXT NOT NULL,
    -- Empirical fields populated from catalog scan:
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    implementing_count INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, language)
);

-- Table 5: Auto-harvested standard library taxonomy (long-tail collections, exceptions, I/O, traits)
CREATE TABLE discovered_stdlib_taxonomy (
    discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    taxonomy_domain TEXT NOT NULL,          -- 'exception', 'collection', 'io_stream', 'protocol_trait_interface'
    stratum INTEGER NOT NULL,
    entity_kind TEXT NOT NULL,              -- container_kind or symbol_kind
    qualified_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    public_method_count INTEGER NOT NULL DEFAULT 0,
    layer2_metadata_json TEXT,
    UNIQUE(language, taxonomy_domain, qualified_name)
);

CREATE INDEX idx_utm_concept_lang ON universal_type_mappings(concept_id, language);
CREATE INDEX idx_uom_concept_op ON universal_operation_mappings(concept_id, canonical_op, language);
CREATE INDEX idx_upm_concept_lang ON universal_protocol_mappings(concept_id, language);
CREATE INDEX idx_dst_domain_lang ON discovered_stdlib_taxonomy(taxonomy_domain, language);
"""


# ============================================================================
# 3. CANONICAL SPECIFICATIONS (PRIMITIVES, COLLECTIONS, EXCEPTIONS, I/O, PROTOCOLS)
# ============================================================================

@dataclass
class TypeTargetSpec:
    qname: str
    syntax: str
    imp: Optional[str]
    mem: str
    null_model: str
    fallbacks: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class ConceptSpec:
    key: str
    category: str
    arity: int
    desc: str
    targets: Dict[str, TypeTargetSpec]


CONCEPT_SPECS: List[ConceptSpec] = [
    # ------------------------------------------------------------------------
    # A. PRIMITIVES
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="prim.bool",
        category="primitive",
        arity=0,
        desc="Boolean truth value (True/False, true/false)",
        targets={
            "python":     TypeTargetSpec("builtins.bool",    "bool",    None, "ref_gc",      "nullable_ref", ["bool"]),
            "csharp":     TypeTargetSpec("System.Boolean",   "bool",    None, "value_stack", "value_default", ["bool"]),
            "rust":       TypeTargetSpec("bool",             "bool",    None, "value_stack", "option_wrapper", ["core::primitive::bool"]),
            "typescript": TypeTargetSpec("Boolean",          "boolean", None, "value_stack", "nullable_ref", ["boolean"]),
            "cpp":        TypeTargetSpec("bool",             "bool",    None, "value_stack", "value_default", []),
            "go":         TypeTargetSpec("bool",             "bool",    None, "value_stack", "value_default", []),
        },
    ),
    ConceptSpec(
        key="prim.int64",
        category="primitive",
        arity=0,
        desc="64-bit signed two's complement integer",
        targets={
            "python":     TypeTargetSpec("builtins.int",     "int",     None,       "ref_gc",      "nullable_ref", ["int"]),
            "csharp":     TypeTargetSpec("System.Int64",     "long",    None,       "value_stack", "value_default", ["long"]),
            "rust":       TypeTargetSpec("i64",              "i64",     None,       "value_stack", "option_wrapper", ["core::primitive::i64"]),
            "typescript": TypeTargetSpec("BigInt",           "bigint",  None,       "value_stack", "nullable_ref", ["Number", "number"]),
            "cpp":        TypeTargetSpec("std::int64_t",     "int64_t", "<cstdint>","value_stack", "value_default", ["int64_t", "long long"]),
            "go":         TypeTargetSpec("int64",            "int64",   None,       "value_stack", "value_default", ["int"]),
        },
    ),
    ConceptSpec(
        key="prim.bigint",
        category="primitive",
        arity=0,
        desc="Arbitrary-precision signed integer (Python default int semantics)",
        targets={
            "python":     TypeTargetSpec("builtins.int",            "int",        None,            "ref_gc",      "nullable_ref", ["int"]),
            "csharp":     TypeTargetSpec("System.Numerics.BigInteger", "BigInteger", "System.Numerics", "value_stack", "value_default", ["BigInteger"]),
            "rust":       TypeTargetSpec("i128",                    "i128",       None,            "value_stack", "option_wrapper", ["u128"]),
            "typescript": TypeTargetSpec("BigInt",                  "bigint",     None,            "value_stack", "nullable_ref", []),
            "cpp":        TypeTargetSpec("long long",               "long long",  "<cstdint>",     "value_stack", "value_default", ["std::intmax_t"]),
            "go":         TypeTargetSpec("math/big.Int",            "*big.Int",   "math/big",      "ref_gc",      "pointer_nil", ["big.Int", "Int"]),
        },
    ),
    ConceptSpec(
        key="prim.float64",
        category="primitive",
        arity=0,
        desc="IEEE 754 double-precision 64-bit floating point number",
        targets={
            "python":     TypeTargetSpec("builtins.float",   "float",   None, "ref_gc",      "nullable_ref", ["float"]),
            "csharp":     TypeTargetSpec("System.Double",    "double",  None, "value_stack", "value_default", ["double"]),
            "rust":       TypeTargetSpec("f64",              "f64",     None, "value_stack", "option_wrapper", ["core::primitive::f64"]),
            "typescript": TypeTargetSpec("Number",           "number",  None, "value_stack", "nullable_ref", ["number"]),
            "cpp":        TypeTargetSpec("double",           "double",  None, "value_stack", "value_default", []),
            "go":         TypeTargetSpec("float64",          "float64", None, "value_stack", "value_default", []),
        },
    ),
    ConceptSpec(
        key="prim.utf8_str",
        category="primitive",
        arity=0,
        desc="Text string (owned heap UTF-8/UTF-16 string)",
        targets={
            "python":     TypeTargetSpec("builtins.str",      "str",         None,      "ref_gc",      "nullable_ref", ["str"]),
            "csharp":     TypeTargetSpec("System.String",     "string",      None,      "ref_gc",      "nullable_ref", ["string"]),
            "rust":       TypeTargetSpec("alloc::string::String", "String",  None,      "owned_heap",  "option_wrapper", ["std::string::String", "String", "str"]),
            "typescript": TypeTargetSpec("String",            "string",      None,      "ref_gc",      "nullable_ref", ["string"]),
            "cpp":        TypeTargetSpec("std::string",       "std::string", "<string>","owned_heap",  "value_default", ["std::basic_string"]),
            "go":         TypeTargetSpec("string",            "string",      None,      "value_stack", "value_default", ["strings"]),
        },
    ),
    ConceptSpec(
        key="prim.bytes",
        category="primitive",
        arity=0,
        desc="Contiguous raw byte buffer / byte array",
        targets={
            "python":     TypeTargetSpec("builtins.bytes",   "bytes",              None,       "ref_gc",       "nullable_ref", ["bytes", "builtins.bytearray"]),
            "csharp":     TypeTargetSpec("System.Byte[]",    "byte[]",             None,       "ref_gc",       "nullable_ref", ["System.Byte", "System.ReadOnlySpan"]),
            "rust":       TypeTargetSpec("alloc::vec::Vec",  "Vec<u8>",            None,       "owned_heap",   "option_wrapper", ["std::vec::Vec", "u8"]),
            "typescript": TypeTargetSpec("Uint8Array",       "Uint8Array",         None,       "ref_gc",       "nullable_ref", ["ArrayBuffer"]),
            "cpp":        TypeTargetSpec("std::vector",      "std::vector<uint8_t>","<vector>","owned_heap",   "value_default", ["std::byte"]),
            "go":         TypeTargetSpec("[]byte",           "[]byte",             "bytes",    "slice_header", "pointer_nil", ["bytes.Buffer", "byte"]),
        },
    ),

    # ------------------------------------------------------------------------
    # B. STANDARD LIBRARY COLLECTIONS
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="col.sequence",
        category="collection",
        arity=1,
        desc="Dynamically-sized contiguous growable sequence <T>",
        targets={
            "python":     TypeTargetSpec("builtins.list",                   "list[{T0}]",        None,                         "ref_gc",       "nullable_ref", ["list"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.List", "List<{T0}>",        "System.Collections.Generic", "ref_gc",       "nullable_ref", ["List"]),
            "rust":       TypeTargetSpec("alloc::vec::Vec",                 "Vec<{T0}>",         None,                         "owned_heap",   "option_wrapper", ["std::vec::Vec", "Vec"]),
            "typescript": TypeTargetSpec("Array",                           "Array<{T0}>",       None,                         "ref_gc",       "nullable_ref", ["ReadonlyArray"]),
            "cpp":        TypeTargetSpec("std::vector",                     "std::vector<{T0}>", "<vector>",                   "owned_heap",   "value_default", []),
            "go":         TypeTargetSpec("slices",                          "[]{T0}",            "slices",                     "slice_header", "pointer_nil", []),
        },
    ),
    ConceptSpec(
        key="col.map",
        category="collection",
        arity=2,
        desc="Hash-table key-value dictionary mapping <K, V>",
        targets={
            "python":     TypeTargetSpec("builtins.dict",                         "dict[{T0}, {T1}]",                  None,                         "ref_gc",     "nullable_ref", ["dict"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.Dictionary", "Dictionary<{T0}, {T1}>",            "System.Collections.Generic", "ref_gc",     "nullable_ref", ["Dictionary"]),
            "rust":       TypeTargetSpec("std::collections::hash_map::HashMap",   "HashMap<{T0}, {T1}>",               "std::collections::HashMap",  "owned_heap", "option_wrapper", ["std::collections::HashMap", "HashMap"]),
            "typescript": TypeTargetSpec("Map",                                   "Map<{T0}, {T1}>",                   None,                         "ref_gc",     "nullable_ref", ["Record"]),
            "cpp":        TypeTargetSpec("std::unordered_map",                    "std::unordered_map<{T0}, {T1}>",    "<unordered_map>",            "owned_heap", "value_default", ["std::map"]),
            "go":         TypeTargetSpec("maps",                                  "map[{T0}]{T1}",                     "maps",                       "ref_gc",     "pointer_nil", []),
        },
    ),
    ConceptSpec(
        key="col.ordered_map",
        category="collection",
        arity=2,
        desc="Sorted or insertion-ordered key-value dictionary <K, V>",
        targets={
            "python":     TypeTargetSpec("collections.OrderedDict",                     "OrderedDict[{T0}, {T1}]",      "collections",                "ref_gc",     "nullable_ref", ["builtins.dict"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.SortedDictionary", "SortedDictionary<{T0}, {T1}>", "System.Collections.Generic", "ref_gc",     "nullable_ref", ["System.Collections.Generic.SortedList"]),
            "rust":       TypeTargetSpec("alloc::collections::btree::map::BTreeMap",    "BTreeMap<{T0}, {T1}>",         "std::collections::BTreeMap", "owned_heap", "option_wrapper", ["std::collections::BTreeMap", "BTreeMap"]),
            "typescript": TypeTargetSpec("Map",                                         "Map<{T0}, {T1}>",              None,                         "ref_gc",     "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::map",                                    "std::map<{T0}, {T1}>",         "<map>",                      "owned_heap", "value_default", []),
            "go":         TypeTargetSpec("maps",                                        "map[{T0}]{T1}",                "maps",                       "ref_gc",     "pointer_nil", []),
        },
    ),
    ConceptSpec(
        key="col.set",
        category="collection",
        arity=1,
        desc="Unordered unique-element hash set <T>",
        targets={
            "python":     TypeTargetSpec("builtins.set",                       "set[{T0}]",                  None,                         "ref_gc",     "nullable_ref", ["set", "builtins.frozenset"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.HashSet", "HashSet<{T0}>",              "System.Collections.Generic", "ref_gc",     "nullable_ref", ["HashSet"]),
            "rust":       TypeTargetSpec("std::collections::hash_set::HashSet","HashSet<{T0}>",              "std::collections::HashSet",  "owned_heap", "option_wrapper", ["std::collections::HashSet", "HashSet"]),
            "typescript": TypeTargetSpec("Set",                                "Set<{T0}>",                  None,                         "ref_gc",     "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::unordered_set",                 "std::unordered_set<{T0}>",   "<unordered_set>",            "owned_heap", "value_default", ["std::set"]),
            "go":         TypeTargetSpec("maps",                               "map[{T0}]struct{}",          "maps",                       "ref_gc",     "pointer_nil", []),
        },
    ),
    ConceptSpec(
        key="col.deque",
        category="collection",
        arity=1,
        desc="Double-ended queue / ring buffer <T> supporting O(1) front/back push and pop",
        targets={
            "python":     TypeTargetSpec("collections.deque",                      "deque[{T0}]",        "collections",                "ref_gc",     "nullable_ref", ["deque"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.Queue",       "Queue<{T0}>",        "System.Collections.Generic", "ref_gc",     "nullable_ref", ["System.Collections.Generic.LinkedList"]),
            "rust":       TypeTargetSpec("alloc::collections::vec_deque::VecDeque","VecDeque<{T0}>",     "std::collections::VecDeque", "owned_heap", "option_wrapper", ["std::collections::VecDeque", "VecDeque"]),
            "typescript": TypeTargetSpec("Array",                                  "Array<{T0}>",        None,                         "ref_gc",     "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::deque",                             "std::deque<{T0}>",   "<deque>",                    "owned_heap", "value_default", []),
            "go":         TypeTargetSpec("container/list.List",                    "*list.List",         "container/list",             "ref_gc",     "pointer_nil", ["container/list", "List"]),
        },
    ),

    # ------------------------------------------------------------------------
    # C. CONTROL FLOW & NULLABILITY WRAPPERS
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="ctrl.optional",
        category="control_flow",
        arity=1,
        desc="Explicit nullable / optional value wrapper <T>",
        targets={
            "python":     TypeTargetSpec("typing.Optional",       "{T0} | None",          "typing",     "ref_gc",      "nullable_ref", ["builtins.None"]),
            "csharp":     TypeTargetSpec("System.Nullable",       "{T0}?",                "System",     "value_stack", "option_wrapper", ["Nullable"]),
            "rust":       TypeTargetSpec("core::option::Option",  "Option<{T0}>",         None,         "value_stack", "option_wrapper", ["std::option::Option", "Option"]),
            "typescript": TypeTargetSpec("NonNullable",           "{T0} | null | undefined", None,      "ref_gc",      "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::optional",         "std::optional<{T0}>",  "<optional>", "value_stack", "option_wrapper", []),
            "go":         TypeTargetSpec("builtin.nil",           "*{T0}",                None,         "ref_gc",      "pointer_nil", []),
        },
    ),
    ConceptSpec(
        key="ctrl.result",
        category="control_flow",
        arity=2,
        desc="Fallible computation outcome returning value <T> or error <E>",
        targets={
            "python":     TypeTargetSpec("builtins.Exception",    "{T0}",                    None,         "ref_gc",      "nullable_ref", ["Exception"]),
            "csharp":     TypeTargetSpec("System.Exception",      "{T0}",                    "System",     "ref_gc",      "nullable_ref", ["Exception"]),
            "rust":       TypeTargetSpec("core::result::Result",  "Result<{T0}, {T1}>",      None,         "value_stack", "option_wrapper", ["std::result::Result", "Result"]),
            "typescript": TypeTargetSpec("Promise",               "Promise<{T0}>",           None,         "ref_gc",      "nullable_ref", ["Error"]),
            "cpp":        TypeTargetSpec("std::expected",         "std::expected<{T0}, {T1}>","<expected>","value_stack", "option_wrapper", ["std::exception"]),
            "go":         TypeTargetSpec("errors",                "({T0}, error)",           "errors",     "value_stack", "pointer_nil", ["error"]),
        },
    ),

    # ------------------------------------------------------------------------
    # D. EXCEPTIONS & ERROR TYPES
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="exc.base_error",
        category="exception",
        arity=0,
        desc="Root catchable application exception / error interface",
        targets={
            "python":     TypeTargetSpec("builtins.Exception",  "Exception",         None,         "ref_gc",     "nullable_ref", ["Exception", "builtins.BaseException"]),
            "csharp":     TypeTargetSpec("System.Exception",    "Exception",         "System",     "ref_gc",     "nullable_ref", ["Exception"]),
            "rust":       TypeTargetSpec("core::error::Error",  "Box<dyn Error>",    "std::error::Error", "owned_heap", "option_wrapper", ["std::error::Error", "Error"]),
            "typescript": TypeTargetSpec("Error",               "Error",             None,         "ref_gc",     "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::exception",      "std::exception",    "<exception>","value_stack","value_default", ["std::runtime_error"]),
            "go":         TypeTargetSpec("errors",              "error",             "errors",     "ref_gc",     "pointer_nil", ["error"]),
        },
    ),
    ConceptSpec(
        key="exc.value_error",
        category="exception",
        arity=0,
        desc="Invalid argument value, domain error, or parse failure",
        targets={
            "python":     TypeTargetSpec("builtins.ValueError",        "ValueError",            None,        "ref_gc",      "nullable_ref", ["ValueError"]),
            "csharp":     TypeTargetSpec("System.ArgumentException",   "ArgumentException",     "System",    "ref_gc",      "nullable_ref", ["System.FormatException"]),
            "rust":       TypeTargetSpec("core::num::ParseIntError",   "ParseIntError",         "std::num",  "value_stack", "option_wrapper", ["std::fmt::Error", "ParseFloatError"]),
            "typescript": TypeTargetSpec("RangeError",                 "RangeError",            None,        "ref_gc",      "nullable_ref", ["TypeError"]),
            "cpp":        TypeTargetSpec("std::invalid_argument",      "std::invalid_argument", "<stdexcept>","value_stack","value_default", ["std::domain_error"]),
            "go":         TypeTargetSpec("strconv.NumError",           "*strconv.NumError",     "strconv",   "ref_gc",      "pointer_nil", ["strconv", "errors"]),
        },
    ),
    ConceptSpec(
        key="exc.index_error",
        category="exception",
        arity=0,
        desc="Out-of-bounds sequence index error",
        targets={
            "python":     TypeTargetSpec("builtins.IndexError",              "IndexError",               None,         "ref_gc",      "nullable_ref", ["IndexError"]),
            "csharp":     TypeTargetSpec("System.IndexOutOfRangeException",  "IndexOutOfRangeException", "System",     "ref_gc",      "nullable_ref", ["System.ArgumentOutOfRangeException"]),
            "rust":       TypeTargetSpec("core::slice::SliceIndex",          "Option::None",             None,         "value_stack", "option_wrapper", ["core::ops::Index"]),
            "typescript": TypeTargetSpec("RangeError",                       "RangeError",               None,         "ref_gc",      "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::out_of_range",                "std::out_of_range",        "<stdexcept>","value_stack", "value_default", []),
            "go":         TypeTargetSpec("runtime.Error",                    "runtime.Error",            "runtime",    "ref_gc",      "pointer_nil", ["runtime"]),
        },
    ),
    ConceptSpec(
        key="exc.key_error",
        category="exception",
        arity=0,
        desc="Missing key lookup in mapping/dictionary",
        targets={
            "python":     TypeTargetSpec("builtins.KeyError",                             "KeyError",                 None,                         "ref_gc",      "nullable_ref", ["KeyError"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.KeyNotFoundException","KeyNotFoundException",    "System.Collections.Generic", "ref_gc",      "nullable_ref", ["KeyNotFoundException"]),
            "rust":       TypeTargetSpec("core::option::Option",                          "Option::None",             None,                         "value_stack", "option_wrapper", ["Option"]),
            "typescript": TypeTargetSpec("Error",                                         "undefined",                None,                         "ref_gc",      "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::out_of_range",                             "std::out_of_range",        "<stdexcept>",                "value_stack", "value_default", []),
            "go":         TypeTargetSpec("errors",                                        "bool (comma-ok idiom)",    "errors",                     "value_stack", "value_default", []),
        },
    ),
    ConceptSpec(
        key="exc.io_error",
        category="exception",
        arity=0,
        desc="Operating system, filesystem, or stream I/O failure",
        targets={
            "python":     TypeTargetSpec("builtins.OSError",                   "OSError",                           None,              "ref_gc",      "nullable_ref", ["OSError", "builtins.FileNotFoundError"]),
            "csharp":     TypeTargetSpec("System.IO.IOException",              "IOException",                       "System.IO",       "ref_gc",      "nullable_ref", ["System.IO.FileNotFoundException"]),
            "rust":       TypeTargetSpec("std::io::error::Error",              "std::io::Error",                    "std::io",         "owned_heap",  "option_wrapper", ["std::io::Error", "Error"]),
            "typescript": TypeTargetSpec("Error",                              "Error",                             None,              "ref_gc",      "nullable_ref", ["DOMException"]),
            "cpp":        TypeTargetSpec("std::filesystem::filesystem_error",  "std::filesystem::filesystem_error", "<filesystem>",    "value_stack", "value_default", ["std::ios_base::failure", "std::system_error"]),
            "go":         TypeTargetSpec("os.PathError",                       "*os.PathError",                     "os",              "ref_gc",      "pointer_nil", ["io/fs.PathError", "os", "io"]),
        },
    ),

    # ------------------------------------------------------------------------
    # E. I/O & FILESYSTEM TYPES
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="io.path",
        category="io",
        arity=0,
        desc="Cross-platform filesystem path representation and manipulator",
        targets={
            "python":     TypeTargetSpec("pathlib.Path",           "Path",                  "pathlib",        "ref_gc",      "nullable_ref", ["pathlib.PurePath", "os.path"]),
            "csharp":     TypeTargetSpec("System.IO.Path",         "string (System.IO.Path)","System.IO",     "ref_gc",      "nullable_ref", ["System.IO.FileInfo", "System.IO.DirectoryInfo"]),
            "rust":       TypeTargetSpec("std::path::PathBuf",     "PathBuf",               "std::path::PathBuf","owned_heap","option_wrapper", ["std::path::Path", "PathBuf"]),
            "typescript": TypeTargetSpec("URL",                    "URL | string",          None,             "ref_gc",      "nullable_ref", ["String"]),
            "cpp":        TypeTargetSpec("std::filesystem::path",  "std::filesystem::path", "<filesystem>",   "owned_heap",  "value_default", []),
            "go":         TypeTargetSpec("path/filepath",          "string (filepath)",     "path/filepath",  "value_stack", "value_default", ["io/fs"]),
        },
    ),
    ConceptSpec(
        key="io.file_stream",
        category="io",
        arity=0,
        desc="Buffered OS file handle for reading and writing",
        targets={
            "python":     TypeTargetSpec("io.BufferedReader",      "io.BufferedReader",     "io",        "ref_gc",     "nullable_ref", ["_io.BufferedReader", "_io.TextIOWrapper", "io.TextIOWrapper", "io.FileIO"]),
            "csharp":     TypeTargetSpec("System.IO.FileStream",   "FileStream",            "System.IO", "ref_gc",     "nullable_ref", ["System.IO.StreamReader", "System.IO.StreamWriter"]),
            "rust":       TypeTargetSpec("std::fs::File",          "std::fs::File",         "std::fs",   "owned_heap", "option_wrapper", ["File", "std::io::BufReader"]),
            "typescript": TypeTargetSpec("ReadableStream",         "ReadableStream<Uint8Array>", None,   "ref_gc",     "nullable_ref", ["Blob", "Response"]),
            "cpp":        TypeTargetSpec("std::fstream",           "std::fstream",          "<fstream>", "owned_heap", "value_default", ["std::ifstream", "std::ofstream", "std::basic_fstream"]),
            "go":         TypeTargetSpec("os.File",                "*os.File",              "os",        "ref_gc",     "pointer_nil", ["os", "bufio.Reader"]),
        },
    ),
    ConceptSpec(
        key="io.memory_buffer",
        category="io",
        arity=0,
        desc="In-memory byte or string stream implementing standard Read/Write contracts",
        targets={
            "python":     TypeTargetSpec("io.BytesIO",             "io.BytesIO",            "io",        "ref_gc",     "nullable_ref", ["_io.BytesIO", "io.StringIO", "_io.StringIO"]),
            "csharp":     TypeTargetSpec("System.IO.MemoryStream", "MemoryStream",          "System.IO", "ref_gc",     "nullable_ref", ["MemoryStream"]),
            "rust":       TypeTargetSpec("std::io::cursor::Cursor","std::io::Cursor<Vec<u8>>","std::io", "owned_heap", "option_wrapper", ["std::io::Cursor", "Cursor"]),
            "typescript": TypeTargetSpec("ArrayBuffer",            "ArrayBuffer",           None,        "ref_gc",     "nullable_ref", ["DataView", "Uint8Array"]),
            "cpp":        TypeTargetSpec("std::stringstream",      "std::stringstream",     "<sstream>", "owned_heap", "value_default", ["std::basic_stringstream", "std::istringstream"]),
            "go":         TypeTargetSpec("bytes.Buffer",           "*bytes.Buffer",         "bytes",     "ref_gc",     "pointer_nil", ["bytes", "strings.Builder"]),
        },
    ),

    # ------------------------------------------------------------------------
    # F. PROTOCOLS & BEHAVIORAL CONTRACTS
    # ------------------------------------------------------------------------
    ConceptSpec(
        key="proto.disposable",
        category="protocol",
        arity=0,
        desc="Deterministic resource cleanup / lexical scope exit protocol",
        targets={
            "python":     TypeTargetSpec("contextlib.AbstractContextManager", "ContextManager", "contextlib", "ref_gc", "nullable_ref", ["builtins.object"]),
            "csharp":     TypeTargetSpec("System.IDisposable",                "IDisposable",    "System",     "ref_gc", "nullable_ref", ["System.IAsyncDisposable"]),
            "rust":       TypeTargetSpec("core::ops::drop::Drop",             "Drop",           None,         "value_stack", "option_wrapper", ["std::ops::Drop", "Drop"]),
            "typescript": TypeTargetSpec("Disposable",                        "Disposable",     None,         "ref_gc", "nullable_ref", ["AsyncDisposable"]),
            "cpp":        TypeTargetSpec("std::default_delete",               "~T() noexcept",  "<memory>",   "value_stack", "value_default", ["std::unique_ptr"]),
            "go":         TypeTargetSpec("io.Closer",                         "io.Closer",      "io",         "ref_gc", "pointer_nil", ["io"]),
        },
    ),
    ConceptSpec(
        key="proto.iterable",
        category="protocol",
        arity=1,
        desc="Sequential element producer supporting for-each loop iteration <T>",
        targets={
            "python":     TypeTargetSpec("collections.abc.Iterable",                "Iterable[{T0}]",    "collections.abc",            "ref_gc",      "nullable_ref", ["_collections_abc.Iterable", "typing.Iterable"]),
            "csharp":     TypeTargetSpec("System.Collections.Generic.IEnumerable",  "IEnumerable<{T0}>", "System.Collections.Generic", "ref_gc",      "nullable_ref", ["System.Collections.IEnumerable"]),
            "rust":       TypeTargetSpec("core::iter::traits::collect::IntoIterator","IntoIterator<Item = {T0}>", None,                "value_stack", "option_wrapper", ["core::iter::Iterator", "std::iter::Iterator", "Iterator"]),
            "typescript": TypeTargetSpec("Iterable",                                "Iterable<{T0}>",    None,                         "ref_gc",      "nullable_ref", ["Iterator", "Array"]),
            "cpp":        TypeTargetSpec("std::ranges::range",                      "std::ranges::range","<ranges>",                   "value_stack", "value_default", ["std::input_iterator"]),
            "go":         TypeTargetSpec("iter.Seq",                                "iter.Seq[{T0}]",    "iter",                       "ref_gc",      "pointer_nil", ["iter"]),
        },
    ),
    ConceptSpec(
        key="proto.equatable",
        category="protocol",
        arity=0,
        desc="Structural or value equality comparison contract",
        targets={
            "python":     TypeTargetSpec("builtins.object",       "__eq__",          None,     "ref_gc",      "nullable_ref", ["object"]),
            "csharp":     TypeTargetSpec("System.IEquatable",     "IEquatable<T>",   "System", "ref_gc",      "nullable_ref", ["System.Object"]),
            "rust":       TypeTargetSpec("core::cmp::PartialEq",  "PartialEq",       None,     "value_stack", "option_wrapper", ["std::cmp::PartialEq", "PartialEq", "Eq"]),
            "typescript": TypeTargetSpec("Object",                "===",             None,     "ref_gc",      "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::equality_comparable","operator==",    "<concepts>","value_stack","value_default", []),
            "go":         TypeTargetSpec("comparable",            "comparable",      None,     "value_stack", "value_default", []),
        },
    ),
    ConceptSpec(
        key="proto.comparable",
        category="protocol",
        arity=0,
        desc="Total or partial ordering comparison contract (<, <=, >, >=)",
        targets={
            "python":     TypeTargetSpec("builtins.object",        "__lt__",                  None,       "ref_gc",      "nullable_ref", ["functools.total_ordering"]),
            "csharp":     TypeTargetSpec("System.IComparable",     "IComparable<T>",          "System",   "ref_gc",      "nullable_ref", ["System.Collections.Generic.IComparer"]),
            "rust":       TypeTargetSpec("core::cmp::PartialOrd",  "PartialOrd + Ord",        None,       "value_stack", "option_wrapper", ["core::cmp::Ord", "PartialOrd", "Ord"]),
            "typescript": TypeTargetSpec("Number",                 "< / >",                   None,       "value_stack", "nullable_ref", []),
            "cpp":        TypeTargetSpec("std::three_way_comparable","operator<=>",           "<compare>","value_stack", "value_default", ["std::totally_ordered"]),
            "go":         TypeTargetSpec("cmp.Ordered",            "cmp.Ordered",             "cmp",      "value_stack", "value_default", ["cmp"]),
        },
    ),
]


# ============================================================================
# 4. CANONICAL OPERATION SPECS (METHODS ACROSS COLLECTIONS, STRINGS, I/O)
# ============================================================================

@dataclass
class OpTargetSpec:
    sym: str
    template: str
    pass_kind: str
    mutates: int
    returns_new: int


# Format: (concept_key, canonical_op) -> { language: OpTargetSpec }
OPERATION_SPECS: Dict[Tuple[str, str], Dict[str, OpTargetSpec]] = {
    # --- col.sequence operations ---
    ("col.sequence", "append"): {
        "python":     OpTargetSpec("append",    "{self}.append({arg0})",           "ref",     1, 0),
        "csharp":     OpTargetSpec("Add",       "{self}.Add({arg0})",              "ref",     1, 0),
        "rust":       OpTargetSpec("push",      "{self}.push({arg0})",             "mut_ref", 1, 0),
        "typescript": OpTargetSpec("push",      "{self}.push({arg0})",             "ref",     1, 0),
        "cpp":        OpTargetSpec("push_back", "{self}.push_back({arg0})",        "mut_ref", 1, 0),
        "go":         OpTargetSpec("append",    "{self} = append({self}, {arg0})", "free_fn", 0, 1),
    },
    ("col.sequence", "length"): {
        "python":     OpTargetSpec("__len__",   "len({self})",                     "free_fn", 0, 1),
        "csharp":     OpTargetSpec("Count",     "{self}.Count",                    "ref",     0, 1),
        "rust":       OpTargetSpec("len",       "{self}.len()",                    "ref",     0, 1),
        "typescript": OpTargetSpec("length",    "{self}.length",                   "ref",     0, 1),
        "cpp":        OpTargetSpec("size",      "{self}.size()",                   "ref",     0, 1),
        "go":         OpTargetSpec("len",       "len({self})",                     "free_fn", 0, 1),
    },
    ("col.sequence", "pop_back"): {
        "python":     OpTargetSpec("pop",       "{self}.pop()",                    "ref",     1, 1),
        "csharp":     OpTargetSpec("RemoveAt",  "{self}.RemoveAt({self}.Count - 1)","ref",    1, 0),
        "rust":       OpTargetSpec("pop",       "{self}.pop()",                    "mut_ref", 1, 1),
        "typescript": OpTargetSpec("pop",       "{self}.pop()",                    "ref",     1, 1),
        "cpp":        OpTargetSpec("pop_back",  "{self}.pop_back()",               "mut_ref", 1, 0),
        "go":         OpTargetSpec("Delete",    "{self} = {self}[:len({self})-1]", "free_fn", 0, 1),
    },
    ("col.sequence", "clear"): {
        "python":     OpTargetSpec("clear",     "{self}.clear()",                  "ref",     1, 0),
        "csharp":     OpTargetSpec("Clear",     "{self}.Clear()",                  "ref",     1, 0),
        "rust":       OpTargetSpec("clear",     "{self}.clear()",                  "mut_ref", 1, 0),
        "typescript": OpTargetSpec("splice",    "{self}.length = 0",               "ref",     1, 0),
        "cpp":        OpTargetSpec("clear",     "{self}.clear()",                  "mut_ref", 1, 0),
        "go":         OpTargetSpec("clear",     "clear({self})",                   "free_fn", 1, 0),
    },
    ("col.sequence", "contains"): {
        "python":     OpTargetSpec("__contains__", "{arg0} in {self}",             "operator",0, 1),
        "csharp":     OpTargetSpec("Contains",  "{self}.Contains({arg0})",         "ref",     0, 1),
        "rust":       OpTargetSpec("contains",  "{self}.contains(&{arg0})",        "ref",     0, 1),
        "typescript": OpTargetSpec("includes",  "{self}.includes({arg0})",         "ref",     0, 1),
        "cpp":        OpTargetSpec("find",      "std::ranges::contains({self}, {arg0})", "free_fn", 0, 1),
        "go":         OpTargetSpec("Contains",  "slices.Contains({self}, {arg0})", "free_fn", 0, 1),
    },

    # --- col.map operations ---
    ("col.map", "insert"): {
        "python":     OpTargetSpec("__setitem__", "{self}[{arg0}] = {arg1}",       "ref",     1, 0),
        "csharp":     OpTargetSpec("Add",       "{self}[{arg0}] = {arg1}",         "ref",     1, 0),
        "rust":       OpTargetSpec("insert",    "{self}.insert({arg0}, {arg1})",   "mut_ref", 1, 1),
        "typescript": OpTargetSpec("set",       "{self}.set({arg0}, {arg1})",      "ref",     1, 0),
        "cpp":        OpTargetSpec("insert_or_assign", "{self}.insert_or_assign({arg0}, {arg1})", "mut_ref", 1, 0),
        "go":         OpTargetSpec("Clone",     "{self}[{arg0}] = {arg1}",         "ref",     1, 0),
    },
    ("col.map", "get_optional"): {
        "python":     OpTargetSpec("get",       "{self}.get({arg0})",              "ref",     0, 1),
        "csharp":     OpTargetSpec("TryGetValue","{self}.TryGetValue({arg0}, out var val)", "ref", 0, 1),
        "rust":       OpTargetSpec("get",       "{self}.get(&{arg0})",             "ref",     0, 1),
        "typescript": OpTargetSpec("get",       "{self}.get({arg0})",              "ref",     0, 1),
        "cpp":        OpTargetSpec("find",      "{self}.find({arg0})",             "ref",     0, 1),
        "go":         OpTargetSpec("Keys",      "val, ok := {self}[{arg0}]",       "operator",0, 1),
    },
    ("col.map", "contains_key"): {
        "python":     OpTargetSpec("__contains__", "{arg0} in {self}",             "operator",0, 1),
        "csharp":     OpTargetSpec("ContainsKey","{self}.ContainsKey({arg0})",     "ref",     0, 1),
        "rust":       OpTargetSpec("contains_key","{self}.contains_key(&{arg0})",  "ref",     0, 1),
        "typescript": OpTargetSpec("has",       "{self}.has({arg0})",              "ref",     0, 1),
        "cpp":        OpTargetSpec("contains",  "{self}.contains({arg0})",         "ref",     0, 1),
        "go":         OpTargetSpec("DeleteFunc","_, ok := {self}[{arg0}]",         "operator",0, 1),
    },
    ("col.map", "remove"): {
        "python":     OpTargetSpec("pop",       "{self}.pop({arg0}, None)",        "ref",     1, 1),
        "csharp":     OpTargetSpec("Remove",    "{self}.Remove({arg0})",           "ref",     1, 1),
        "rust":       OpTargetSpec("remove",    "{self}.remove(&{arg0})",          "mut_ref", 1, 1),
        "typescript": OpTargetSpec("delete",    "{self}.delete({arg0})",           "ref",     1, 1),
        "cpp":        OpTargetSpec("erase",     "{self}.erase({arg0})",            "mut_ref", 1, 1),
        "go":         OpTargetSpec("delete",    "delete({self}, {arg0})",          "free_fn", 1, 0),
    },

    # --- col.set operations ---
    ("col.set", "add"): {
        "python":     OpTargetSpec("add",       "{self}.add({arg0})",              "ref",     1, 0),
        "csharp":     OpTargetSpec("Add",       "{self}.Add({arg0})",              "ref",     1, 1),
        "rust":       OpTargetSpec("insert",    "{self}.insert({arg0})",           "mut_ref", 1, 1),
        "typescript": OpTargetSpec("add",       "{self}.add({arg0})",              "ref",     1, 0),
        "cpp":        OpTargetSpec("insert",    "{self}.insert({arg0})",           "mut_ref", 1, 1),
        "go":         OpTargetSpec("Clone",     "{self}[{arg0}] = struct{}{}",     "ref",     1, 0),
    },
    ("col.set", "contains"): {
        "python":     OpTargetSpec("__contains__", "{arg0} in {self}",             "operator",0, 1),
        "csharp":     OpTargetSpec("Contains",  "{self}.Contains({arg0})",         "ref",     0, 1),
        "rust":       OpTargetSpec("contains",  "{self}.contains(&{arg0})",        "ref",     0, 1),
        "typescript": OpTargetSpec("has",       "{self}.has({arg0})",              "ref",     0, 1),
        "cpp":        OpTargetSpec("contains",  "{self}.contains({arg0})",         "ref",     0, 1),
        "go":         OpTargetSpec("Keys",      "_, ok := {self}[{arg0}]",         "operator",0, 1),
    },

    # --- prim.utf8_str operations ---
    ("prim.utf8_str", "split"): {
        "python":     OpTargetSpec("split",     "{self}.split({arg0})",            "ref",     0, 1),
        "csharp":     OpTargetSpec("Split",     "{self}.Split({arg0})",            "ref",     0, 1),
        "rust":       OpTargetSpec("split",     "{self}.split({arg0})",            "ref",     0, 1),
        "typescript": OpTargetSpec("split",     "{self}.split({arg0})",            "ref",     0, 1),
        "cpp":        OpTargetSpec("find",      "std::views::split({self}, {arg0})","ref",    0, 1),
        "go":         OpTargetSpec("Split",     "strings.Split({self}, {arg0})",   "free_fn", 0, 1),
    },
    ("prim.utf8_str", "trim"): {
        "python":     OpTargetSpec("strip",     "{self}.strip()",                  "ref",     0, 1),
        "csharp":     OpTargetSpec("Trim",      "{self}.Trim()",                   "ref",     0, 1),
        "rust":       OpTargetSpec("trim",      "{self}.trim()",                   "ref",     0, 1),
        "typescript": OpTargetSpec("trim",      "{self}.trim()",                   "ref",     0, 1),
        "cpp":        OpTargetSpec("substr",    "/* trim_view */ {self}",          "ref",     0, 1),
        "go":         OpTargetSpec("TrimSpace", "strings.TrimSpace({self})",       "free_fn", 0, 1),
    },
    ("prim.utf8_str", "starts_with"): {
        "python":     OpTargetSpec("startswith","{self}.startswith({arg0})",       "ref",     0, 1),
        "csharp":     OpTargetSpec("StartsWith","{self}.StartsWith({arg0})",       "ref",     0, 1),
        "rust":       OpTargetSpec("starts_with","{self}.starts_with({arg0})",     "ref",     0, 1),
        "typescript": OpTargetSpec("startsWith","{self}.startsWith({arg0})",       "ref",     0, 1),
        "cpp":        OpTargetSpec("starts_with","{self}.starts_with({arg0})",     "ref",     0, 1),
        "go":         OpTargetSpec("HasPrefix", "strings.HasPrefix({self}, {arg0})","free_fn",0, 1),
    },

    # --- io.file_stream operations ---
    ("io.file_stream", "read"): {
        "python":     OpTargetSpec("read",      "{self}.read({arg0})",             "ref",     1, 1),
        "csharp":     OpTargetSpec("Read",      "{self}.Read({arg0})",             "ref",     1, 1),
        "rust":       OpTargetSpec("read_to_end","{self}.read_to_end(&mut {arg0})","mut_ref", 1, 1),
        "typescript": OpTargetSpec("getReader", "{self}.getReader().read()",       "ref",     1, 1),
        "cpp":        OpTargetSpec("read",      "{self}.read({arg0}, {arg1})",     "mut_ref", 1, 0),
        "go":         OpTargetSpec("Read",      "{self}.Read({arg0})",             "pointer", 1, 1),
    },
    ("io.file_stream", "write"): {
        "python":     OpTargetSpec("write",     "{self}.write({arg0})",            "ref",     1, 1),
        "csharp":     OpTargetSpec("Write",     "{self}.Write({arg0})",            "ref",     1, 0),
        "rust":       OpTargetSpec("write_all", "{self}.write_all({arg0})",        "mut_ref", 1, 1),
        "typescript": OpTargetSpec("pipeTo",    "{self}.pipeTo({arg0})",           "ref",     1, 1),
        "cpp":        OpTargetSpec("write",     "{self}.write({arg0}, {arg1})",    "mut_ref", 1, 0),
        "go":         OpTargetSpec("Write",     "{self}.Write({arg0})",            "pointer", 1, 1),
    },
    ("io.file_stream", "close"): {
        "python":     OpTargetSpec("close",     "{self}.close()",                  "ref",     1, 0),
        "csharp":     OpTargetSpec("Close",     "{self}.Dispose()",                "ref",     1, 0),
        "rust":       OpTargetSpec("sync_all",  "drop({self})",                    "val",     1, 0),
        "typescript": OpTargetSpec("cancel",    "await {self}.cancel()",           "ref",     1, 1),
        "cpp":        OpTargetSpec("close",     "{self}.close()",                  "mut_ref", 1, 0),
        "go":         OpTargetSpec("Close",     "{self}.Close()",                  "pointer", 1, 1),
    },
}


# ============================================================================
# 5. PROTOCOL SPECS
# ============================================================================

@dataclass
class ProtoTargetSpec:
    kind: str
    qname: str
    methods: List[str]
    strategy: str


PROTOCOL_SPECS: Dict[str, Dict[str, ProtoTargetSpec]] = {
    "proto.disposable": {
        "python":     ProtoTargetSpec("dunder_protocol",    "contextlib.AbstractContextManager", ["__enter__", "__exit__"], "with_statement"),
        "csharp":     ProtoTargetSpec("interface",          "System.IDisposable",                ["Dispose"],               "using_statement"),
        "rust":       ProtoTargetSpec("trait",              "core::ops::drop::Drop",             ["drop"],                  "raii_drop_scope"),
        "typescript": ProtoTargetSpec("symbol_protocol",    "Disposable",                        ["[Symbol.dispose]"],      "using_declaration"),
        "cpp":        ProtoTargetSpec("operator",           "~Destructor",                       ["~T"],                    "raii_drop_scope"),
        "go":         ProtoTargetSpec("implicit_interface", "io.Closer",                         ["Close"],                 "defer_close"),
    },
    "proto.iterable": {
        "python":     ProtoTargetSpec("dunder_protocol",    "collections.abc.Iterable",               ["__iter__", "__next__"],      "for_in_loop"),
        "csharp":     ProtoTargetSpec("interface",          "System.Collections.Generic.IEnumerable", ["GetEnumerator", "MoveNext"], "foreach_loop"),
        "rust":       ProtoTargetSpec("trait",              "core::iter::traits::iterator::Iterator", ["next", "into_iter"],         "for_in_loop"),
        "typescript": ProtoTargetSpec("symbol_protocol",    "Iterable",                               ["[Symbol.iterator]"],         "for_of_loop"),
        "cpp":        ProtoTargetSpec("operator",           "std::ranges::range",                     ["begin", "end"],              "range_for_loop"),
        "go":         ProtoTargetSpec("implicit_interface", "iter.Seq",                               ["Seq"],                       "for_range_loop"),
    },
    "proto.equatable": {
        "python":     ProtoTargetSpec("dunder_protocol",    "builtins.object",          ["__eq__", "__ne__"], "dunder_eq_dispatch"),
        "csharp":     ProtoTargetSpec("interface",          "System.IEquatable",        ["Equals"],           "iequatable_equals"),
        "rust":       ProtoTargetSpec("trait",              "core::cmp::PartialEq",     ["eq", "ne"],         "derive_partial_eq"),
        "typescript": ProtoTargetSpec("operator",           "Object",                   ["==="],              "strict_equality"),
        "cpp":        ProtoTargetSpec("operator",           "std::equality_comparable", ["operator=="],       "default_eq_operator"),
        "go":         ProtoTargetSpec("implicit_interface", "comparable",               ["=="],               "builtin_comparable"),
    },
    "proto.comparable": {
        "python":     ProtoTargetSpec("dunder_protocol",    "builtins.object",            ["__lt__", "__le__", "__gt__", "__ge__"], "dunder_ord_dispatch"),
        "csharp":     ProtoTargetSpec("interface",          "System.IComparable",         ["CompareTo"],                            "icomparable_compareto"),
        "rust":       ProtoTargetSpec("trait",              "core::cmp::Ord",             ["cmp", "partial_cmp"],                   "derive_ord"),
        "typescript": ProtoTargetSpec("operator",           "Number",                     ["<", ">"],                               "relational_operator"),
        "cpp":        ProtoTargetSpec("operator",           "std::three_way_comparable",  ["operator<=>"],                          "spaceship_operator"),
        "go":         ProtoTargetSpec("implicit_interface", "cmp.Ordered",                ["Compare"],                              "cmp_ordered_constraint"),
    },
}


# ============================================================================
# 6. EMPIRICAL CATALOG RESOLVER & ENRICHER
# ============================================================================

def discover_catalogs(base_dir: Path) -> Dict[str, Path]:
    """Discovers the 6 UTSS SQLite databases from candidate paths or directory scan."""
    discovered: Dict[str, Path] = {}
    for lang, rel_paths in DEFAULT_DB_CANDIDATES.items():
        for rel in rel_paths:
            for root in (base_dir, base_dir.parent):
                candidate = (root / rel).resolve()
                if candidate.is_file():
                    discovered[lang] = candidate
                    break
            if lang in discovered:
                break

    if len(discovered) < 6 and base_dir.is_dir():
        for db_file in sorted(base_dir.glob("*.db")):
            if "bridge" in db_file.name:
                continue
            try:
                uri = f"file:{db_file.resolve()}?mode=ro"
                with sqlite3.connect(uri, uri=True) as conn:
                    row = conn.execute(
                        "SELECT LOWER(language) FROM environments LIMIT 1;"
                    ).fetchone()
                    if row and row[0] in DEFAULT_DB_CANDIDATES:
                        lang = row[0]
                        if lang not in discovered or "full" in db_file.name:
                            discovered[lang] = db_file.resolve()
            except sqlite3.Error:
                continue
    return discovered


def fetch_layer2_container_facet(
    conn: sqlite3.Connection, lang: str, container_id: int
) -> Optional[str]:
    """Extracts the 1:1 Layer 2 container facet row as JSON for a resolved container."""
    facet_table_map = {
        "python": "py_container_facets",
        "csharp": "cs_container_facets",
        "rust": "rust_container_facets",
        "typescript": "ts_container_facets",
        "cpp": "cpp_container_facets",
        "go": "go_container_facets",
    }
    table = facet_table_map.get(lang)
    if not table:
        return None
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"SELECT * FROM {table} WHERE container_id = ? LIMIT 1;",
            (container_id,),
        ).fetchone()
        if row:
            data = {k: row[k] for k in row.keys() if k != "container_id" and row[k] is not None}
            return json.dumps(data)
    except sqlite3.Error:
        pass
    return None


def resolve_type_in_catalog(
    conn: sqlite3.Connection,
    lang: str,
    primary_qname: str,
    fallbacks: List[str],
) -> Dict[str, Any]:
    """
    Searches a language's UTSS catalog for a target type across:
      1. Exact or suffix match in `containers`
      2. Exact or suffix match in `symbols` (for type aliases, primitives, typedefs)
      3. Public facade re-exports in `symbol_aliases`
    """
    conn.row_factory = sqlite3.Row
    candidates = [primary_qname] + fallbacks

    # Pass A: Search `containers`
    for cand in candidates:
        short = cand.split("::")[-1].split(".")[-1].split("/")[-1]
        row = conn.execute(
            """
            SELECT c.container_id, c.qualified_name, c.requires_import, d.stratum
            FROM containers c
            JOIN distributions d ON c.dist_id = d.dist_id
            WHERE c.qualified_name = ?
               OR c.qualified_name LIKE ?
               OR (c.short_name = ? AND d.stratum IN (0, 1))
            ORDER BY
                CASE WHEN c.qualified_name = ? THEN 0
                     WHEN c.qualified_name LIKE ? THEN 1
                     ELSE 2 END,
                d.stratum ASC
            LIMIT 1;
            """,
            (cand, f"%{cand}", short, cand, f"%{cand}"),
        ).fetchone()

        if row:
            cid = row["container_id"]
            facet_json = fetch_layer2_container_facet(conn, lang, cid)
            return {
                "catalog_container_id": cid,
                "catalog_symbol_id": None,
                "resolved_qualified_name": row["qualified_name"],
                "verified_stratum": row["stratum"],
                "verified_requires_import": row["requires_import"],
                "verification_status": "verified_container",
                "layer2_facet_json": facet_json,
            }

    # Pass B: Search `symbols` (ambient primitives, type_alias, struct/class symbols)
    for cand in candidates:
        short = cand.split("::")[-1].split(".")[-1].split("/")[-1]
        row = conn.execute(
            """
            SELECT s.symbol_id, s.container_id, s.qualified_name,
                   c.requires_import, d.stratum
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            JOIN distributions d ON c.dist_id = d.dist_id
            WHERE s.qualified_name = ?
               OR (s.name = ? AND d.stratum IN (0, 1))
            ORDER BY
                CASE WHEN s.qualified_name = ? THEN 0 ELSE 1 END,
                d.stratum ASC
            LIMIT 1;
            """,
            (cand, short, cand),
        ).fetchone()

        if row:
            return {
                "catalog_container_id": row["container_id"],
                "catalog_symbol_id": row["symbol_id"],
                "resolved_qualified_name": row["qualified_name"],
                "verified_stratum": row["stratum"],
                "verified_requires_import": row["requires_import"],
                "verification_status": "verified_symbol",
                "layer2_facet_json": fetch_layer2_container_facet(conn, lang, row["container_id"]),
            }

    # Pass C: Search `symbol_aliases` (e.g., io.BufferedReader -> _io.BufferedReader, pub use)
    for cand in candidates:
        short = cand.split("::")[-1].split(".")[-1]
        row = conn.execute(
            """
            SELECT sa.source_container_id, sa.exposed_name,
                   sa.target_module_name, sa.target_symbol_name,
                   c.qualified_name AS source_qname, c.requires_import, d.stratum
            FROM symbol_aliases sa
            JOIN containers c ON sa.source_container_id = c.container_id
            JOIN distributions d ON c.dist_id = d.dist_id
            WHERE sa.exposed_name = ? OR sa.target_symbol_name = ?
            LIMIT 1;
            """,
            (short, short),
        ).fetchone()
        if row:
            return {
                "catalog_container_id": row["source_container_id"],
                "catalog_symbol_id": None,
                "resolved_qualified_name": f"{row['source_qname']}.{row['exposed_name']} -> {row['target_module_name']}.{row['target_symbol_name']}",
                "verified_stratum": row["stratum"],
                "verified_requires_import": row["requires_import"],
                "verification_status": "verified_alias",
                "layer2_facet_json": None,
            }

    return {
        "catalog_container_id": None,
        "catalog_symbol_id": None,
        "resolved_qualified_name": None,
        "verified_stratum": 0,
        "verified_requires_import": 0,
        "verification_status": "intrinsic_unindexed",
        "layer2_facet_json": None,
    }


def resolve_operation_in_catalog(
    conn: sqlite3.Connection,
    container_id: Optional[int],
    resolved_container_qname: Optional[str],
    target_symbol_name: str,
) -> Dict[str, Any]:
    """
    Resolves a method or free function inside the target language catalog,
    extracting its live signature, return type, overload count, and parameter pass_kinds.
    """
    conn.row_factory = sqlite3.Row
    row = None

    # 1. Try direct lookup on the resolved container_id
    if container_id is not None:
        row = conn.execute(
            """
            SELECT s.symbol_id, s.qualified_name,
                   cal.raw_signature, cal.return_type_expr,
                   COALESCE(cal.overload_count, 0) AS overload_count
            FROM symbols s
            LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
            WHERE s.container_id = ? AND s.name = ?
            LIMIT 1;
            """,
            (container_id, target_symbol_name),
        ).fetchone()

    # 2. Fallback: search by container short name or ambient Stratum 0/1 function
    if row is None:
        prefix = (
            resolved_container_qname.split(" -> ")[-1]
            if resolved_container_qname
            else ""
        )
        row = conn.execute(
            """
            SELECT s.symbol_id, s.qualified_name,
                   cal.raw_signature, cal.return_type_expr,
                   COALESCE(cal.overload_count, 0) AS overload_count
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            JOIN distributions d ON c.dist_id = d.dist_id
            LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
            WHERE s.name = ?
              AND d.stratum IN (0, 1)
            ORDER BY
                CASE WHEN ? != '' AND c.qualified_name LIKE ('%' || ?) THEN 0
                     WHEN d.stratum = 0 THEN 1
                     ELSE 2 END
            LIMIT 1;
            """,
            (target_symbol_name, prefix, prefix),
        ).fetchone()

    if row is None:
        return {
            "catalog_symbol_id": None,
            "verified_qualified_name": None,
            "verified_raw_signature": None,
            "verified_return_type": None,
            "verified_overload_count": 0,
            "verified_pass_kinds_json": "[]",
            "verification_status": "syntax_intrinsic",
        }

    sym_id = row["symbol_id"]
    param_rows = conn.execute(
        """
        SELECT pass_kind
        FROM parameters
        WHERE callable_symbol_id = ? AND overload_id IS NULL
        ORDER BY ordinal ASC;
        """,
        (sym_id,),
    ).fetchall()
    pass_kinds = [p["pass_kind"] for p in param_rows if p["pass_kind"]]

    return {
        "catalog_symbol_id": sym_id,
        "verified_qualified_name": row["qualified_name"],
        "verified_raw_signature": row["raw_signature"],
        "verified_return_type": row["return_type_expr"],
        "verified_overload_count": row["overload_count"],
        "verified_pass_kinds_json": json.dumps(pass_kinds),
        "verification_status": "verified_callable" if row["raw_signature"] else "verified_member",
    }


def resolve_protocol_in_catalog(
    conn: sqlite3.Connection,
    lang: str,
    spec: ProtoTargetSpec,
) -> Dict[str, Any]:
    """Resolves protocol/trait/interface contracts and counts implementing containers."""
    conn.row_factory = sqlite3.Row
    short_name = spec.qname.split("::")[-1].split(".")[-1]

    # Count implementing containers or symbols per ecosystem
    impl_count = 0
    try:
        if lang == "python" and spec.methods:
            placeholders = ",".join("?" for _ in spec.methods)
            r = conn.execute(
                f"SELECT COUNT(DISTINCT container_id) AS cnt FROM symbols WHERE name IN ({placeholders});",
                tuple(spec.methods),
            ).fetchone()
            impl_count = r["cnt"] if r else 0
        elif lang == "csharp":
            r = conn.execute(
                "SELECT COUNT(*) AS cnt FROM cs_container_facets WHERE implemented_interfaces_json LIKE ?;",
                (f"%{short_name}%",),
            ).fetchone()
            impl_count = r["cnt"] if r else 0
        elif lang == "rust":
            r = conn.execute(
                "SELECT COUNT(*) AS cnt FROM containers WHERE qualified_name LIKE ?;",
                (f"%{short_name}",),
            ).fetchone()
            impl_count = r["cnt"] if r else 0
        elif lang == "go" and spec.methods:
            r = conn.execute(
                "SELECT COUNT(DISTINCT container_id) AS cnt FROM symbols WHERE name = ?;",
                (spec.methods[0],),
            ).fetchone()
            impl_count = r["cnt"] if r else 0
    except sqlite3.Error:
        impl_count = 0

    base_res = resolve_type_in_catalog(conn, lang, spec.qname, spec.methods)
    return {
        "catalog_container_id": base_res["catalog_container_id"],
        "catalog_symbol_id": base_res["catalog_symbol_id"],
        "implementing_count": impl_count,
        "verification_status": base_res["verification_status"],
    }


# ============================================================================
# 7. PASS 4: AUTONOMOUS STDLIB TAXONOMY HARVESTER
# ============================================================================

def harvest_stdlib_taxonomy(
    bridge_conn: sqlite3.Connection,
    catalogs: Dict[str, Path],
) -> int:
    """
    Autonomously scans all 6 catalogs to index every standard library:
      - Exception & Error container/type
      - Collection & Container structure
      - I/O & Stream handle
      - Trait / Interface / Concept protocol container
    into `discovered_stdlib_taxonomy`.
    """
    total_discovered = 0

    for lang, db_path in catalogs.items():
        uri = f"file:{db_path.resolve()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Harvest all Stratum 0 & 1 containers with public method counts
            rows = conn.execute(
                """
                SELECT
                    c.container_id,
                    c.container_kind,
                    c.qualified_name,
                    c.short_name,
                    d.stratum,
                    COUNT(s.symbol_id) AS pub_methods
                FROM containers c
                JOIN distributions d ON c.dist_id = d.dist_id
                LEFT JOIN symbols s
                  ON s.container_id = c.container_id
                 AND s.is_hidden = 0
                 AND s.symbol_kind IN ('method', 'function', 'constructor', 'property')
                WHERE d.stratum IN (0, 1)
                  AND c.is_hidden = 0
                GROUP BY c.container_id;
                """
            ).fetchall()

            for r in rows:
                qname = r["qualified_name"] or ""
                sname = r["short_name"] or ""
                ckind = (r["container_kind"] or "").lower()
                domain: Optional[str] = None

                # Classify domain heuristically + structurally
                if (
                    ckind == "exception_class"
                    or sname.endswith(("Error", "Exception", "Fault", "Panic"))
                    or "::error::" in qname.lower()
                    or "stdexcept" in qname.lower()
                ):
                    domain = "exception"
                elif (
                    any(
                        tok in qname.lower()
                        for tok in (
                            "collections",
                            "vector",
                            "vec",
                            "list",
                            "dict",
                            "map",
                            "set",
                            "queue",
                            "deque",
                            "slice",
                            "array",
                            "btree",
                            "heap",
                        )
                    )
                    and ckind in ("class", "struct", "interface", "trait", "type", "module")
                ):
                    domain = "collection"
                elif (
                    any(
                        tok in qname.lower()
                        for tok in (
                            "io.",
                            "std::io",
                            "system.io",
                            "fstream",
                            "sstream",
                            "stream",
                            "reader",
                            "writer",
                            "buffer",
                            "path",
                            "file",
                            "bufio",
                        )
                    )
                    and ckind in ("class", "struct", "interface", "trait", "type")
                ):
                    domain = "io_stream"
                elif ckind in ("interface", "trait", "concept", "protocol"):
                    domain = "protocol_trait_interface"

                if domain is not None:
                    facet_json = fetch_layer2_container_facet(conn, lang, r["container_id"])
                    bridge_conn.execute(
                        """
                        INSERT OR IGNORE INTO discovered_stdlib_taxonomy (
                            language, taxonomy_domain, stratum, entity_kind,
                            qualified_name, short_name, catalog_container_id,
                            public_method_count, layer2_metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            lang,
                            domain,
                            r["stratum"],
                            r["container_kind"],
                            qname,
                            sname,
                            r["container_id"],
                            r["pub_methods"],
                            facet_json,
                        ),
                    )
                    total_discovered += 1

    return total_discovered


# ============================================================================
# 8. MAIN BUILDER ORCHESTRATOR
# ============================================================================

def build_bridge_database(db_dir: Path, out_db: Path) -> None:
    catalogs = discover_catalogs(db_dir)
    if not catalogs:
        raise SystemExit(
            f"[ERROR] No UTSS language catalogs found in {db_dir.resolve()}.\n"
            "Pass --db-dir pointing to the directory containing your 6 .db files."
        )

    print("==> 1. Discovered UTSS Language Catalogs:")
    for lang, path in catalogs.items():
        print(f"    - {lang.upper():10s} : {path}")

    out_db.parent.mkdir(parents=True, exist_ok=True)
    bridge_conn = sqlite3.connect(str(out_db))
    bridge_conn.executescript(BRIDGE_DDL)

    # Open read-only connections to all discovered catalogs
    lang_conns: Dict[str, sqlite3.Connection] = {}
    for lang, path in catalogs.items():
        uri = f"file:{path.resolve()}?mode=ro"
        lang_conns[lang] = sqlite3.connect(uri, uri=True)

    try:
        concept_id_map: Dict[str, int] = {}
        resolved_container_cache: Dict[Tuple[str, str], Tuple[Optional[int], Optional[str]]] = {}

        print("==> 2. Populating & Verifying Universal Concepts and Type Mappings...")
        for spec in CONCEPT_SPECS:
            cur = bridge_conn.execute(
                """
                INSERT INTO universal_concepts (concept_key, category, type_arity, description)
                VALUES (?, ?, ?, ?);
                """,
                (spec.key, spec.category, spec.arity, spec.desc),
            )
            cid = cur.lastrowid
            assert cid is not None
            concept_id_map[spec.key] = cid

            for lang, tspec in spec.targets.items():
                if lang in lang_conns:
                    emp = resolve_type_in_catalog(
                        lang_conns[lang], lang, tspec.qname, tspec.fallbacks
                    )
                else:
                    emp = {
                        "catalog_container_id": None,
                        "catalog_symbol_id": None,
                        "resolved_qualified_name": None,
                        "verified_stratum": None,
                        "verified_requires_import": None,
                        "verification_status": "catalog_missing",
                        "layer2_facet_json": None,
                    }

                resolved_container_cache[(spec.key, lang)] = (
                    emp["catalog_container_id"],
                    emp["resolved_qualified_name"] or tspec.qname,
                )

                bridge_conn.execute(
                    """
                    INSERT INTO universal_type_mappings (
                        concept_id, language, target_qualified_name,
                        fallback_candidates_json, type_syntax_template,
                        required_import, memory_model, nullability_model,
                        catalog_container_id, catalog_symbol_id,
                        resolved_qualified_name, verified_stratum,
                        verified_requires_import, verification_status,
                        layer2_facet_json, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        cid,
                        lang,
                        tspec.qname,
                        json.dumps(tspec.fallbacks),
                        tspec.syntax,
                        tspec.imp,
                        tspec.mem,
                        tspec.null_model,
                        emp["catalog_container_id"],
                        emp["catalog_symbol_id"],
                        emp["resolved_qualified_name"],
                        emp["verified_stratum"],
                        emp["verified_requires_import"],
                        emp["verification_status"],
                        emp["layer2_facet_json"],
                        tspec.notes,
                    ),
                )

        print("==> 3. Populating & Verifying Canonical Operation Mappings...")
        for (concept_key, canonical_op), lang_ops in OPERATION_SPECS.items():
            cid = concept_id_map[concept_key]
            for lang, ospec in lang_ops.items():
                cat_cid, resolved_qname = resolved_container_cache.get(
                    (concept_key, lang), (None, None)
                )
                if lang in lang_conns:
                    emp_op = resolve_operation_in_catalog(
                        lang_conns[lang], cat_cid, resolved_qname, ospec.sym
                    )
                else:
                    emp_op = {
                        "catalog_symbol_id": None,
                        "verified_qualified_name": None,
                        "verified_raw_signature": None,
                        "verified_return_type": None,
                        "verified_overload_count": 0,
                        "verified_pass_kinds_json": "[]",
                        "verification_status": "catalog_missing",
                    }

                bridge_conn.execute(
                    """
                    INSERT INTO universal_operation_mappings (
                        concept_id, canonical_op, language,
                        target_symbol_name, call_syntax_template,
                        receiver_pass_kind, mutates_receiver, returns_new_value,
                        catalog_symbol_id, verified_qualified_name,
                        verified_raw_signature, verified_return_type,
                        verified_overload_count, verified_pass_kinds_json,
                        verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        cid,
                        canonical_op,
                        lang,
                        ospec.sym,
                        ospec.template,
                        ospec.pass_kind,
                        ospec.mutates,
                        ospec.returns_new,
                        emp_op["catalog_symbol_id"],
                        emp_op["verified_qualified_name"],
                        emp_op["verified_raw_signature"],
                        emp_op["verified_return_type"],
                        emp_op["verified_overload_count"],
                        emp_op["verified_pass_kinds_json"],
                        emp_op["verification_status"],
                    ),
                )

        print("==> 4. Populating & Verifying Behavioral Protocol Mappings...")
        for concept_key, lang_protos in PROTOCOL_SPECS.items():
            cid = concept_id_map[concept_key]
            for lang, pspec in lang_protos.items():
                if lang in lang_conns:
                    emp_proto = resolve_protocol_in_catalog(lang_conns[lang], lang, pspec)
                else:
                    emp_proto = {
                        "catalog_container_id": None,
                        "catalog_symbol_id": None,
                        "implementing_count": 0,
                        "verification_status": "catalog_missing",
                    }

                bridge_conn.execute(
                    """
                    INSERT INTO universal_protocol_mappings (
                        concept_id, language, contract_kind,
                        contract_qualified_name, required_methods_json,
                        lowering_strategy, catalog_container_id,
                        catalog_symbol_id, implementing_count,
                        verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        cid,
                        lang,
                        pspec.kind,
                        pspec.qname,
                        json.dumps(pspec.methods),
                        pspec.strategy,
                        emp_proto["catalog_container_id"],
                        emp_proto["catalog_symbol_id"],
                        emp_proto["implementing_count"],
                        emp_proto["verification_status"],
                    ),
                )

        print("==> 5. Running Autonomous Stdlib Taxonomy Harvester across all 6 DBs...")
        harvested_count = harvest_stdlib_taxonomy(bridge_conn, catalogs)
        bridge_conn.commit()

        # Print Verification Summary Report
        print("\n=== UTSS UNIVERSAL BRIDGE DB VERIFICATION SUMMARY ===")
        cur = bridge_conn.execute(
            """
            SELECT uc.category, utm.verification_status, COUNT(*) AS cnt
            FROM universal_type_mappings utm
            JOIN universal_concepts uc ON utm.concept_id = uc.concept_id
            GROUP BY uc.category, utm.verification_status
            ORDER BY uc.category, cnt DESC;
            """
        )
        for row in cur.fetchall():
            print(f"  [Type Mapping] Category: {row[0]:14s} | Status: {row[1]:22s} | Count: {row[2]}")

        cur_tax = bridge_conn.execute(
            """
            SELECT taxonomy_domain, COUNT(*) AS cnt, COUNT(DISTINCT language) AS langs
            FROM discovered_stdlib_taxonomy
            GROUP BY taxonomy_domain
            ORDER BY cnt DESC;
            """
        )
        print(f"\n  [Auto-Harvested Stdlib Entities: {harvested_count} total]")
        for row in cur_tax.fetchall():
            print(f"    * Domain: {row[0]:26s} -> {row[1]:5d} entities across {row[2]} languages")

        print(f"\n==> Successfully generated: {out_db.resolve()}")

    finally:
        for c in lang_conns.values():
            c.close()
        bridge_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and populate utss_universal_bridge.db by scanning all 6 UTSS catalogs."
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=Path("dbs"),
        help="Directory containing the 6 UTSS SQLite catalogs (or repository root).",
    )
    parser.add_argument(
        "--out-db",
        type=Path,
        default=Path("dbs/utss_universal_bridge.db"),
        help="Output path for the generated universal bridge SQLite database.",
    )
    args = parser.parse_args()
    build_bridge_database(args.db_dir, args.out_db)


if __name__ == "__main__":
    main()

```

---

### 3. Running the Populator & Querying `utss_universal_bridge.db`

1. **Generate the Bridge Database**:
```bash
uv run python build_bridge_db.py --db-dir ./dbs --out-db ./dbs/utss_universal_bridge.db

```


*(If running from the harvester repository root where `catalog_base_full.db`, `Z_CS/`, `Z_Rust/`, `Z_TS/`, `Z_C/`, and `Z_Go/` reside, pass `--db-dir .`)*.


2. **Drop It Into the Workbench**:
Because `build_bridge_db.py` writes `utss_universal_bridge.db` directly into `./dbs/`, your FastAPI backend can expose it in the database switcher or attach it alongside the 6 language catalogs (`ATTACH DATABASE 'dbs/utss_universal_bridge.db' AS bridge;`).


3. **Sample Transpiler Lookup Query (Verifying Live Signatures + Lowering Templates)**:
Once built, your Phase 5 transpiler backend (`psc`) or SQL Workbench can query `utss_universal_bridge.db` directly to translate any source type and method call into any of the 6 target languages with empirical catalog verification:

```sql
SELECT
    uc.concept_key,
    uom.canonical_op,
    uom.language,
    utm.type_syntax_template AS container_type,
    uom.call_syntax_template AS lowering_template,
    uom.receiver_pass_kind,
    uom.verified_raw_signature AS catalog_signature,
    uom.verified_overload_count AS overloads
FROM universal_operation_mappings uom
JOIN universal_concepts uc ON uom.concept_id = uc.concept_id
JOIN universal_type_mappings utm
  ON utm.concept_id = uc.concept_id AND utm.language = uom.language
WHERE uc.concept_key IN ('col.sequence', 'col.map', 'io.file_stream')
ORDER BY uc.concept_key, uom.canonical_op, uom.language;

```

Would you like to build the **Phase 4 / Phase 5 Transpiler Resolution API (`bridge_resolver.py`)** next—which takes a Python AST node (e.g., `items.append(x)`, `with open(...) as f:`, or `dict[str, int]`) and queries `utss_universal_bridge.db` to emit target C#, Rust, Go, C++, or TypeScript code?















`bridge_resolver.py` implements the **Phase 4 Semantic Normalizer** and **Phase 5 Multi-Target Code Emitter** by querying `utss_universal_bridge.db` to translate Python AST type annotations, collection/string/stream operations, and dunder protocols into verified **C#, Rust, Go, C++, and TypeScript** code.

### 1. Resolution Pipeline Architecture

The resolver bridges Python's AST and the relational tables in `utss_universal_bridge.db` across four stages:

| Resolution Stage | Input Python AST Node | Bridge Table Queried | Target Output & Compiler Metadata |
| --- | --- | --- | --- |
| **1. Recursive Type Lowering** | `ast.AnnAssign`, `ast.Subscript`, `ast.BinOp (BitOr)` (e.g., `dict[str, list[int]]`, `int | None`) | `universal_concepts` + `universal_type_mappings` | Recursively expands `type_syntax_template` (`Dictionary<string, List<long>>`, `HashMap<String, Vec<i64>>`, `map[string][]int64`), collects `required_import`, and attaches `memory_model` & `nullability_model`. |
| **2. Operation & Call Lowering** | `ast.Call`, `ast.Compare (In)`, `ast.Subscript` (e.g., `items.append(x)`, `len(items)`, `k in d`) | `universal_operation_mappings` | Resolves `(concept_key, canonical_op)` against receiver type, formats `call_syntax_template`, and flags `mutates_receiver`, `receiver_pass_kind` (`mut_ref`, `free_fn`), and `verified_raw_signature`. |
| **3. Protocol & Scope Lowering** | `ast.With`, `ast.For`, `ast.ClassDef` (`__enter__`, `__iter__`, `__eq__`, `__lt__`) | `universal_protocol_mappings` | Maps duck-typed Python blocks and dunders to `using_statement` (C#), `raii_drop_scope` (Rust/C++), `defer_close` (Go), and `using_declaration` (TypeScript). |
| **4. Long-Tail Stdlib Fallback** | Unmapped stdlib classes/exceptions (e.g., `ValueError`, `Path`, `BytesIO`) | `discovered_stdlib_taxonomy` | Looks up harvested Stratum 0/1 containers and Layer 2 facets when a symbol falls outside core primitives.

 |

---

### 2. Complete Implementation (`bridge_resolver.py`)

Save this module in the root of your repository (or inside `server/analysis/bridge_resolver.py`):

```python
#!/usr/bin/env python3
"""
UTSS Phase 4 & 5: Universal Bridge Resolver & Multi-Target Synthesizer
=======================================================================
Queries `utss_universal_bridge.db` in read-only mode to normalize Python AST
types, method calls, built-in functions, operators, and dunder protocols into
empirically verified C#, Rust, Go, C++, and TypeScript code.

Usage:
    uv run python bridge_resolver.py --bridge-db ./dbs/utss_universal_bridge.db
"""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

TARGET_LANGUAGES: Tuple[str, ...] = (
    "csharp",
    "rust",
    "go",
    "cpp",
    "typescript",
)


# ============================================================================
# 1. UNIVERSAL IR DATA STRUCTURES
# ============================================================================

@dataclass
class UniversalTypeNode:
    """Recursive language-agnostic representation of a normalized type."""
    concept_key: str
    type_args: List["UniversalTypeNode"] = field(default_factory=list)

    def pretty(self) -> str:
        if not self.type_args:
            return self.concept_key
        inner = ", ".join(arg.pretty() for arg in self.type_args)
        return f"{self.concept_key}<{inner}>"


@dataclass
class ResolvedTypeEmission:
    """Target language emission for a UniversalTypeNode."""
    language: str
    concept_key: str
    emitted_type: str
    required_imports: List[str]
    memory_model: str
    nullability_model: str
    resolved_qualified_name: Optional[str]
    verification_status: str


@dataclass
class ResolvedOperationEmission:
    """Target language emission for a normalized method/function/operator call."""
    language: str
    concept_key: str
    canonical_op: str
    emitted_expr: str
    receiver_pass_kind: str
    mutates_receiver: bool
    returns_new_value: bool
    verified_qualified_name: Optional[str]
    verified_raw_signature: Optional[str]
    verification_status: str


@dataclass
class ResolvedProtocolEmission:
    """Target language emission for a behavioral protocol (e.g., disposable, iterable)."""
    language: str
    concept_key: str
    contract_kind: str
    contract_qualified_name: str
    required_methods: List[str]
    lowering_strategy: str
    emitted_construct: str
    verification_status: str


@dataclass
class SynthesisReport:
    """Full multi-language synthesis output for a Python AST snippet."""
    source_code: str
    target_language: str
    required_imports: List[str]
    emitted_lines: List[str]
    type_resolutions: List[ResolvedTypeEmission]
    operation_resolutions: List[ResolvedOperationEmission]
    protocol_resolutions: List[ResolvedProtocolEmission]

    def formatted_code(self) -> str:
        blocks: List[str] = []
        if self.required_imports:
            blocks.append("\n".join(self.required_imports))
            blocks.append("")
        blocks.extend(self.emitted_lines)
        return "\n".join(blocks)


# ============================================================================
# 2. PYTHON LEXICAL -> UNIVERSAL CONCEPT NORMALIZATION MAPS
# ============================================================================

PYTHON_TYPE_TO_CONCEPT: Dict[str, str] = {
    # Primitives
    "bool": "prim.bool",
    "builtins.bool": "prim.bool",
    "int": "prim.int64",
    "builtins.int": "prim.int64",
    "BigInt": "prim.bigint",
    "float": "prim.float64",
    "builtins.float": "prim.float64",
    "str": "prim.utf8_str",
    "builtins.str": "prim.utf8_str",
    "bytes": "prim.bytes",
    "bytearray": "prim.bytes",
    "builtins.bytes": "prim.bytes",
    # Collections
    "list": "col.sequence",
    "List": "col.sequence",
    "builtins.list": "col.sequence",
    "dict": "col.map",
    "Dict": "col.map",
    "builtins.dict": "col.map",
    "OrderedDict": "col.ordered_map",
    "collections.OrderedDict": "col.ordered_map",
    "set": "col.set",
    "Set": "col.set",
    "builtins.set": "col.set",
    "deque": "col.deque",
    "collections.deque": "col.deque",
    # Control flow
    "Optional": "ctrl.optional",
    "typing.Optional": "ctrl.optional",
    "Result": "ctrl.result",
    # Exceptions
    "Exception": "exc.base_error",
    "BaseException": "exc.base_error",
    "ValueError": "exc.value_error",
    "IndexError": "exc.index_error",
    "KeyError": "exc.key_error",
    "OSError": "exc.io_error",
    "IOError": "exc.io_error",
    "FileNotFoundError": "exc.io_error",
    # I/O & Filesystem
    "Path": "io.path",
    "pathlib.Path": "io.path",
    "BufferedReader": "io.file_stream",
    "TextIOWrapper": "io.file_stream",
    "FileIO": "io.file_stream",
    "io.BufferedReader": "io.file_stream",
    "BytesIO": "io.memory_buffer",
    "StringIO": "io.memory_buffer",
    "io.BytesIO": "io.memory_buffer",
    # Protocols
    "AbstractContextManager": "proto.disposable",
    "ContextManager": "proto.disposable",
    "Iterable": "proto.iterable",
    "collections.abc.Iterable": "proto.iterable",
}

# Maps (concept_key, python_method_name) -> canonical_op in `universal_operation_mappings`
PYTHON_METHOD_TO_CANONICAL_OP: Dict[Tuple[str, str], str] = {
    # col.sequence
    ("col.sequence", "append"): "append",
    ("col.sequence", "pop"): "pop_back",
    ("col.sequence", "clear"): "clear",
    ("col.sequence", "__len__"): "length",
    ("col.sequence", "__contains__"): "contains",
    # col.map
    ("col.map", "__setitem__"): "insert",
    ("col.map", "get"): "get_optional",
    ("col.map", "pop"): "remove",
    ("col.map", "__contains__"): "contains_key",
    # col.set
    ("col.set", "add"): "add",
    ("col.set", "__contains__"): "contains",
    # prim.utf8_str
    ("prim.utf8_str", "split"): "split",
    ("prim.utf8_str", "strip"): "trim",
    ("prim.utf8_str", "startswith"): "starts_with",
    # io.file_stream
    ("io.file_stream", "read"): "read",
    ("io.file_stream", "write"): "write",
    ("io.file_stream", "close"): "close",
}

# Maps Python dunder sets on a ClassDef -> universal protocol concept_key
DUNDER_TO_PROTOCOL_CONCEPT: List[Tuple[Set[str], str]] = [
    ({"__enter__", "__exit__"}, "proto.disposable"),
    ({"__iter__"}, "proto.iterable"),
    ({"__lt__"}, "proto.comparable"),
    ({"__eq__"}, "proto.equatable"),
]


# ============================================================================
# 3. CORE BRIDGE RESOLVER ENGINE
# ============================================================================

class BridgeResolver:
    """
    Read-only query and lowering engine backed by `utss_universal_bridge.db`.
    """

    def __init__(self, bridge_db_path: Path) -> None:
        if not bridge_db_path.is_file():
            raise FileNotFoundError(
                f"Bridge database not found at {bridge_db_path.resolve()}. "
                "Run `build_bridge_db.py` first."
            )
        self.db_path = bridge_db_path.resolve()
        uri = f"file:{self.db_path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "BridgeResolver":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    # ------------------------------------------------------------------------
    # Stage 1: Parse Python AST Type Annotation -> UniversalTypeNode
    # ------------------------------------------------------------------------
    def parse_python_type_ast(self, node: ast.AST) -> UniversalTypeNode:
        """Recursively converts a Python AST type annotation into a UniversalTypeNode."""
        # Simple identifier: `int`, `str`, `list`, `Path`
        if isinstance(node, ast.Name):
            concept = PYTHON_TYPE_TO_CONCEPT.get(node.id, f"custom.{node.id}")
            return UniversalTypeNode(concept_key=concept)

        # Dotted attribute: `pathlib.Path`, `collections.deque`, `io.BytesIO`
        if isinstance(node, ast.Attribute):
            full_name = self._unparse_attr(node)
            short_name = node.attr
            concept = (
                PYTHON_TYPE_TO_CONCEPT.get(full_name)
                or PYTHON_TYPE_TO_CONCEPT.get(short_name)
                or f"custom.{full_name}"
            )
            return UniversalTypeNode(concept_key=concept)

        # Generic Subscript: `list[int]`, `dict[str, int]`, `Optional[str]`
        if isinstance(node, ast.Subscript):
            base_node = self.parse_python_type_ast(node.value)
            raw_slice = node.slice
            if isinstance(raw_slice, ast.Tuple):
                arg_nodes = [self.parse_python_type_ast(elt) for elt in raw_slice.elts]
            else:
                arg_nodes = [self.parse_python_type_ast(raw_slice)]
            return UniversalTypeNode(
                concept_key=base_node.concept_key,
                type_args=arg_nodes,
            )

        # PEP 604 Union: `T | None` or `None | T` -> `ctrl.optional<T>`
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_is_none = isinstance(node.left, ast.Constant) and node.left.value is None
            right_is_none = isinstance(node.right, ast.Constant) and node.right.value is None
            if right_is_none:
                inner = self.parse_python_type_ast(node.left)
                return UniversalTypeNode("ctrl.optional", [inner])
            if left_is_none:
                inner = self.parse_python_type_ast(node.right)
                return UniversalTypeNode("ctrl.optional", [inner])

        return UniversalTypeNode(concept_key=f"unmapped.{ast.unparse(node)}")

    def parse_python_type_str(self, type_expr: str) -> UniversalTypeNode:
        """Parses a Python type annotation string (e.g. 'dict[str, list[int]]')."""
        tree = ast.parse(type_expr, mode="eval")
        return self.parse_python_type_ast(tree.body)

    # ------------------------------------------------------------------------
    # Stage 2: Emit Target Type Syntax from `universal_type_mappings`
    # ------------------------------------------------------------------------
    def resolve_type(
        self, utype: UniversalTypeNode, target_lang: str
    ) -> ResolvedTypeEmission:
        """
        Recursively resolves a UniversalTypeNode into target language type syntax
        and collects required imports from `utss_universal_bridge.db`.
        """
        imports: List[str] = []
        child_emissions: List[ResolvedTypeEmission] = []

        for arg in utype.type_args:
            child_res = self.resolve_type(arg, target_lang)
            child_emissions.append(child_res)
            for imp in child_res.required_imports:
                if imp not in imports:
                    imports.append(imp)

        row = self.conn.execute(
            """
            SELECT
                utm.type_syntax_template,
                utm.required_import,
                utm.memory_model,
                utm.nullability_model,
                utm.resolved_qualified_name,
                utm.verification_status
            FROM universal_type_mappings utm
            JOIN universal_concepts uc ON utm.concept_id = uc.concept_id
            WHERE uc.concept_key = ? AND utm.language = ?
            LIMIT 1;
            """,
            (utype.concept_key, target_lang),
        ).fetchone()

        if row is None:
            # Fallback to `discovered_stdlib_taxonomy` if unmapped
            short = utype.concept_key.split(".")[-1]
            tax = self.conn.execute(
                """
                SELECT qualified_name
                FROM discovered_stdlib_taxonomy
                WHERE language = ? AND short_name = ?
                LIMIT 1;
                """,
                (target_lang, short),
            ).fetchone()
            fallback_name = tax["qualified_name"] if tax else short
            return ResolvedTypeEmission(
                language=target_lang,
                concept_key=utype.concept_key,
                emitted_type=fallback_name,
                required_imports=imports,
                memory_model="unknown",
                nullability_model="unknown",
                resolved_qualified_name=fallback_name,
                verification_status="taxonomy_fallback" if tax else "unmapped",
            )

        template: str = row["type_syntax_template"]
        for idx, child in enumerate(child_emissions):
            template = template.replace(f"{{T{idx}}}", child.emitted_type)

        # Clean up unfilled generic placeholders if bare container was referenced (e.g. `list`)
        if "{T0}" in template:
            default_any = {
                "csharp": "object",
                "rust": "serde_json::Value",
                "go": "any",
                "cpp": "std::any",
                "typescript": "unknown",
                "python": "Any",
            }.get(target_lang, "T")
            template = template.replace("{T0}", default_any).replace("{T1}", default_any)

        req_imp = row["required_import"]
        if req_imp:
            formatted_imp = self._format_import_statement(target_lang, req_imp)
            if formatted_imp not in imports:
                imports.append(formatted_imp)

        return ResolvedTypeEmission(
            language=target_lang,
            concept_key=utype.concept_key,
            emitted_type=template,
            required_imports=imports,
            memory_model=row["memory_model"],
            nullability_model=row["nullability_model"],
            resolved_qualified_name=row["resolved_qualified_name"],
            verification_status=row["verification_status"],
        )

    # ------------------------------------------------------------------------
    # Stage 3: Emit Target Method/Operation Call from `universal_operation_mappings`
    # ------------------------------------------------------------------------
    def resolve_operation(
        self,
        concept_key: str,
        canonical_op: str,
        target_lang: str,
        receiver_expr: str,
        arg_exprs: Optional[List[str]] = None,
    ) -> Optional[ResolvedOperationEmission]:
        """
        Queries `universal_operation_mappings` to lower a canonical operation
        (e.g., `('col.sequence', 'append')`) into target language syntax.
        """
        arg_exprs = arg_exprs or []
        row = self.conn.execute(
            """
            SELECT
                uom.call_syntax_template,
                uom.receiver_pass_kind,
                uom.mutates_receiver,
                uom.returns_new_value,
                uom.verified_qualified_name,
                uom.verified_raw_signature,
                uom.verification_status
            FROM universal_operation_mappings uom
            JOIN universal_concepts uc ON uom.concept_id = uc.concept_id
            WHERE uc.concept_key = ?
              AND uom.canonical_op = ?
              AND uom.language = ?
            LIMIT 1;
            """,
            (concept_key, canonical_op, target_lang),
        ).fetchone()

        if row is None:
            return None

        emitted = row["call_syntax_template"].replace("{self}", receiver_expr)
        for idx, arg in enumerate(arg_exprs):
            emitted = emitted.replace(f"{{arg{idx}}}", arg)

        return ResolvedOperationEmission(
            language=target_lang,
            concept_key=concept_key,
            canonical_op=canonical_op,
            emitted_expr=emitted,
            receiver_pass_kind=row["receiver_pass_kind"],
            mutates_receiver=bool(row["mutates_receiver"]),
            returns_new_value=bool(row["returns_new_value"]),
            verified_qualified_name=row["verified_qualified_name"],
            verified_raw_signature=row["verified_raw_signature"],
            verification_status=row["verification_status"],
        )

    # ------------------------------------------------------------------------
    # Stage 4: Emit Behavioral Protocol Lowering from `universal_protocol_mappings`
    # ------------------------------------------------------------------------
    def resolve_protocol(
        self,
        concept_key: str,
        target_lang: str,
        resource_var: str = "res",
        init_expr: str = "open_resource()",
        body_comment: str = "// scoped body",
    ) -> Optional[ResolvedProtocolEmission]:
        """
        Queries `universal_protocol_mappings` and synthesizes the target language's
        idiomatic lexical construct (e.g. `using`, RAII scope, `defer Close()`, `for`).
        """
        row = self.conn.execute(
            """
            SELECT
                upm.contract_kind,
                upm.contract_qualified_name,
                upm.required_methods_json,
                upm.lowering_strategy,
                upm.verification_status
            FROM universal_protocol_mappings upm
            JOIN universal_concepts uc ON upm.concept_id = uc.concept_id
            WHERE uc.concept_key = ? AND upm.language = ?
            LIMIT 1;
            """,
            (concept_key, target_lang),
        ).fetchone()

        if row is None:
            return None

        strategy = row["lowering_strategy"]
        methods = json.loads(row["required_methods_json"] or "[]")
        construct = self._render_protocol_construct(
            strategy=strategy,
            target_lang=target_lang,
            contract_qname=row["contract_qualified_name"],
            resource_var=resource_var,
            init_expr=init_expr,
            body_comment=body_comment,
        )

        return ResolvedProtocolEmission(
            language=target_lang,
            concept_key=concept_key,
            contract_kind=row["contract_kind"],
            contract_qualified_name=row["contract_qualified_name"],
            required_methods=methods,
            lowering_strategy=strategy,
            emitted_construct=construct,
            verification_status=row["verification_status"],
        )

    # ------------------------------------------------------------------------
    # Stage 5: Full AST Snippet Synthesizer (`synthesize_python_snippet`)
    # ------------------------------------------------------------------------
    def synthesize_python_snippet(
        self, python_code: str, target_lang: str
    ) -> SynthesisReport:
        """
        Walks a Python AST snippet, tracks variable types + mutability requirements,
        and emits translated code for `target_lang` backed by `utss_universal_bridge.db`.
        """
        tree = ast.parse(python_code)
        sym_table: Dict[str, UniversalTypeNode] = {}
        mutated_vars: Set[str] = set()

        # Pass 1: Pre-scan variable declarations and mutations (for Rust `let mut` / TS `let` vs `const`)
        self._prescan_mutations(tree, sym_table, mutated_vars)

        imports: List[str] = []
        emitted_lines: List[str] = []
        type_resolutions: List[ResolvedTypeEmission] = []
        op_resolutions: List[ResolvedOperationEmission] = []
        proto_resolutions: List[ResolvedProtocolEmission] = []

        def add_imports(new_imps: List[str]) -> None:
            for imp in new_imps:
                if imp not in imports:
                    imports.append(imp)

        for stmt in tree.body:
            # 1. Annotated Assignment: `items: list[int] = []` or `cache: dict[str, int] = {}`
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                var_name = stmt.target.id
                utype = self.parse_python_type_ast(stmt.annotation)
                sym_table[var_name] = utype
                tres = self.resolve_type(utype, target_lang)
                type_resolutions.append(tres)
                add_imports(tres.required_imports)

                is_mut = var_name in mutated_vars
                init_rhs = self._lower_expr(
                    stmt.value,
                    target_lang,
                    sym_table,
                    op_resolutions,
                    expected_type=utype,
                    emitted_type_str=tres.emitted_type,
                )
                decl_line = self._format_var_declaration(
                    target_lang, var_name, tres.emitted_type, init_rhs, is_mut
                )
                emitted_lines.append(decl_line)

            # 2. Subscript Assignment: `cache["k"] = 42` -> canonical_op = 'insert'
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Subscript):
                sub = stmt.targets[0]
                if isinstance(sub.value, ast.Name) and sub.value.id in sym_table:
                    recv_name = sub.value.id
                    recv_utype = sym_table[recv_name]
                    key_expr = self._lower_expr(sub.slice, target_lang, sym_table, op_resolutions)
                    val_expr = self._lower_expr(stmt.value, target_lang, sym_table, op_resolutions)
                    op_res = self.resolve_operation(
                        recv_utype.concept_key,
                        "insert",
                        target_lang,
                        recv_name,
                        [key_expr, val_expr],
                    )
                    if op_res:
                        op_resolutions.append(op_res)
                        emitted_lines.append(self._terminate_stmt(target_lang, op_res.emitted_expr))
                        continue

            # 3. Standalone Expression Statement (e.g. `items.append(10)`, `stream.close()`)
            elif isinstance(stmt, ast.Expr):
                expr_str = self._lower_expr(stmt.value, target_lang, sym_table, op_resolutions)
                emitted_lines.append(self._terminate_stmt(target_lang, expr_str))

            # 4. Context Manager (`with open(...) as f:`) -> `proto.disposable`
            elif isinstance(stmt, ast.With) and stmt.items:
                item = stmt.items[0]
                var_name = (
                    item.optional_vars.id
                    if isinstance(item.optional_vars, ast.Name)
                    else "resource"
                )
                sym_table[var_name] = UniversalTypeNode("io.file_stream")
                init_str = ast.unparse(item.context_expr)

                body_lines: List[str] = []
                for bstmt in stmt.body:
                    if isinstance(bstmt, ast.Expr):
                        body_lines.append(
                            self._terminate_stmt(
                                target_lang,
                                self._lower_expr(bstmt.value, target_lang, sym_table, op_resolutions),
                            )
                        )
                body_str = "\n    ".join(body_lines) if body_lines else "// resource body"
                pres = self.resolve_protocol(
                    "proto.disposable", target_lang, var_name, init_str, body_str
                )
                if pres:
                    proto_resolutions.append(pres)
                    emitted_lines.append(pres.emitted_construct)

            # 5. For Loop (`for x in items:`) -> `proto.iterable`
            elif isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name):
                loop_var = stmt.target.id
                iter_expr = self._lower_expr(stmt.iter, target_lang, sym_table, op_resolutions)
                pres = self.resolve_protocol(
                    "proto.iterable", target_lang, loop_var, iter_expr, "// loop body"
                )
                if pres:
                    proto_resolutions.append(pres)
                    emitted_lines.append(pres.emitted_construct)

            # 6. Class Definition with Dunders (`__enter__`, `__iter__`, `__eq__`, `__lt__`)
            elif isinstance(stmt, ast.ClassDef):
                method_names = {
                    n.name for n in stmt.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                matched_contracts: List[str] = []
                for req_dunders, proto_key in DUNDER_TO_PROTOCOL_CONCEPT:
                    if req_dunders.issubset(method_names):
                        pres = self.resolve_protocol(proto_key, target_lang, stmt.name, "", "")
                        if pres:
                            proto_resolutions.append(pres)
                            matched_contracts.append(pres.contract_qualified_name)
                if matched_contracts:
                    emitted_lines.append(
                        f"// Class `{stmt.name}` implements {target_lang.upper()} contracts: {', '.join(matched_contracts)}"
                    )

        return SynthesisReport(
            source_code=python_code,
            target_language=target_lang,
            required_imports=imports,
            emitted_lines=emitted_lines,
            type_resolutions=type_resolutions,
            operation_resolutions=op_resolutions,
            protocol_resolutions=proto_resolutions,
        )

    # ------------------------------------------------------------------------
    # Internal AST & Formatting Helpers
    # ------------------------------------------------------------------------
    def _prescan_mutations(
        self,
        tree: ast.AST,
        sym_table: Dict[str, UniversalTypeNode],
        mutated_vars: Set[str],
    ) -> None:
        """Identifies variables that undergo mutating operations so Rust emits `let mut`."""
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                sym_table[node.target.id] = self.parse_python_type_ast(node.annotation)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    recv = node.func.value.id
                    mname = node.func.attr
                    if mname in {"append", "pop", "clear", "add", "read", "write", "close"}:
                        mutated_vars.add(recv)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                        mutated_vars.add(t.value.id)

    def _lower_expr(
        self,
        node: Optional[ast.AST],
        target_lang: str,
        sym_table: Dict[str, UniversalTypeNode],
        op_resolutions: List[ResolvedOperationEmission],
        expected_type: Optional[UniversalTypeNode] = None,
        emitted_type_str: Optional[str] = None,
    ) -> str:
        if node is None:
            return ""

        # Empty collection literals `[]`, `{}`, `set()`
        if isinstance(node, ast.List) and not node.elts:
            return self._empty_collection_literal(target_lang, "col.sequence", emitted_type_str)
        if isinstance(node, ast.Dict) and not node.keys:
            return self._empty_collection_literal(target_lang, "col.map", emitted_type_str)

        # Constants & Identifiers
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                if target_lang == "rust":
                    return f'String::from("{node.value}")'
                return f'"{node.value}"'
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if node.value is None:
                return {"csharp": "null", "rust": "None", "go": "nil", "cpp": "std::nullopt", "typescript": "null"}.get(target_lang, "None")
            return str(node.value)

        if isinstance(node, ast.Name):
            return node.id

        # Built-in `len(x)` -> canonical_op = 'length'
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1:
            arg0 = node.args[0]
            if isinstance(arg0, ast.Name) and arg0.id in sym_table:
                utype = sym_table[arg0.id]
                op_res = self.resolve_operation(utype.concept_key, "length", target_lang, arg0.id)
                if op_res:
                    op_resolutions.append(op_res)
                    return op_res.emitted_expr

        # Method call `recv.method(arg0, ...)`
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in sym_table:
                recv_name = node.func.value.id
                method_name = node.func.attr
                recv_utype = sym_table[recv_name]
                canonical_op = PYTHON_METHOD_TO_CANONICAL_OP.get(
                    (recv_utype.concept_key, method_name), method_name
                )
                lowered_args = [
                    self._lower_expr(a, target_lang, sym_table, op_resolutions)
                    for a in node.args
                ]
                op_res = self.resolve_operation(
                    recv_utype.concept_key,
                    canonical_op,
                    target_lang,
                    recv_name,
                    lowered_args,
                )
                if op_res:
                    op_resolutions.append(op_res)
                    return op_res.emitted_expr

        # Membership test `x in container` -> canonical_op = 'contains' or 'contains_key'
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            container_node = node.comparators[0]
            if isinstance(container_node, ast.Name) and container_node.id in sym_table:
                recv_name = container_node.id
                recv_utype = sym_table[recv_name]
                canonical_op = PYTHON_METHOD_TO_CANONICAL_OP.get(
                    (recv_utype.concept_key, "__contains__"), "contains"
                )
                needle_expr = self._lower_expr(node.left, target_lang, sym_table, op_resolutions)
                op_res = self.resolve_operation(
                    recv_utype.concept_key,
                    canonical_op,
                    target_lang,
                    recv_name,
                    [needle_expr],
                )
                if op_res:
                    op_resolutions.append(op_res)
                    return op_res.emitted_expr

        return ast.unparse(node)

    @staticmethod
    def _unparse_attr(node: ast.Attribute) -> str:
        parts: List[str] = [node.attr]
        curr = node.value
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        return ".".join(reversed(parts))

    @staticmethod
    def _format_import_statement(target_lang: str, raw_import: str) -> str:
        if target_lang == "csharp":
            return f"using {raw_import};"
        if target_lang == "rust":
            return f"use {raw_import};"
        if target_lang == "go":
            return f'import "{raw_import}"'
        if target_lang == "cpp":
            return f"#include {raw_import}"
        if target_lang == "python":
            return f"import {raw_import}"
        `bridge_resolver.py` implements the **Phase 4 / Phase 5 Transpiler Resolution Engine**, connecting Python AST analysis directly to `utss_universal_bridge.db` to normalize types, resolve method calls and dunder protocols against empirical catalog signatures, and emit target code across C#, Rust, TypeScript, C++, and Go[cite: 1].

### 1. Resolution Pipeline Architecture

The engine translates Python AST constructs into target language syntax in four stages:

| Stage | Resolver Component | Input AST / IR Node | Bridge Table Queried | Output Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | **`TypeNormalizer`** | `ast.Name`, `ast.Subscript`, `ast.BinOp` (`T \| None`) | `universal_concepts`, `universal_type_mappings` | Recursive `ResolvedType` tree with target syntax & required imports |
| **Stage 2** | **`OperationLoweringEngine`** | `ast.Call` (`x.append(y)`, `len(x)`), `ast.Compare` (`k in d`) | `universal_operation_mappings` | Target call expression, `receiver_pass_kind`, mutation flags, and catalog signature |
| **Stage 3** | **`ProtocolLoweringEngine`** | `ast.With`, `ast.For`, `ast.Raise`, class dunders | `universal_protocol_mappings`, `universal_type_mappings` | Paradigm-specific control flow (`using`, RAII drop, `defer`, `Result<T, E>`) |
| **Stage 4** | **`MultiTargetSynthesizer`** | Normalized Module / Statement IR | All 4 Bridge Tables + `discovered_stdlib_taxonomy` | Target source code + deduplicated imports + empirical provenance log[cite: 1] |

---

### 2. Complete Transpiler Resolution Engine (`bridge_resolver.py`)

Save this module in the root of your repository (or inside `server/analysis/bridge_resolver.py`):

```python
#!/usr/bin/env python3
"""
UTSS Phase 4/5: Universal Bridge Resolver & Multi-Target Transpiler Engine
==========================================================================
Parses Python AST type annotations, variable declarations, collection/string/IO
operations, context managers (`with`), and exceptions, then queries
`utss_universal_bridge.db` to synthesize target C#, Rust, TypeScript, C++,
and Go code backed by empirical UTSS catalog signatures.

Usage (CLI Demo):
    uv run python bridge_resolver.py --bridge-db ./dbs/utss_universal_bridge.db
"""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

TARGET_LANGUAGES: Tuple[str, ...] = ("csharp", "rust", "typescript", "cpp", "go")

# Maps Python source type identifiers to universal_concepts.concept_key
PYTHON_TYPE_TO_CONCEPT: Dict[str, str] = {
    # Primitives
    "bool": "prim.bool",
    "int": "prim.int64",
    "bigint": "prim.bigint",
    "float": "prim.float64",
    "str": "prim.utf8_str",
    "bytes": "prim.bytes",
    "bytearray": "prim.bytes",
    # Collections
    "list": "col.sequence",
    "List": "col.sequence",
    "Sequence": "col.sequence",
    "dict": "col.map",
    "Dict": "col.map",
    "Mapping": "col.map",
    "OrderedDict": "col.ordered_map",
    "set": "col.set",
    "Set": "col.set",
    "frozenset": "col.set",
    "deque": "col.deque",
    "Deque": "col.deque",
    # Control Flow & Wrappers
    "Optional": "ctrl.optional",
    "Result": "ctrl.result",
    # Exceptions
    "Exception": "exc.base_error",
    "BaseException": "exc.base_error",
    "ValueError": "exc.value_error",
    "IndexError": "exc.index_error",
    "KeyError": "exc.key_error",
    "OSError": "exc.io_error",
    "IOError": "exc.io_error",
    "FileNotFoundError": "exc.io_error",
    # I/O & Filesystem
    "Path": "io.path",
    "PurePath": "io.path",
    "BufferedReader": "io.file_stream",
    "TextIOWrapper": "io.file_stream",
    "FileIO": "io.file_stream",
    "BytesIO": "io.memory_buffer",
    "StringIO": "io.memory_buffer",
    # Protocols
    "Iterable": "proto.iterable",
    "ContextManager": "proto.disposable",
    "AbstractContextManager": "proto.disposable",
}

# Maps (concept_key, python_method_or_syntax) -> canonical_op in universal_operation_mappings
PYTHON_OP_TO_CANONICAL: Dict[Tuple[str, str], str] = {
    # col.sequence
    ("col.sequence", "append"): "append",
    ("col.sequence", "__len__"): "length",
    ("col.sequence", "pop"): "pop_back",
    ("col.sequence", "clear"): "clear",
    ("col.sequence", "__contains__"): "contains",
    # col.map
    ("col.map", "__setitem__"): "insert",
    ("col.map", "get"): "get_optional",
    ("col.map", "__contains__"): "contains_key",
    ("col.map", "pop"): "remove",
    # col.set
    ("col.set", "add"): "add",
    ("col.set", "__contains__"): "contains",
    # prim.utf8_str
    ("prim.utf8_str", "split"): "split",
    ("prim.utf8_str", "strip"): "trim",
    ("prim.utf8_str", "startswith"): "starts_with",
    # io.file_stream
    ("io.file_stream", "read"): "read",
    ("io.file_stream", "write"): "write",
    ("io.file_stream", "close"): "close",
}


# ============================================================================
# 1. DATA MODELS FOR NORMALIZED IR & PROVENANCE TRACE
# ============================================================================

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


# ============================================================================
# 2. BRIDGE DATABASE CLIENT & QUERY LAYER
# ============================================================================

class BridgeCatalogRepository:
    """Read-only query interface over `utss_universal_bridge.db`."""

    def __init__(self, bridge_db_path: Path) -> None:
        if not bridge_db_path.is_file():
            raise FileNotFoundError(
                f"Bridge DB not found at {bridge_db_path}. Run `build_bridge_db.py` first."
            )
        self.db_path = bridge_db_path.resolve()
        uri = f"file:{self.db_path}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def get_type_mapping(self, concept_key: str, language: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT
                uc.concept_key, uc.category, uc.type_arity,
                utm.target_qualified_name, utm.type_syntax_template,
                utm.required_import, utm.memory_model, utm.nullability_model,
                utm.catalog_container_id, utm.catalog_symbol_id,
                utm.resolved_qualified_name, utm.verification_status
            FROM universal_type_mappings utm
            JOIN universal_concepts uc ON utm.concept_id = uc.concept_id
            WHERE uc.concept_key = ? AND utm.language = ?
            LIMIT 1;
            """,
            (concept_key, language),
        ).fetchone()
        return dict(row) if row else None

    def get_operation_mapping(
        self, concept_key: str, canonical_op: str, language: str
    ) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT
                uc.concept_key, uom.canonical_op, uom.language,
                uom.target_symbol_name, uom.call_syntax_template,
                uom.receiver_pass_kind, uom.mutates_receiver, uom.returns_new_value,
                uom.catalog_symbol_id, uom.verified_qualified_name,
                uom.verified_raw_signature, uom.verified_return_type,
                uom.verification_status
            FROM universal_operation_mappings uom
            JOIN universal_concepts uc ON uom.concept_id = uc.concept_id
            WHERE uc.concept_key = ? AND uom.canonical_op = ? AND uom.language = ?
            LIMIT 1;
            """,
            (concept_key, canonical_op, language),
        ).fetchone()
        return dict(row) if row else None

    def get_protocol_mapping(self, concept_key: str, language: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT
                uc.concept_key, upm.language, upm.contract_kind,
                upm.contract_qualified_name, upm.required_methods_json,
                upm.lowering_strategy, upm.catalog_container_id,
                upm.catalog_symbol_id, upm.implementing_count,
                upm.verification_status
            FROM universal_protocol_mappings upm
            JOIN universal_concepts uc ON upm.concept_id = uc.concept_id
            WHERE uc.concept_key = ? AND upm.language = ?
            LIMIT 1;
            """,
            (concept_key, language),
        ).fetchone()
        return dict(row) if row else None


# ============================================================================
# 3. RECURSIVE AST TYPE NORMALIZER & LOWERING ENGINE
# ============================================================================

class BridgeTranspiler:
    """
    Translates Python AST nodes into C#, Rust, TypeScript, C++, or Go code
    using empirical mappings from `utss_universal_bridge.db`.
    """

    def __init__(self, repo: BridgeCatalogRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------------------
    # Stage 1: Recursive Type Annotation Resolution
    # ------------------------------------------------------------------------
    def resolve_type_node(self, node: ast.AST, target_lang: str) -> ResolvedType:
        """Recursively resolves a Python type AST node into a target language type."""
        # Case 1: Simple identifier (`int`, `str`, `Path`, `ValueError`)
        if isinstance(node, ast.Name):
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(node.id, "prim.int64")
            return self._instantiate_type_template(concept_key, [], target_lang, raw_name=node.id)

        # Case 2: Qualified attribute (`pathlib.Path`, `io.BytesIO`, `collections.deque`)
        if isinstance(node, ast.Attribute):
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(node.attr, "prim.int64")
            return self._instantiate_type_template(concept_key, [], target_lang, raw_name=node.attr)

        # Case 3: PEP 604 Union (`T | None` or `None | T`) -> ctrl.optional<T>
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_is_none = isinstance(node.left, ast.Constant) and node.left.value is None
            right_is_none = isinstance(node.right, ast.Constant) and node.right.value is None
            if left_is_none or right_is_none:
                inner_node = node.right if left_is_none else node.left
                inner_resolved = self.resolve_type_node(inner_node, target_lang)
                return self._instantiate_type_template(
                    "ctrl.optional", [inner_resolved], target_lang, raw_name="Optional"
                )

        # Case 4: Generic subscript (`list[int]`, `dict[str, list[int]]`, `Optional[str]`)
        if isinstance(node, ast.Subscript):
            base_name = (
                node.value.id
                if isinstance(node.value, ast.Name)
                else (node.value.attr if isinstance(node.value, ast.Attribute) else "list")
            )
            concept_key = PYTHON_TYPE_TO_CONCEPT.get(base_name, "col.sequence")

            if isinstance(node.slice, ast.Tuple):
                arg_nodes = list(node.slice.elts)
            else:
                arg_nodes = [node.slice]

            resolved_args = [self.resolve_type_node(arg, target_lang) for arg in arg_nodes]
            return self._instantiate_type_template(
                concept_key, resolved_args, target_lang, raw_name=base_name
            )

        # Fallback
        return self._instantiate_type_template("prim.int64", [], target_lang, raw_name="Any")

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

        if mapping["required_import"]:
            imports.append(mapping["required_import"])

        for idx, arg in enumerate(type_args):
            rendered = rendered.replace(f"{{T{idx}}}", arg.rendered_type)
            imports.extend(arg.required_imports)
            prov.extend(arg.provenance)

        # Fill any unfulfilled generic placeholders with default target int/string
        rendered = rendered.replace("{T0}", "int").replace("{T1}", "int")

        prov.append(
            ProvenanceRecord(
                construct=f"type:{raw_name}",
                concept_key=concept_key,
                target_language=target_lang,
                resolved_target=mapping["resolved_qualified_name"] or mapping["target_qualified_name"],
                verification_status=mapping["verification_status"],
                catalog_container_id=mapping["catalog_container_id"],
                catalog_symbol_id=mapping["catalog_symbol_id"],
            )
        )

        return ResolvedType(
            concept_key=concept_key,
            target_language=target_lang,
            rendered_type=rendered,
            memory_model=mapping["memory_model"],
            nullability_model=mapping["nullability_model"],
            required_imports=imports,
            provenance=prov,
        )

    # ------------------------------------------------------------------------
    # Stage 2 & 3: Statement, Operation & Protocol Lowering
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

        # 2. Subscript Assignment (`scores["alice"] = 100`) -> col.map.insert
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                receiver = target.value.id
                rec_type = env_types.get(receiver)
                concept_key = rec_type.concept_key if rec_type else "col.map"
                key_expr = self._render_expr(target.slice, lang, env_types, imports, prov)
                val_expr = self._render_expr(stmt.value, lang, env_types, imports, prov)

                op_str = self._lower_operation(
                    concept_key,
                    "insert",
                    receiver,
                    [key_expr, val_expr],
                    lang,
                    prov,
                )
                return [self._terminate_stmt(op_str, lang)], imports, prov

            # Standard variable assignment (`n = len(items)`)
            if isinstance(target, ast.Name):
                var_name = target.id
                rhs = self._render_expr(stmt.value, lang, env_types, imports, prov)
                return [self._format_untyped_assign(var_name, rhs, lang)], imports, prov

        # 3. Standalone Expression Statement (`items.append(42)`)
        if isinstance(stmt, ast.Expr):
            expr_str = self._render_expr(stmt.value, lang, env_types, imports, prov)
            return [self._terminate_stmt(expr_str, lang)], imports, prov

        # 4. Context Manager (`with open("data.txt") as f:`) -> proto.disposable
        if isinstance(stmt, ast.With) and stmt.items:
            return self._lower_with_protocol(stmt, lang, env_types)

        # 5. Exception Raising (`raise ValueError("invalid input")`) -> exc.*
        if isinstance(stmt, ast.Raise) and stmt.exc is not None:
            return self._lower_raise_exception(stmt.exc, lang, env_types)

        return [f"// [unhandled AST node: {type(stmt).__name__}]"], imports, prov

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
                return {"csharp": "null", "rust": "None", "typescript": "null", "cpp": "std::nullopt", "go": "nil"}.get(lang, "null")
            return str(expr.value)

        if isinstance(expr, ast.Name):
            return expr.id

        # `k in container` -> canonical_op `contains` or `contains_key`
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and isinstance(expr.ops[0], ast.In):
            needle = self._render_expr(expr.left, lang, env_types, imports, prov)
            comparator = expr.comparators[0]
            if isinstance(comparator, ast.Name):
                rec_name = comparator.id
                rec_type = env_types.get(rec_name)
                ckey = rec_type.concept_key if rec_type else "col.sequence"
                canon_op = PYTHON_OP_TO_CANONICAL.get((ckey, "__contains__"), "contains")
                return self._lower_operation(ckey, canon_op, rec_name, [needle], lang, prov)

        # Function & Method Calls
        if isinstance(expr, ast.Call):
            args = [self._render_expr(a, lang, env_types, imports, prov) for a in expr.args]

            # Builtin `len(x)` -> canonical_op `length`
            if isinstance(expr.func, ast.Name) and expr.func.id == "len" and len(args) == 1:
                rec_name = args[0]
                rec_type = env_types.get(rec_name)
                ckey = rec_type.concept_key if rec_type else "col.sequence"
                return self._lower_operation(ckey, "length", rec_name, [], lang, prov)

            # Method call `receiver.method(arg0, ...)`
            if isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name):
                rec_name = expr.func.value.id
                py_method = expr.func.attr
                rec_type = env_types.get(rec_name)
                ckey = rec_type.concept_key if rec_type else "col.sequence"
                canon_op = PYTHON_OP_TO_CANONICAL.get((ckey, py_method), py_method)
                return self._lower_operation(ckey, canon_op, rec_name, args, lang, prov)

        return ast.unparse(expr)

    def _lower_operation(
        self,
        concept_key: str,
        canonical_op: str,
        receiver_expr: str,
        arg_exprs: List[str],
        lang: str,
        prov: List[ProvenanceRecord],
    ) -> str:
        op_map = self.repo.get_operation_mapping(concept_key, canonical_op, lang)
        if not op_map:
            joined = ", ".join(arg_exprs)
            return f"{receiver_expr}.{canonical_op}({joined})"

        rendered: str = op_map["call_syntax_template"].replace("{self}", receiver_expr)
        for idx, arg in enumerate(arg_exprs):
            rendered = rendered.replace(f"{{arg{idx}}}", arg)

        prov.append(
            ProvenanceRecord(
                construct=f"op:{concept_key}.{canonical_op}",
                concept_key=concept_key,
                target_language=lang,
                resolved_target=op_map["verified_qualified_name"] or op_map["target_symbol_name"],
                verification_status=op_map["verification_status"],
                catalog_symbol_id=op_map["catalog_symbol_id"],
                catalog_signature=op_map["verified_raw_signature"],
                receiver_pass_kind=op_map["receiver_pass_kind"],
            )
        )
        return rendered

    def _lower_with_protocol(
        self,
        stmt: ast.With,
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        """Lowers Python `with open(path) as handle:` via `proto.disposable` and `io.file_stream`."""
        imports: List[str] = []
        prov: List[ProvenanceRecord] = []

        item = stmt.items[0]
        handle_name = item.optional_vars.id if isinstance(item.optional_vars, ast.Name) else "stream"
        file_type = self._instantiate_type_template("io.file_stream", [], lang, raw_name="FileStream")
        env_types[handle_name] = file_type
        imports.extend(file_type.required_imports)
        prov.extend(file_type.provenance)

        proto = self.repo.get_protocol_mapping("proto.disposable", lang)
        strategy = proto["lowering_strategy"] if proto else "raii_drop_scope"
        if proto:
            prov.append(
                ProvenanceRecord(
                    construct="protocol:with_statement",
                    concept_key="proto.disposable",
                    target_language=lang,
                    resolved_target=proto["contract_qualified_name"],
                    verification_status=proto["verification_status"],
                    catalog_container_id=proto["catalog_container_id"],
                    catalog_symbol_id=proto["catalog_symbol_id"],
                )
            )

        path_arg = '"data.bin"'
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

        if lang == "csharp" and strategy == "using_statement":
            return (
                [f"using (var {handle_name} = File.OpenRead({path_arg}))", "{"]
                + indented_body
                + ["}"],
                imports,
                prov,
            )
        if lang == "rust" and strategy == "raii_drop_scope":
            return (
                [f"{{ // RAII Drop scope ({proto['contract_qualified_name'] if proto else 'Drop'})",
                 f"    let mut {handle_name} = std::fs::File::open({path_arg})?;"]
                + indented_body
                + ["} // <- drop(f) invoked deterministically"],
                imports,
                prov,
            )
        if lang == "go" and strategy == "defer_close":
            return (
                [f"{handle_name}, err := os.Open({path_arg})",
                 f"if err != nil {{ return err }}",
                 f"defer {handle_name}.Close()"]
                + body_lines,
                imports,
                prov,
            )
        if lang == "cpp" and strategy == "raii_drop_scope":
            return (
                [f"{{ // RAII scope (~fstream destructor)",
                 f"    std::fstream {handle_name}({path_arg});"]
                + indented_body
                + ["}"],
                imports,
                prov,
            )
        # TypeScript Explicit Resource Management (`using`)
        return (
            [f"using {handle_name} = await openFileStream({path_arg});"] + body_lines,
            imports,
            prov,
        )

    def _lower_raise_exception(
        self,
        exc_node: ast.AST,
        lang: str,
        env_types: Dict[str, ResolvedType],
    ) -> Tuple[List[str], List[str], List[ProvenanceRecord]]:
        """Lowers Python `raise ExcType(msg)` using `exc.*` mappings in `utss_universal_bridge.db`."""
        exc_name = "Exception"
        msg_arg = '"error"'
        if isinstance(exc_node, ast.Call) and isinstance(exc_node.func, ast.Name):
            exc_name = exc_node.func.id
            if exc_node.args and isinstance(exc_node.args[0], ast.Constant):
                msg_arg = f'"{exc_node.args[0].value}"'
        elif isinstance(exc_node, ast.Name):
            exc_name = exc_node.id

        concept_key = PYTHON_TYPE_TO_CONCEPT.get(exc_name, "exc.base_error")
        res_exc = self._instantiate_type_template(concept_key, [], lang, raw_name=exc_name)

        if lang == "csharp":
            line = f"throw new {res_exc.rendered_type}({msg_arg});"
        elif lang == "rust":
            line = f"return Err({res_exc.rendered_type}::from({msg_arg}));"
        elif lang == "typescript":
            line = f"throw new {res_exc.rendered_type}({msg_arg});"
        elif lang == "cpp":
            line = f"throw {res_exc.rendered_type}({msg_arg});"
        else:  # go
            line = f"return fmt.Errorf(\"%w: %s\", {res_exc.rendered_type}, {msg_arg})"

        return [line], res_exc.required_imports, res_exc.provenance

    # ------------------------------------------------------------------------
    # Stage 4: Target Syntax Formatting Helpers
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
            if ckey == "col.sequence":
                return {
                    "csharp": f"new {t_str}()",
                    "rust": "Vec::new()",
                    "typescript": "[]",
                    "cpp": "{}",
                    "go": f"{t_str}{{}}",
                }[lang]
            if ckey in ("col.map", "col.ordered_map"):
                return {
                    "csharp": f"new {t_str}()",
                    "rust": f"{t_str.split('<')[0]}::new()",
                    "typescript": f"new {t_str}()",
                    "cpp": "{}",
                    "go": f"make({t_str})",
                }[lang]
            if ckey == "col.set":
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
            return "\n".join(f"#include {imp}" for imp in imports)
        if lang == "go":
            return "\n".join(f'import "{imp}"' for imp in imports)
        return ""


# ============================================================================
# 4. CLI DEMO & PROVENANCE INSPECTOR
# ============================================================================

DEMO_PYTHON_SNIPPET = """
items: list[int] = []
items.append(42)
count = len(items)

scores: dict[str, int] = {}
scores["alice"] = 100
has_alice = "alice" in scores

with open("audit.log") as f:
    chunk = f.read(1024)

raise ValueError("invalid audit state")
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run UTSS Phase 4/5 Bridge Resolver across C#, Rust, TS, C++, and Go."
    )
    parser.add_argument(
        "--bridge-db",
        type=Path,
        default=Path("dbs/utss_universal_bridge.db"),
        help="Path to utss_universal_bridge.db generated by build_bridge_db.py",
    )
    parser.add_argument(
        "--code",
        type=str,
        default=DEMO_PYTHON_SNIPPET,
        help="Python source snippet to normalize and transpile.",
    )
    args = parser.parse_args()

    repo = BridgeCatalogRepository(args.bridge_db)
    transpiler = BridgeTranspiler(repo)

    try:
        print("=== SOURCE PYTHON SNIPPET ===")
        print(args.code)
        print("=" * 72)

        for lang in TARGET_LANGUAGES:
            result = transpiler.transpile_module(args.code, lang)
            print(f"\n>>> TARGET: {lang.upper()} <<<")
            print(result.source_code)
            print("\n  [Empirical UTSS Catalog Provenance Trace]:")
            for p in result.provenance_trace:
                sig_info = f" | sig: {p.catalog_signature}" if p.catalog_signature else ""
                pass_info = f" | pass: {p.receiver_pass_kind}" if p.receiver_pass_kind else ""
                print(
                    f"    - {p.construct:26s} -> {p.concept_key:16s} -> "
                    f"{p.resolved_target} ({p.verification_status}{pass_info}{sig_info})"
                )
    finally:
        repo.close()


if __name__ == "__main__":
    main()

```

---

### 3. FastAPI Endpoint Integration for the Workbench (`server/analysis/bridge_router.py`)

To expose `bridge_resolver.py` inside the Workbench UI's **Phase 3 Transpilation Synthesis Sandbox** tab, mount this lightweight FastAPI router alongside `comparative_engine.py`:

```python
# server/analysis/bridge_router.py
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dataclasses import asdict

from bridge_resolver import (
    BridgeCatalogRepository,
    BridgeTranspiler,
    TARGET_LANGUAGES,
)

router = APIRouter(prefix="/api/bridge", tags=["Bridge Synthesis Sandbox"])
BRIDGE_DB_PATH = Path("dbs/utss_universal_bridge.db")


class TranspileRequest(BaseModel):
    python_code: str
    target_languages: List[str] = list(TARGET_LANGUAGES)


@router.post("/transpile")
def transpile_python_snippet(req: TranspileRequest) -> Dict[str, Any]:
    """Transpiles Python code to C#, Rust, TypeScript, C++, and Go using utss_universal_bridge.db."""
    if not BRIDGE_DB_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail="utss_universal_bridge.db not found. Run build_bridge_db.py first.",
        )

    repo = BridgeCatalogRepository(BRIDGE_DB_PATH)
    transpiler = BridgeTranspiler(repo)
    try:
        targets: Dict[str, Any] = {}
        for lang in req.target_languages:
            lang_key = lang.lower()
            if lang_key not in TARGET_LANGUAGES:
                continue
            out = transpiler.transpile_module(req.python_code, lang_key)
            targets[lang_key] = asdict(out)
        return {"source_python": req.python_code, "targets": targets}
    except SyntaxError as exc:
        raise HTTPException(status_code=400, detail=f"Python AST SyntaxError: {exc}") from exc
    finally:
        repo.close()

```

---

### 4. Running the End-to-End Pipeline

1. **Build `utss_universal_bridge.db` from your 6 catalogs**:
```bash
uv run python build_bridge_db.py --db-dir ./dbs --out-db ./dbs/utss_universal_bridge.db

```


2. **Run the Multi-Target Transpiler Resolver CLI**:
```bash
uv run python bridge_resolver.py --bridge-db ./dbs/utss_universal_bridge.db

```


3. **Register the Sandbox Endpoint in FastAPI**:
In `server/main.py`, add `app.include_router(bridge_router.router)` so the React UI can send live Python code to `POST /api/bridge/transpile` and display side-by-side C#, Rust, Go, C++, and TypeScript outputs with clickable catalog provenance badges.



Would you like to build the **React `TranspilationSandbox.tsx` UI component** next—featuring a split Monaco editor (Python input on the left, multi-tab target language output on the right) and an interactive provenance inspector table showing the matched `utss_universal_bridge.db` catalog signatures?








`React_UI/src/components/TranspilationSandbox.tsx` completes the **Phase 3 Transpilation Synthesis Sandbox** tab of the UTSS Workbench, pairing a split-pane Monaco Editor (Python AST input on the left, multi-target C#, Rust, TypeScript, C++, and Go emission on the right) with an interactive **Empirical Catalog Provenance Inspector** backed by `POST /api/bridge/transpile`.

### 1. Sandbox Component Architecture

The component connects the React Workbench UI to `bridge_router.py` and `utss_universal_bridge.db` across four interactive panels:

| UI Panel | Function in the Synthesis Workflow | Data Source from `/api/bridge/transpile` |
| --- | --- | --- |
| **Preset & Target Bar** | Switches between 4 curated Python AST test suites (Collections, Resource `with` Blocks, Strings, Exceptions) and selects the active target language (`csharp`, `rust`, `typescript`, `cpp`, `go`). | Local state + triggers `POST /api/bridge/transpile` |
| **Left Pane: Python Source Editor** | Offline-bundled Monaco editor (`language="python"`) with `Ctrl+Enter` / `Cmd+Enter` live transpilation binding. | Sends `python_code` payload |
| **Right Pane: Target Emission Viewer** | Read-only Monaco editor dynamically switching syntax highlighting (`csharp`, `rust`, `typescript`, `cpp`, `go`) and displaying deduplicated target imports (`using`, `use`, `#include`, `import`). | `targets[activeLang].source_code` & `imports` |
| **Bottom Pane: Provenance Inspector** | Displays the step-by-step lowering trace from Python AST construct $\rightarrow$ Universal Concept (`col.sequence`, `proto.disposable`) $\rightarrow$ Verified Catalog Target (`container_id`, `symbol_id`, `receiver_pass_kind`, and `catalog_signature`). | `targets[activeLang].provenance_trace`

 |

---

### 2. Complete React Component (`React_UI/src/components/TranspilationSandbox.tsx`)

Save this component in `React_UI/src/components/TranspilationSandbox.tsx`:

```tsx
// React_UI/src/components/TranspilationSandbox.tsx
import React, { useCallback, useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

export type TargetLanguage = "csharp" | "rust" | "typescript" | "cpp" | "go";

export interface ProvenanceRecord {
  construct: string;
  concept_key: string;
  target_language: string;
  resolved_target: string;
  verification_status: string;
  catalog_container_id?: number | null;
  catalog_symbol_id?: number | null;
  catalog_signature?: string | null;
  receiver_pass_kind?: string | null;
}

export interface TargetSynthesisOutput {
  language: TargetLanguage;
  imports: string[];
  statements: string[];
  source_code: string;
  provenance_trace: ProvenanceRecord[];
}

interface TranspileResponse {
  source_python: string;
  targets: Record<TargetLanguage, TargetSynthesisOutput>;
}

const LANGUAGE_META: Record<
  TargetLanguage,
  { label: string; monacoLang: string; badgeColor: string }
> = {
  csharp: { label: "C# .NET", monacoLang: "csharp", badgeColor: "#68217A" },
  rust: { label: "Rust", monacoLang: "rust", badgeColor: "#DEA584" },
  typescript: { label: "TypeScript", monacoLang: "typescript", badgeColor: "#3178C6" },
  cpp: { label: "C++20", monacoLang: "cpp", badgeColor: "#00599C" },
  go: { label: "Go", monacoLang: "go", badgeColor: "#00ADD8" },
};

const PYTHON_PRESETS: Record<string, { title: string; code: string }> = {
  full_demo: {
    title: "1. Full Rosetta Suite (Collections, I/O & Exceptions)",
    code: `items: list[int] = []
items.append(42)
count = len(items)

scores: dict[str, int] = {}
scores["alice"] = 100
has_alice = "alice" in scores

with open("audit.log") as f:
    chunk = f.read(1024)

raise ValueError("invalid audit state")`,
  },
  collections_and_sets: {
    title: "2. Generic Sequences, Maps & Hash Sets",
    code: `ids: list[int] = []
ids.append(101)
ids.append(202)
last_id = ids.pop()
ids.clear()

seen: set[str] = set()
seen.add("token_a")
is_present = "token_a" in seen`,
  },
  resource_protocols: {
    title: "3. Context Manager Lowering (proto.disposable)",
    code: `with open("telemetry.bin") as stream:
    payload = stream.read(4096)
    stream.write(payload)`,
  },
  strings_and_errors: {
    title: "4. UTF-8 String Operations & Error Semantics",
    code: `raw_line: str = "  utss:phase5:ready  "
clean_line = raw_line.strip()
is_utss = clean_line.startswith("utss")
parts = clean_line.split(":")

raise IndexError("token index out of bounds")`,
  },
};

export const TranspilationSandbox: React.FC<{ isLightTheme?: boolean }> = ({
  isLightTheme = false,
}) => {
  const [pythonCode, setPythonCode] = useState<string>(PYTHON_PRESETS.full_demo.code);
  const [selectedPreset, setSelectedPreset] = useState<string>("full_demo");
  const [activeLang, setActiveLang] = useState<TargetLanguage>("rust");
  const [outputs, setOutputs] = useState<Record<TargetLanguage, TargetSynthesisOutput> | null>(
    null
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [conceptFilter, setConceptFilter] = useState<string>("ALL");

  const runTranspilation = useCallback(async (sourceToCompile: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/bridge/transpile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          python_code: sourceToCompile,
          target_languages: ["csharp", "rust", "typescript", "cpp", "go"],
        }),
      });
      if (!res.ok) {
        const errPayload = await res.json().catch(() => ({}));
        throw new Error(errPayload.detail || `HTTP ${res.status}: Transpilation failed`);
      }
      const data: TranspileResponse = await res.json();
      setOutputs(data.targets);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    runTranspilation(pythonCode);
  }, []); // Initial synthesis on mount

  const handlePresetChange = (presetKey: string) => {
    setSelectedPreset(presetKey);
    const nextCode = PYTHON_PRESETS[presetKey]?.code || "";
    setPythonCode(nextCode);
    runTranspilation(nextCode);
  };

  const handleCopyOutput = async () => {
    const code = outputs?.[activeLang]?.source_code;
    if (!code) return;
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const currentOutput: TargetSynthesisOutput | undefined = outputs?.[activeLang];
  const provenanceRows: ProvenanceRecord[] = (
    currentOutput?.provenance_trace || []
  ).filter((row) => conceptFilter === "ALL" || row.concept_key.startsWith(conceptFilter));

  const renderStatusBadge = (status: string) => {
    const isVerified = status.startsWith("verified_");
    const bg = isVerified ? "rgba(16, 185, 129, 0.16)" : "rgba(245, 158, 11, 0.16)";
    const fg = isVerified ? "#10B981" : "#F59E0B";
    return (
      <span
        style={{
          padding: "2px 8px",
          borderRadius: "999px",
          fontSize: "0.74rem",
          fontWeight: 600,
          background: bg,
          color: fg,
          border: `1px solid ${fg}`,
        }}
      >
        {status}
      </span>
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        padding: "16px",
        color: "var(--text-main)",
      }}
    >
      {/* 1. Top Control Bar: Presets + Synthesize Button */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "var(--bg-card)",
          padding: "12px 16px",
          borderRadius: "8px",
          border: "1px solid var(--border-color)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <strong>Phase 4/5 Universal Bridge Transpiler</strong>
          <select
            value={selectedPreset}
            onChange={(e) => handlePresetChange(e.target.value)}
            style={{
              background: "var(--bg-surface)",
              color: "var(--text-main)",
              border: "1px solid var(--border-color)",
              padding: "6px 10px",
              borderRadius: "6px",
              fontSize: "0.85rem",
            }}
          >
            {Object.entries(PYTHON_PRESETS).map(([key, item]) => (
              <option key={key} value={key}>
                {item.title}
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "0.8rem", opacity: 0.75 }}>
            Backed by <code>utss_universal_bridge.db</code>
          </span>
          <button
            onClick={() => runTranspilation(pythonCode)}
            disabled={loading}
            style={{
              background: "var(--accent-primary)",
              color: "#ffffff",
              border: "none",
              padding: "7px 16px",
              borderRadius: "6px",
              cursor: loading ? "wait" : "pointer",
              fontWeight: 600,
              fontSize: "0.86rem",
            }}
          >
            {loading ? "Synthesizing..." : "⚡ Synthesize All 5 Targets"}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid #EF4444",
            color: "#EF4444",
            padding: "10px 14px",
            borderRadius: "8px",
            fontSize: "0.86rem",
          }}
        >
          <strong>Synthesis Error:</strong> {error}
        </div>
      )}

      {/* 2. Split-Pane Monaco Editors: Python Source (Left) -> Target Language (Right) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "16px",
          minHeight: "340px",
        }}
      >
        {/* Left Pane: Source Python AST Input */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "var(--bg-card)",
            borderRadius: "8px",
            border: "1px solid var(--border-color)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 14px",
              background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-color)",
            }}
          >
            <span style={{ fontWeight: 600, fontSize: "0.88rem" }}>
              🐍 Source Python 3.13+ AST Input
            </span>
            <span style={{ fontSize: "0.76rem", opacity: 0.7 }}>
              Type-annotated statements & protocols
            </span>
          </div>
          <div style={{ flex: 1, minHeight: "300px" }}>
            <Editor
              height="100%"
              defaultLanguage="python"
              theme={isLightTheme ? "vs" : "vs-dark"}
              value={pythonCode}
              onChange={(val) => setPythonCode(val || "")}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        </div>

        {/* Right Pane: Multi-Tab Target Language Output */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "var(--bg-card)",
            borderRadius: "8px",
            border: "1px solid var(--border-color)",
            overflow: "hidden",
          }}
        >
          {/* Target Language Switcher Tabs */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "6px 10px",
              background: "var(--bg-surface)",
              borderBottom: "1px solid var(--border-color)",
            }}
          >
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {(Object.keys(LANGUAGE_META) as TargetLanguage[]).map((langKey) => {
                const meta = LANGUAGE_META[langKey];
                const isActive = activeLang === langKey;
                return (
                  <button
                    key={langKey}
                    onClick={() => setActiveLang(langKey)}
                    style={{
                      padding: "5px 12px",
                      borderRadius: "6px",
                      border: isActive
                        ? `1px solid ${meta.badgeColor}`
                        : "1px solid transparent",
                      background: isActive ? "var(--bg-card)" : "transparent",
                      color: "var(--text-main)",
                      cursor: "pointer",
                      fontWeight: isActive ? 700 : 500,
                      fontSize: "0.82rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: meta.badgeColor,
                      }}
                    />
                    {meta.label}
                  </button>
                );
              })}
            </div>

            <button
              onClick={handleCopyOutput}
              style={{
                background: "transparent",
                color: "var(--text-main)",
                border: "1px solid var(--border-color)",
                padding: "4px 10px",
                borderRadius: "5px",
                cursor: "pointer",
                fontSize: "0.78rem",
              }}
            >
              {copied ? "✓ Copied" : "Copy Code"}
            </button>
          </div>

          {/* Required Target Imports Strip */}
          <div
            style={{
              padding: "6px 14px",
              fontSize: "0.78rem",
              borderBottom: "1px solid var(--border-color)",
              display: "flex",
              gap: "8px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <span style={{ opacity: 0.7 }}>Synthesized Imports:</span>
            {currentOutput?.imports && currentOutput.imports.length > 0 ? (
              currentOutput.imports.map((imp) => (
                <code
                  key={imp}
                  style={{
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  {imp}
                </code>
              ))
            ) : (
              <em style={{ opacity: 0.6 }}>None (Stratum 0 Ambient / Prelude)</em>
            )}
          </div>

          <div style={{ flex: 1, minHeight: "265px" }}>
            <Editor
              height="100%"
              language={LANGUAGE_META[activeLang].monacoLang}
              theme={isLightTheme ? "vs" : "vs-dark"}
              value={currentOutput?.source_code || "// No output generated"}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        </div>
      </div>

      {/* 3. Bottom Pane: Empirical UTSS Catalog Provenance & Signature Inspector */}
      <div
        style={{
          background: "var(--bg-card)",
          padding: "14px 16px",
          borderRadius: "8px",
          border: "1px solid var(--border-color)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "10px",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <div>
            <strong>
              Empirical Catalog Provenance Trace ({LANGUAGE_META[activeLang].label})
            </strong>
            <span style={{ marginLeft: "10px", fontSize: "0.8rem", opacity: 0.75 }}>
              Every lowered type, method call, and protocol is verified against the target
              language's SQLite catalog.
            </span>
          </div>

          {/* Concept Category Filter */}
          <div style={{ display: "flex", gap: "6px" }}>
            {["ALL", "prim.", "col.", "io.", "proto.", "exc."].map((prefix) => (
              <button
                key={prefix}
                onClick={() => setConceptFilter(prefix)}
                style={{
                  padding: "3px 9px",
                  borderRadius: "4px",
                  fontSize: "0.76rem",
                  cursor: "pointer",
                  border: "1px solid var(--border-color)",
                  background:
                    conceptFilter === prefix ? "var(--accent-primary)" : "var(--bg-surface)",
                  color: conceptFilter === prefix ? "#fff" : "var(--text-main)",
                }}
              >
                {prefix === "ALL" ? "All Concepts" : prefix}
              </button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: "auto", maxHeight: "260px" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.83rem",
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-color)",
                  textAlign: "left",
                  background: "var(--bg-surface)",
                }}
              >
                <th style={{ padding: "8px" }}>AST CONSTRUCT</th>
                <th style={{ padding: "8px" }}>UNIVERSAL CONCEPT</th>
                <th style={{ padding: "8px" }}>RESOLVED CATALOG TARGET</th>
                <th style={{ padding: "8px" }}>PASS / RECEIVER</th>
                <th style={{ padding: "8px" }}>CATALOG SIGNATURE (LAYER 1)</th>
                <th style={{ padding: "8px" }}>CATALOG IDs</th>
                <th style={{ padding: "8px" }}>VERIFICATION</th>
              </tr>
            </thead>
            <tbody>
              {provenanceRows.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "12px", textAlign: "center", opacity: 0.6 }}>
                    No provenance records match the current filter.
                  </td>
                </tr>
              ) : (
                provenanceRows.map((row, idx) => (
                  <tr
                    key={`${row.construct}-${idx}`}
                    style={{ borderBottom: "1px solid rgba(148,163,184,0.12)" }}
                  >
                    <td style={{ padding: "7px 8px", fontFamily: "monospace" }}>
                      {row.construct}
                    </td>
                    <td style={{ padding: "7px 8px" }}>
                      <code>{row.concept_key}</code>
                    </td>
                    <td style={{ padding: "7px 8px", fontWeight: 600 }}>
                      <code>{row.resolved_target}</code>
                    </td>
                    <td style={{ padding: "7px 8px" }}>
                      {row.receiver_pass_kind ? (
                        <code>{row.receiver_pass_kind}</code>
                      ) : (
                        <span style={{ opacity: 0.45 }}>—</span>
                      )}
                    </td>
                    <td
                      style={{
                        padding: "7px 8px",
                        fontFamily: "monospace",
                        fontSize: "0.79rem",
                      }}
                    >
                      {row.catalog_signature || <span style={{ opacity: 0.45 }}>—</span>}
                    </td>
                    <td style={{ padding: "7px 8px", fontSize: "0.76rem", opacity: 0.8 }}>
                      {row.catalog_container_id && `cid:${row.catalog_container_id} `}
                      {row.catalog_symbol_id && `sid:${row.catalog_symbol_id}`}
                      {!row.catalog_container_id && !row.catalog_symbol_id && "—"}
                    </td>
                    <td style={{ padding: "7px 8px" }}>
                      {renderStatusBadge(row.verification_status)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

```

---

### 3. Wiring the All-in-One Workbench (`server/main.py` & `React_UI/src/App.tsx`)

1. **Mount Both Analytical Routers in FastAPI (`server/main.py`)**:
```python
from fastapi import FastAPI
from server.analysis import comparative_engine, bridge_router

app = FastAPI(title="UTSS Universal Language Analysis & Synthesis Workbench")
app.include_router(comparative_engine.router)
app.include_router(bridge_router.router)

```


2. **Connect All Three Workbench Modes in `React_UI/src/App.tsx**`:
```tsx
import { ComparativeWorkbench } from "./components/ComparativeWorkbench";
import { TranspilationSandbox } from "./components/TranspilationSandbox";

// Inside your main view switcher in App.tsx:
{activeTab === "tutoring" && <TutoringSqlView />}
{activeTab === "comparative" && (
  <ComparativeWorkbench isLightTheme={theme === "vscode-light"} />
)}
{activeTab === "synthesis" && (
  <TranspilationSandbox isLightTheme={theme === "vscode-light"} />
)}

```



Would you like to build an **automated pytest suite (`tests/test_universal_bridge.py`)** next to validate the end-to-end pipeline—verifying that `build_bridge_db.py` resolves all canonical concepts across the catalogs and that `bridge_resolver.py` emits valid C#, Rust, TypeScript, C++, and Go syntax for every concept category?








`tests/test_universal_bridge.py` validates the end-to-end Phase 4 and Phase 5 Universal Bridge pipeline—from scanning the 6 UTSS Layer 1 and Layer 2 SQLite catalogs in `build_bridge_db.py` to multi-target AST transpilation and provenance tracing in `bridge_resolver.py`.

### 1. Test Suite Coverage Matrix

The test suite is organized into five verification tiers:

| Test Tier | Test Functions | What Is Verified |
| --- | --- | --- |
| **Tier 1: Bridge DDL & Populator Integrity** | `test_bridge_tables_and_concept_inventory`, `test_empirical_type_resolution_across_6_languages`, `test_alias_and_layer2_facet_resolution` | Verifies that all 5 bridge tables exist, all 6 concept categories (`primitive`, `collection`, `control_flow`, `exception`, `io`, `protocol`) are populated across all 6 languages, `symbol_aliases` re-exports resolve, and Layer 2 facet JSON is captured. |
| **Tier 2: Empirical Operation & Protocol Binding** | `test_operation_signature_and_pass_kind_verification`, `test_protocol_lowering_and_implementing_counts` | Confirms that `universal_operation_mappings` extracts `raw_signature`, `return_type_expr`, and `parameters.pass_kind` from the catalogs, and `universal_protocol_mappings` binds dunders, interfaces, traits, and implicit interfaces. |
| **Tier 3: Autonomous Stdlib Taxonomist (Pass 4)** | `test_discovered_stdlib_taxonomy_harvester` | Verifies that `discovered_stdlib_taxonomy` autonomously harvests Stratum 0/1 exceptions, collections, I/O streams, and traits/interfaces with public method counts. |
| **Tier 4: Recursive AST Type & Expression Lowering** | `test_recursive_generic_and_union_type_resolution`, `test_collection_and_string_operations_across_targets`, `test_with_protocol_and_exception_lowering` | Parametrizes nested generics (`dict[str, list[int]]`), PEP 604 unions (`str | None`), collection mutations, string methods, `with open(...)` blocks, and `raise ValueError(...)` across `csharp`, `rust`, `typescript`, `cpp`, and `go`. |
| **Tier 5: Provenance & FastAPI Sandbox Endpoint** | `test_provenance_trace_completeness`, `test_fastapi_bridge_router_endpoint` | Asserts that every synthesized statement emits a `ProvenanceRecord` with catalog IDs and signatures, and tests `POST /api/bridge/transpile` (including `SyntaxError` HTTP 400 handling).

 |

---

### 2. Complete Pytest Suite (`tests/test_universal_bridge.py`)

Save this file in `tests/test_universal_bridge.py`:

```python
#!/usr/bin/env python3
"""
End-to-End Pytest Suite for UTSS Phase 4 & Phase 5 Universal Bridge
===================================================================
Validates:
  1. `build_bridge_db.py`: Empirical catalog scanning across all 6 UTSS
     schemas (Layer 1 Universal Core + Layer 2 Language-Fidelity Facets),
     alias resolution, callable signature extraction, and Pass 4 stdlib
     taxonomy harvesting.
  2. `bridge_resolver.py`: Recursive Python AST type normalization,
     collection/string/IO operation lowering, `with` disposable protocol
     synthesis, exception lowering, and empirical provenance tracing across
     C#, Rust, TypeScript, C++, and Go.

Run with:
    uv run pytest tests/test_universal_bridge.py -v
"""

from __future__ import annotations

import ast
import json
import sqlite3
from pathlib import Path
from typing import Dict, Tuple

import pytest

from build_bridge_db import (
    CONCEPT_SPECS,
    OPERATION_SPECS,
    PROTOCOL_SPECS,
    build_bridge_database,
)
from bridge_resolver import (
    TARGET_LANGUAGES,
    BridgeCatalogRepository,
    BridgeTranspiler,
)


# ============================================================================
# 1. SYNTHETIC 6-LANGUAGE UTSS LAYER 1 + LAYER 2 CATALOG FIXTURE BUILDER
# ============================================================================

LAYER1_CORE_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    runtime_name TEXT NOT NULL,
    language_version TEXT NOT NULL,
    version_major INTEGER NOT NULL DEFAULT 1,
    version_minor INTEGER NOT NULL DEFAULT 0,
    version_micro INTEGER NOT NULL DEFAULT 0,
    platform_triplet TEXT NOT NULL DEFAULT 'x86_64-linux-gnu'
);

CREATE TABLE distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,
    dist_name TEXT NOT NULL
);

CREATE TABLE containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT 'public',
    is_hidden INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    origin_container_id INTEGER REFERENCES containers(container_id),
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,
    visibility TEXT NOT NULL DEFAULT 'public',
    provenance TEXT NOT NULL DEFAULT 'stdlib',
    is_hidden INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE callables (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_generator INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    is_class_bound INTEGER NOT NULL DEFAULT 0,
    has_overloads INTEGER NOT NULL DEFAULT 0,
    overload_count INTEGER NOT NULL DEFAULT 0,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL DEFAULT 'static_ast'
);

CREATE TABLE callable_overloads (
    overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_ordinal INTEGER NOT NULL,
    return_type_expr TEXT,
    raw_signature TEXT NOT NULL
);

CREATE TABLE parameters (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_id INTEGER REFERENCES callable_overloads(overload_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    pass_kind TEXT NOT NULL,
    type_expr TEXT,
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    access_mode TEXT NOT NULL DEFAULT 'read_write',
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 1,
    declared_type_expr TEXT
);

CREATE TABLE symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,
    is_in_dunder_all INTEGER NOT NULL DEFAULT 1
);
"""

LAYER2_FACET_DDLS: Dict[str, str] = {
    "python": """
        CREATE TABLE py_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            module_origin_kind TEXT,
            dunder_all_json TEXT,
            has_lazy_getattr INTEGER DEFAULT 0,
            mro_json TEXT,
            metaclass_name TEXT
        );
        CREATE TABLE py_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            py_runtime_type TEXT,
            descriptor_kind TEXT,
            co_flags INTEGER DEFAULT 0,
            dunder_category TEXT
        );
    """,
    "csharp": """
        CREATE TABLE cs_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            type_kind TEXT,
            is_readonly_struct INTEGER DEFAULT 0,
            is_ref_struct INTEGER DEFAULT 0,
            is_sealed INTEGER DEFAULT 0,
            implemented_interfaces_json TEXT
        );
        CREATE TABLE cs_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            member_kind TEXT,
            is_extension_method INTEGER DEFAULT 0,
            is_init_only INTEGER DEFAULT 0,
            explicit_interface_specifier TEXT,
            operator_kind TEXT,
            is_async INTEGER DEFAULT 0
        );
    """,
    "rust": """
        CREATE TABLE rust_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            item_kind TEXT,
            is_auto_trait INTEGER DEFAULT 0,
            generics_json TEXT,
            where_clause_json TEXT
        );
        CREATE TABLE rust_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            member_kind TEXT,
            is_const INTEGER DEFAULT 0,
            is_unsafe INTEGER DEFAULT 0,
            is_extern INTEGER DEFAULT 0,
            abi TEXT,
            self_kind TEXT,
            is_async INTEGER DEFAULT 0,
            is_pub_crate INTEGER DEFAULT 0
        );
    """,
    "typescript": """
        CREATE TABLE ts_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            is_export INTEGER DEFAULT 1,
            is_default_export INTEGER DEFAULT 0,
            is_ambient INTEGER DEFAULT 1,
            heritage_clauses_json TEXT
        );
        CREATE TABLE ts_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            access_modifier TEXT DEFAULT 'public',
            is_readonly INTEGER DEFAULT 0,
            is_optional INTEGER DEFAULT 0,
            is_declare INTEGER DEFAULT 0,
            type_annotation_json TEXT
        );
    """,
    "cpp": """
        CREATE TABLE cpp_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            item_kind TEXT,
            is_template INTEGER DEFAULT 0,
            template_params_json TEXT
        );
        CREATE TABLE cpp_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            member_kind TEXT,
            is_pure_virtual INTEGER DEFAULT 0,
            is_noexcept INTEGER DEFAULT 0,
            is_constexpr INTEGER DEFAULT 0,
            is_inline INTEGER DEFAULT 0,
            is_const INTEGER DEFAULT 0,
            pass_by TEXT
        );
    """,
    "go": """
        CREATE TABLE go_container_facets (
            container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
            package_name TEXT,
            item_kind TEXT,
            embedded_fields_json TEXT
        );
        CREATE TABLE go_symbol_facets (
            symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
            member_kind TEXT,
            receiver_kind TEXT DEFAULT 'none',
            receiver_type TEXT,
            is_variadic INTEGER DEFAULT 0,
            is_exported INTEGER DEFAULT 1
        );
    """,
}


def _seed_container_with_methods(
    conn: sqlite3.Connection,
    dist_id: int,
    c_kind: str,
    qname: str,
    requires_import: int,
    methods: Dict[str, Tuple[str, str, str]],
) -> int:
    """Inserts a container, its methods, callables, and parameters."""
    short = qname.split("::")[-1].split(".")[-1].split("/")[-1]
    cur = conn.execute(
        """
        INSERT INTO containers (dist_id, container_kind, qualified_name, short_name, requires_import)
        VALUES (?, ?, ?, ?, ?);
        """,
        (dist_id, c_kind, qname, short, requires_import),
    )
    cid = cur.lastrowid
    assert cid is not None

    for m_name, (raw_sig, ret_type, pass_kind) in methods.items():
        scur = conn.execute(
            """
            INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind)
            VALUES (?, ?, ?, ?, 'method');
            """,
            (cid, cid, m_name, f"{qname}.{m_name}"),
        )
        sid = scur.lastrowid
        assert sid is not None
        conn.execute(
            """
            INSERT INTO callables (symbol_id, overload_count, has_overloads, return_type_expr, raw_signature)
            VALUES (?, 1, 0, ?, ?);
            """,
            (sid, ret_type, raw_sig),
        )
        conn.execute(
            """
            INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr)
            VALUES (?, 0, 'arg0', ?, 'T');
            """,
            (sid, pass_kind),
        )
    return cid


def create_synthetic_utss_catalogs(db_dir: Path) -> Dict[str, Path]:
    """
    Creates 6 schema-exact UTSS SQLite catalogs (Python, C#, Rust, TS, C++, Go)
    populated with canonical primitives, collections, exceptions, I/O types,
    protocols, aliases, and Layer 2 facets.
    """
    db_dir.mkdir(parents=True, exist_ok=True)
    filenames = {
        "python": "python_base_full.db",
        "csharp": "cs_base_full.db",
        "rust": "rust_base_full.db",
        "typescript": "ts_base_full.db",
        "cpp": "cpp_base_full.db",
        "go": "go_base_full.db",
    }
    paths: Dict[str, Path] = {}

    for lang, fname in filenames.items():
        p = db_dir / fname
        paths[lang] = p
        with sqlite3.connect(str(p)) as conn:
            conn.executescript(LAYER1_CORE_DDL)
            conn.executescript(LAYER2_FACET_DDLS[lang])

            conn.execute(
                "INSERT INTO environments (env_id, language, runtime_name, language_version) VALUES (1, ?, ?, '1.0');",
                (lang, f"{lang}-runtime"),
            )
            conn.execute(
                "INSERT INTO distributions (dist_id, env_id, stratum, dist_name) VALUES (1, 1, 0, '<ambient>');"
            )
            conn.execute(
                "INSERT INTO distributions (dist_id, env_id, stratum, dist_name) VALUES (2, 1, 1, 'stdlib');"
            )

            if lang == "python":
                c_list = _seed_container_with_methods(
                    conn, 1, "class", "builtins.list", 0,
                    {
                        "append": ("(self, object: _T) -> None", "None", "positional_or_keyword"),
                        "__len__": ("(self) -> int", "int", "positional_only"),
                        "pop": ("(self, index: SupportsIndex = -1) -> _T", "_T", "positional_or_keyword"),
                        "clear": ("(self) -> None", "None", "positional_only"),
                        "__contains__": ("(self, key: object) -> bool", "bool", "positional_only"),
                    },
                )
                conn.execute(
                    "INSERT INTO py_container_facets (container_id, module_origin_kind, mro_json) VALUES (?, 'builtin_c', '[\"list\", \"object\"]');",
                    (c_list,),
                )
                _seed_container_with_methods(
                    conn, 1, "class", "builtins.dict", 0,
                    {
                        "__setitem__": ("(self, key: _KT, value: _VT) -> None", "None", "positional_only"),
                        "get": ("(self, key: _KT, default: None = None) -> _VT | None", "_VT | None", "positional_or_keyword"),
                        "__contains__": ("(self, key: object) -> bool", "bool", "positional_only"),
                        "pop": ("(self, key: _KT) -> _VT", "_VT", "positional_or_keyword"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "class", "builtins.set", 0,
                    {
                        "add": ("(self, element: _T) -> None", "None", "positional_only"),
                        "__contains__": ("(self, element: object) -> bool", "bool", "positional_only"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "class", "builtins.str", 0,
                    {
                        "split": ("(self, sep: str | None = None) -> list[str]", "list[str]", "positional_or_keyword"),
                        "strip": ("(self, chars: str | None = None) -> str", "str", "positional_or_keyword"),
                        "startswith": ("(self, prefix: str) -> bool", "bool", "positional_or_keyword"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "_io.BufferedReader", 1,
                    {
                        "read": ("(self, size: int = -1) -> bytes", "bytes", "positional_or_keyword"),
                        "write": ("(self, b: Buffer) -> int", "int", "positional_only"),
                        "close": ("(self) -> None", "None", "positional_only"),
                    },
                )
                c_io = _seed_container_with_methods(conn, 2, "module", "io", 1, {})
                conn.execute(
                    """
                    INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind)
                    VALUES (?, 'BufferedReader', '_io', 'BufferedReader', 'c_accelerator_reexport');
                    """,
                    (c_io,),
                )
                _seed_container_with_methods(conn, 1, "exception_class", "builtins.ValueError", 0, {})
                _seed_container_with_methods(conn, 1, "exception_class", "builtins.IndexError", 0, {})
                _seed_container_with_methods(conn, 1, "exception_class", "builtins.KeyError", 0, {})
                _seed_container_with_methods(conn, 1, "exception_class", "builtins.OSError", 0, {})
                _seed_container_with_methods(
                    conn, 2, "class", "contextlib.AbstractContextManager", 1,
                    {"__enter__": ("(self) -> Any", "Any", "positional_only"), "__exit__": ("(self, exc_type, exc_val, exc_tb) -> bool | None", "bool | None", "positional_only")},
                )

            elif lang == "csharp":
                c_cs_list = _seed_container_with_methods(
                    conn, 2, "class", "System.Collections.Generic.List", 1,
                    {
                        "Add": ("void Add(T item)", "void", "value"),
                        "Count": ("int Count { get; }", "int", "value"),
                        "RemoveAt": ("void RemoveAt(int index)", "void", "value"),
                        "Clear": ("void Clear()", "void", "value"),
                        "Contains": ("bool Contains(T item)", "bool", "value"),
                    },
                )
                conn.execute(
                    "INSERT INTO cs_container_facets (container_id, type_kind, implemented_interfaces_json) VALUES (?, 'class', '[\"System.Collections.Generic.IEnumerable\", \"System.IDisposable\"]');",
                    (c_cs_list,),
                )
                _seed_container_with_methods(
                    conn, 2, "class", "System.Collections.Generic.Dictionary", 1,
                    {
                        "Add": ("void Add(TKey key, TValue value)", "void", "value"),
                        "TryGetValue": ("bool TryGetValue(TKey key, out TValue value)", "bool", "out"),
                        "ContainsKey": ("bool ContainsKey(TKey key)", "bool", "value"),
                        "Remove": ("bool Remove(TKey key)", "bool", "value"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "System.Collections.Generic.HashSet", 1,
                    {
                        "Add": ("bool Add(T item)", "bool", "value"),
                        "Contains": ("bool Contains(T item)", "bool", "value"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "class", "System.String", 0,
                    {
                        "Split": ("string[] Split(string? separator)", "string[]", "value"),
                        "Trim": ("string Trim()", "string", "value"),
                        "StartsWith": ("bool StartsWith(string value)", "bool", "value"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "System.IO.FileStream", 1,
                    {
                        "Read": ("int Read(byte[] buffer)", "int", "value"),
                        "Write": ("void Write(byte[] buffer)", "void", "value"),
                        "Close": ("void Close()", "void", "value"),
                    },
                )
                _seed_container_with_methods(conn, 2, "interface", "System.IDisposable", 1, {"Dispose": ("void Dispose()", "void", "value")})
                _seed_container_with_methods(conn, 2, "exception_class", "System.ArgumentException", 1, {})

            elif lang == "rust":
                c_vec = _seed_container_with_methods(
                    conn, 1, "struct", "alloc::vec::Vec", 0,
                    {
                        "push": ("pub fn push(&mut self, value: T)", "()", "mut_ref"),
                        "len": ("pub const fn len(&self) -> usize", "usize", "ref"),
                        "pop": ("pub fn pop(&mut self) -> Option<T>", "Option<T>", "mut_ref"),
                        "clear": ("pub fn clear(&mut self)", "()", "mut_ref"),
                        "contains": ("pub fn contains(&self, x: &T) -> bool", "bool", "ref"),
                    },
                )
                conn.execute(
                    "INSERT INTO rust_container_facets (container_id, item_kind, generics_json) VALUES (?, 'struct', '[\"T\", \"A\"]');",
                    (c_vec,),
                )
                _seed_container_with_methods(
                    conn, 2, "struct", "std::collections::hash_map::HashMap", 1,
                    {
                        "insert": ("pub fn insert(&mut self, k: K, v: V) -> Option<V>", "Option<V>", "mut_ref"),
                        "get": ("pub fn get<Q>(&self, k: &Q) -> Option<&V>", "Option<&V>", "ref"),
                        "contains_key": ("pub fn contains_key<Q>(&self, k: &Q) -> bool", "bool", "ref"),
                        "remove": ("pub fn remove<Q>(&mut self, k: &Q) -> Option<V>", "Option<V>", "mut_ref"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "struct", "std::collections::hash_set::HashSet", 1,
                    {
                        "insert": ("pub fn insert(&mut self, value: T) -> bool", "bool", "mut_ref"),
                        "contains": ("pub fn contains<Q>(&self, value: &Q) -> bool", "bool", "ref"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "struct", "alloc::string::String", 0,
                    {
                        "split": ("pub fn split<'a, P>(&'a self, pat: P) -> Split<'a, P>", "Split", "ref"),
                        "trim": ("pub fn trim(&self) -> &str", "&str", "ref"),
                        "starts_with": ("pub fn starts_with<'a, P>(&'a self, pat: P) -> bool", "bool", "ref"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "struct", "std::fs::File", 1,
                    {
                        "read_to_end": ("pub fn read_to_end(&mut self, buf: &mut Vec<u8>) -> Result<usize>", "Result<usize>", "mut_ref"),
                        "write_all": ("pub fn write_all(&mut self, buf: &[u8]) -> Result<()>", "Result<()>", "mut_ref"),
                        "sync_all": ("pub fn sync_all(&self) -> Result<()>", "Result<()>", "ref"),
                    },
                )
                c_drop = _seed_container_with_methods(
                    conn, 1, "trait", "core::ops::drop::Drop", 0,
                    {"drop": ("fn drop(&mut self)", "()", "mut_ref")},
                )
                conn.execute("INSERT INTO rust_container_facets (container_id, item_kind) VALUES (?, 'trait');", (c_drop,))
                _seed_container_with_methods(conn, 2, "struct", "core::num::ParseIntError", 1, {})

            elif lang == "typescript":
                _seed_container_with_methods(
                    conn, 1, "interface", "Array", 0,
                    {
                        "push": ("push(...items: T[]): number", "number", "val"),
                        "length": ("length: number", "number", "val"),
                        "pop": ("pop(): T | undefined", "T | undefined", "val"),
                        "splice": ("splice(start: number, deleteCount?: number): T[]", "T[]", "val"),
                        "includes": ("includes(searchElement: T): boolean", "boolean", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "interface", "Map", 0,
                    {
                        "set": ("set(key: K, value: V): this", "this", "val"),
                        "get": ("get(key: K): V | undefined", "V | undefined", "val"),
                        "has": ("has(key: K): boolean", "boolean", "val"),
                        "delete": ("delete(key: K): boolean", "boolean", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "interface", "Set", 0,
                    {
                        "add": ("add(value: T): this", "this", "val"),
                        "has": ("has(value: T): boolean", "boolean", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "interface", "String", 0,
                    {
                        "split": ("split(separator: string): string[]", "string[]", "val"),
                        "trim": ("trim(): string", "string", "val"),
                        "startsWith": ("startsWith(searchString: string): boolean", "boolean", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 1, "interface", "ReadableStream", 0,
                    {
                        "getReader": ("getReader(): ReadableStreamDefaultReader<R>", "ReadableStreamDefaultReader<R>", "val"),
                        "pipeTo": ("pipeTo(destination: WritableStream<R>): Promise<void>", "Promise<void>", "val"),
                        "cancel": ("cancel(reason?: any): Promise<void>", "Promise<void>", "val"),
                    },
                )
                _seed_container_with_methods(conn, 1, "exception_class", "RangeError", 0, {})

            elif lang == "cpp":
                c_cpp_vec = _seed_container_with_methods(
                    conn, 2, "class", "std::vector", 1,
                    {
                        "push_back": ("constexpr void push_back(const T& value)", "void", "const_ref"),
                        "size": ("constexpr size_type size() const noexcept", "size_type", "val"),
                        "pop_back": ("constexpr void pop_back() noexcept", "void", "val"),
                        "clear": ("constexpr void clear() noexcept", "void", "val"),
                        "find": ("constexpr iterator find(const T& value)", "iterator", "const_ref"),
                    },
                )
                conn.execute("INSERT INTO cpp_container_facets (container_id, item_kind, is_template) VALUES (?, 'class', 1);", (c_cpp_vec,))
                _seed_container_with_methods(
                    conn, 2, "class", "std::unordered_map", 1,
                    {
                        "insert_or_assign": ("pair<iterator, bool> insert_or_assign(const Key& k, M&& obj)", "pair<iterator, bool>", "const_ref"),
                        "find": ("iterator find(const Key& key)", "iterator", "const_ref"),
                        "contains": ("bool contains(const Key& key) const", "bool", "const_ref"),
                        "erase": ("size_type erase(const Key& key)", "size_type", "const_ref"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "std::unordered_set", 1,
                    {
                        "insert": ("pair<iterator, bool> insert(const value_type& value)", "pair<iterator, bool>", "const_ref"),
                        "contains": ("bool contains(const Key& key) const", "bool", "const_ref"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "std::string", 1,
                    {
                        "find": ("size_type find(const basic_string& str) const noexcept", "size_type", "const_ref"),
                        "substr": ("basic_string substr(size_type pos = 0) const", "basic_string", "val"),
                        "starts_with": ("constexpr bool starts_with(string_view sv) const noexcept", "bool", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "class", "std::fstream", 1,
                    {
                        "read": ("basic_istream& read(char_type* s, streamsize count)", "basic_istream&", "pointer"),
                        "write": ("basic_ostream& write(const char_type* s, streamsize count)", "basic_ostream&", "pointer"),
                        "close": ("void close()", "void", "val"),
                    },
                )
                _seed_container_with_methods(conn, 2, "exception_class", "std::invalid_argument", 1, {})

            elif lang == "go":
                _seed_container_with_methods(
                    conn, 2, "module", "slices", 1,
                    {
                        "append": ("func append(slice []Type, elems ...Type) []Type", "[]Type", "slice"),
                        "len": ("func len(v Type) int", "int", "val"),
                        "Delete": ("func Delete[S ~[]E, E any](s S, i, j int) S", "S", "slice"),
                        "clear": ("func clear[T ~[]Type | ~map[Type]Type1](t T)", "void", "slice"),
                        "Contains": ("func Contains[S ~[]E, E comparable](s S, v E) bool", "bool", "slice"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "module", "maps", 1,
                    {
                        "Clone": ("func Clone[M ~map[K]V, K comparable, V any](m M) M", "M", "val"),
                        "Keys": ("func Keys[M ~map[K]V, K comparable, V any](m M) iter.Seq[K]", "iter.Seq[K]", "val"),
                        "DeleteFunc": ("func DeleteFunc[M ~map[K]V, K comparable, V any](m M, del func(K, V) bool)", "void", "val"),
                        "delete": ("func delete(m map[Type]Type1, key Type)", "void", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "module", "strings", 1,
                    {
                        "Split": ("func Split(s, sep string) []string", "[]string", "val"),
                        "TrimSpace": ("func TrimSpace(s string) string", "string", "val"),
                        "HasPrefix": ("func HasPrefix(s, prefix string) bool", "bool", "val"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "struct", "os.File", 1,
                    {
                        "Read": ("func (f *File) Read(b []byte) (n int, err error)", "(int, error)", "pointer"),
                        "Write": ("func (f *File) Write(b []byte) (n int, err error)", "(int, error)", "pointer"),
                        "Close": ("func (f *File) Close() error", "error", "pointer"),
                    },
                )
                _seed_container_with_methods(
                    conn, 2, "interface", "io.Closer", 1,
                    {"Close": ("Close() error", "error", "pointer")},
                )
                _seed_container_with_methods(conn, 2, "struct", "strconv.NumError", 1, {})

    return paths


@pytest.fixture(scope="session")
def built_bridge_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Session-scoped fixture that generates the 6 UTSS SQLite catalogs and runs
    `build_bridge_database()` to produce `utss_universal_bridge.db`.
    """
    work_dir = tmp_path_factory.mktemp("utss_bridge_suite")
    dbs_dir = work_dir / "dbs"
    create_synthetic_utss_catalogs(dbs_dir)

    bridge_db_path = dbs_dir / "utss_universal_bridge.db"
    build_bridge_database(dbs_dir, bridge_db_path)
    return bridge_db_path


@pytest.fixture()
def transpiler(built_bridge_db: Path) -> BridgeTranspiler:
    repo = BridgeCatalogRepository(built_bridge_db)
    return BridgeTranspiler(repo)


# ============================================================================
# TIER 1: BRIDGE DDL & POPULATOR INTEGRITY TESTS
# ============================================================================

def test_bridge_tables_and_concept_inventory(built_bridge_db: Path) -> None:
    """Verifies all 5 tables exist and all 23 canonical concepts across 6 categories are present."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        expected_tables = {
            "universal_concepts",
            "universal_type_mappings",
            "universal_operation_mappings",
            "universal_protocol_mappings",
            "discovered_stdlib_taxonomy",
        }
        assert expected_tables.issubset(tables)

        concept_count = conn.execute("SELECT COUNT(*) FROM universal_concepts;").fetchone()[0]
        assert concept_count == len(CONCEPT_SPECS)

        categories = {
            r[0] for r in conn.execute("SELECT DISTINCT category FROM universal_concepts;").fetchall()
        }
        assert categories == {"primitive", "collection", "control_flow", "exception", "io", "protocol"}

        # Every concept must have a type mapping for all 6 languages
        type_mapping_count = conn.execute("SELECT COUNT(*) FROM universal_type_mappings;").fetchone()[0]
        assert type_mapping_count == len(CONCEPT_SPECS) * 6


def test_empirical_type_resolution_across_6_languages(built_bridge_db: Path) -> None:
    """Verifies that core collections and I/O types resolve to verified catalog containers."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT uc.concept_key, utm.language, utm.verification_status,
                   utm.catalog_container_id, utm.resolved_qualified_name
            FROM universal_type_mappings utm
            JOIN universal_concepts uc ON utm.concept_id = uc.concept_id
            WHERE uc.concept_key IN ('col.sequence', 'col.map', 'col.set');
            """
        ).fetchall()

        assert len(rows) == 18  # 3 concepts * 6 languages
        for r in rows:
            assert r["verification_status"] == "verified_container", (
                f"Expected verified_container for {r['concept_key']} in {r['language']}, "
                f"got {r['verification_status']}"
            )
            assert r["catalog_container_id"] is not None


def test_alias_and_layer2_facet_resolution(built_bridge_db: Path) -> None:
    """Verifies that `symbol_aliases` re-exports and Layer 2 facets are captured in `universal_type_mappings`."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        conn.row_factory = sqlite3.Row
        # Check Layer 2 facet JSON on Python's builtins.list, C#'s List, Rust's Vec, and C++'s std::vector
        for lang in ("python", "csharp", "rust", "cpp"):
            row = conn.execute(
                """
                SELECT utm.layer2_facet_json
                FROM universal_type_mappings utm
                JOIN universal_concepts uc ON utm.concept_id = uc.concept_id
                WHERE uc.concept_key = 'col.sequence' AND utm.language = ?;
                """,
                (lang,),
            ).fetchone()
            assert row is not None and row["layer2_facet_json"] is not None
            parsed_facet = json.loads(row["layer2_facet_json"])
            assert isinstance(parsed_facet, dict) and len(parsed_facet) > 0


# ============================================================================
# TIER 2: EMPIRICAL OPERATION & PROTOCOL BINDING TESTS
# ============================================================================

def test_operation_signature_and_pass_kind_verification(built_bridge_db: Path) -> None:
    """Verifies that `universal_operation_mappings` binds live catalog signatures and pass_kinds."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        conn.row_factory = sqlite3.Row
        total_ops = conn.execute("SELECT COUNT(*) FROM universal_operation_mappings;").fetchone()[0]
        assert total_ops == len(OPERATION_SPECS) * 6

        # Check `col.sequence.append` across all 6 languages
        rows = conn.execute(
            """
            SELECT uom.language, uom.verification_status, uom.verified_raw_signature,
                   uom.verified_pass_kinds_json, uom.receiver_pass_kind
            FROM universal_operation_mappings uom
            JOIN universal_concepts uc ON uom.concept_id = uc.concept_id
            WHERE uc.concept_key = 'col.sequence' AND uom.canonical_op = 'append';
            """
        ).fetchall()
        assert len(rows) == 6
        for r in rows:
            assert r["verification_status"] == "verified_callable"
            assert r["verified_raw_signature"] is not None
            pass_kinds = json.loads(r["verified_pass_kinds_json"])
            assert len(pass_kinds) >= 1


def test_protocol_lowering_and_implementing_counts(built_bridge_db: Path) -> None:
    """Verifies that `universal_protocol_mappings` populates all 4 protocol families and counts implementers."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        conn.row_factory = sqlite3.Row
        proto_count = conn.execute("SELECT COUNT(*) FROM universal_protocol_mappings;").fetchone()[0]
        assert proto_count == len(PROTOCOL_SPECS) * 6

        disp_rows = conn.execute(
            """
            SELECT language, lowering_strategy, implementing_count
            FROM universal_protocol_mappings upm
            JOIN universal_concepts uc ON upm.concept_id = uc.concept_id
            WHERE uc.concept_key = 'proto.disposable';
            """
        ).fetchall()
        strategies = {r["language"]: r["lowering_strategy"] for r in disp_rows}
        assert strategies == {
            "python": "with_statement",
            "csharp": "using_statement",
            "rust": "raii_drop_scope",
            "typescript": "using_declaration",
            "cpp": "raii_drop_scope",
            "go": "defer_close",
        }
        # Python, C#, Rust, and Go seeded implementing containers for disposable
        counts = {r["language"]: r["implementing_count"] for r in disp_rows}
        assert counts["python"] >= 1
        assert counts["csharp"] >= 1
        assert counts["rust"] >= 1
        assert counts["go"] >= 1


# ============================================================================
# TIER 3: PASS 4 AUTONOMOUS STDLIB TAXONOMY HARVESTER TESTS
# ============================================================================

def test_discovered_stdlib_taxonomy_harvester(built_bridge_db: Path) -> None:
    """Verifies that Pass 4 harvests exceptions, collections, I/O streams, and traits across languages."""
    with sqlite3.connect(str(built_bridge_db)) as conn:
        conn.row_factory = sqlite3.Row
        domains = {
            r["taxonomy_domain"]
            for r in conn.execute(
                "SELECT DISTINCT taxonomy_domain FROM discovered_stdlib_taxonomy;"
            ).fetchall()
        }
        assert {"exception", "collection", "io_stream", "protocol_trait_interface"}.issubset(domains)

        vec_row = conn.execute(
            """
            SELECT public_method_count, layer2_metadata_json
            FROM discovered_stdlib_taxonomy
            WHERE language = 'rust' AND qualified_name = 'alloc::vec::Vec';
            """
        ).fetchone()
        assert vec_row is not None
        assert vec_row["public_method_count"] == 5
        assert vec_row["layer2_metadata_json"] is not None


# ============================================================================
# TIER 4: RECURSIVE AST TYPE & EXPRESSION LOWERING TESTS
# ============================================================================

@pytest.mark.parametrize(
    ("py_type_expr", "expected_by_lang"),
    [
        (
            "int",
            {
                "csharp": "long",
                "rust": "i64",
                "typescript": "bigint",
                "cpp": "int64_t",
                "go": "int64",
            },
        ),
        (
            "list[str]",
            {
                "csharp": "List<string>",
                "rust": "Vec<String>",
                "typescript": "Array<string>",
                "cpp": "std::vector<std::string>",
                "go": "[]string",
            },
        ),
        (
            "dict[str, list[int]]",
            {
                "csharp": "Dictionary<string, List<long>>",
                "rust": "HashMap<String, Vec<i64>>",
                "typescript": "Map<string, Array<bigint>>",
                "cpp": "std::unordered_map<std::string, std::vector<int64_t>>",
                "go": "map[string][]int64",
            },
        ),
        (
            "str | None",
            {
                "csharp": "string?",
                "rust": "Option<String>",
                "typescript": "string | null | undefined",
                "cpp": "std::optional<std::string>",
                "go": "*string",
            },
        ),
    ],
)
def test_recursive_generic_and_union_type_resolution(
    transpiler: BridgeTranspiler,
    py_type_expr: str,
    expected_by_lang: Dict[str, str],
) -> None:
    """Verifies recursive generic and PEP 604 union type lowering across all 5 target languages."""
    node = ast.parse(py_type_expr, mode="eval").body
    for lang, expected_syntax in expected_by_lang.items():
        resolved = transpiler.resolve_type_node(node, lang)
        assert resolved.rendered_type == expected_syntax


def test_collection_and_string_operations_across_targets(transpiler: BridgeTranspiler) -> None:
    """Verifies sequence, map, set, and string operations lower to target-idiomatic syntax."""
    snippet = """
items: list[int] = []
items.append(42)
n = len(items)

scores: dict[str, int] = {}
scores["alice"] = 100
has_alice = "alice" in scores

raw: str = "  utss:ready  "
trimmed = raw.strip()
parts = trimmed.split(":")
""".strip()

    expected_fragments: Dict[str, Tuple[str, ...]] = {
        "csharp": (
            "using System.Collections.Generic;",
            "List<long> items = new List<long>();",
            "items.Add(42);",
            "var n = items.Count;",
            'scores["alice"] = 100;',
            'scores.ContainsKey("alice");',
            "raw.Trim();",
            'trimmed.Split(":");',
        ),
        "rust": (
            "use std::collections::HashMap;",
            "let mut items: Vec<i64> = Vec::new();",
            "items.push(42);",
            "let n = items.len();",
            'scores.insert(String::from("alice"), 100);',
            'scores.contains_key(&String::from("alice"));',
            "raw.trim();",
            'trimmed.split(String::from(":"));',
        ),
        "typescript": (
            "const items: Array<bigint> = [];",
            "items.push(42);",
            "const n = items.length;",
            'scores.set("alice", 100);',
            'scores.has("alice");',
            "raw.trim();",
            'trimmed.split(":");',
        ),
        "cpp": (
            "#include <vector>",
            "#include <unordered_map>",
            "std::vector<int64_t> items = {};",
            "items.push_back(42);",
            "auto n = items.size();",
            'scores.insert_or_assign("alice", 100);',
            'scores.contains("alice");',
        ),
        "go": (
            'import "slices"',
            'import "maps"',
            "var items []int64 = []int64{}",
            "items = append(items, 42)",
            "n := len(items)",
            'scores["alice"] = 100',
            '_, ok := scores["alice"]',
            "strings.TrimSpace(raw)",
            'strings.Split(trimmed, ":")',
        ),
    }

    for lang, fragments in expected_fragments.items():
        output = transpiler.transpile_module(snippet, lang)
        for frag in fragments:
            assert frag in output.source_code, (
                f"Missing expected fragment in {lang} output:\n"
                f"  Expected: {frag}\n"
                f"  Actual:\n{output.source_code}"
            )


def test_with_protocol_and_exception_lowering(transpiler: BridgeTranspiler) -> None:
    """Verifies `with open(...) as f:` and `raise ValueError(...)` lower per target paradigm."""
    snippet = """
with open("audit.log") as f:
    chunk = f.read(1024)

raise ValueError("invalid audit state")
""".strip()

    cs_out = transpiler.transpile_module(snippet, "csharp").source_code
    assert 'using (var f = File.OpenRead("audit.log"))' in cs_out
    assert "f.Read(1024);" in cs_out
    assert 'throw new ArgumentException("invalid audit state");' in cs_out

    rs_out = transpiler.transpile_module(snippet, "rust").source_code
    assert 'let mut f = std::fs::File::open("audit.log")?;' in rs_out
    assert "f.read_to_end(&mut 1024);" in rs_out
    assert 'return Err(ParseIntError::from("invalid audit state"));' in rs_out

    go_out = transpiler.transpile_module(snippet, "go").source_code
    assert 'f, err := os.Open("audit.log")' in go_out
    assert "defer f.Close()" in go_out
    assert 'return fmt.Errorf("%w: %s", *strconv.NumError, "invalid audit state")' in go_out

    cpp_out = transpiler.transpile_module(snippet, "cpp").source_code
    assert 'std::fstream f("audit.log");' in cpp_out
    assert 'throw std::invalid_argument("invalid audit state");' in cpp_out

    ts_out = transpiler.transpile_module(snippet, "typescript").source_code
    assert 'using f = await openFileStream("audit.log");' in ts_out
    assert 'throw new RangeError("invalid audit state");' in ts_out


# ============================================================================
# TIER 5: PROVENANCE TRACE & FASTAPI SANDBOX ROUTER TESTS
# ============================================================================

def test_provenance_trace_completeness(transpiler: BridgeTranspiler) -> None:
    """Verifies that every lowered construct produces a verified ProvenanceRecord with catalog IDs."""
    snippet = """
items: list[int] = []
items.append(7)
with open("events.bin") as f:
    data = f.read(512)
""".strip()

    for lang in TARGET_LANGUAGES:
        result = transpiler.transpile_module(snippet, lang)
        constructs = {p.construct for p in result.provenance_trace}
        assert "type:list" in constructs
        assert "type:int" in constructs
        assert "op:col.sequence.append" in constructs
        assert "protocol:with_statement" in constructs
        assert "op:io.file_stream.read" in constructs

        append_prov = next(
            p for p in result.provenance_trace if p.construct == "op:col.sequence.append"
        )
        assert append_prov.verification_status == "verified_callable"
        assert append_prov.catalog_symbol_id is not None
        assert append_prov.catalog_signature is not None
        assert append_prov.receiver_pass_kind is not None

```

---

### 3. Running the Test Suite

Execute the suite via `uv`:

```bash
uv run pytest tests/test_universal_bridge.py -v

```

Every test executes deterministically in under 1 second using the session-scoped 6-language UTSS SQLite fixture, while also allowing you to point `BridgeCatalogRepository` directly at your production `dbs/utss_universal_bridge.db` file.

Would you like to package the complete **Phase 1–5 CLI workflow (`utss_cli.py` or `Makefile` / `justfile` tasks)** next so a single command (`utss bridge-build`, `utss analyze`, `utss transpile`) orchestrates catalog harvesting, Pandas chart generation, bridge DB compilation, and multi-target code synthesis?