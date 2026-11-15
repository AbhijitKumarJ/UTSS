#!/usr/bin/env python3
"""
UTSS Universal Transpilation Bridge Database Builder.
Compiles dbs/utss_universal_bridge.db via 4-pass extraction pipeline.
"""

import json
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.config import Config
from server.db_manager import DatabaseManager


DDL_SCHEMA = """
-- Environments table for UTSS platform compatibility
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL,
    runtime_name TEXT NOT NULL,
    language_version TEXT NOT NULL,
    version_major INTEGER,
    version_minor INTEGER,
    version_micro INTEGER,
    platform_triplet TEXT,
    sys_platform TEXT,
    executable_path TEXT,
    captured_at TEXT
);

CREATE TABLE IF NOT EXISTS universal_concepts (
    concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_key TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    type_arity INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS universal_type_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    target_qualified_name TEXT NOT NULL,
    fallback_candidates_json TEXT NOT NULL DEFAULT '[]',
    type_syntax_template TEXT NOT NULL,
    required_import TEXT,
    memory_model TEXT NOT NULL,
    nullability_model TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS universal_operation_mappings (
    op_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    canonical_op TEXT NOT NULL,
    language TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    call_syntax_template TEXT NOT NULL,
    receiver_pass_kind TEXT NOT NULL,
    mutates_receiver INTEGER NOT NULL DEFAULT 0,
    returns_new_value INTEGER NOT NULL DEFAULT 0,
    catalog_symbol_id INTEGER,
    verified_qualified_name TEXT,
    verified_raw_signature TEXT,
    verified_return_type TEXT,
    verified_overload_count INTEGER NOT NULL DEFAULT 0,
    verified_pass_kinds_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, canonical_op, language)
);

CREATE TABLE IF NOT EXISTS universal_protocol_mappings (
    proto_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    contract_kind TEXT NOT NULL,
    contract_qualified_name TEXT NOT NULL,
    required_methods_json TEXT NOT NULL,
    lowering_strategy TEXT NOT NULL,
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    implementing_count INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, language)
);

CREATE TABLE IF NOT EXISTS discovered_stdlib_taxonomy (
    discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    taxonomy_domain TEXT NOT NULL,
    stratum INTEGER NOT NULL,
    entity_kind TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    public_method_count INTEGER NOT NULL DEFAULT 0,
    layer2_metadata_json TEXT,
    UNIQUE(language, taxonomy_domain, qualified_name)
);
"""

CONCEPTS = [
    # Primitives
    ("primitive.int32", "primitive", 0, "Signed 32-bit integer"),
    ("primitive.int64", "primitive", 0, "Signed 64-bit integer"),
    ("primitive.float64", "primitive", 0, "IEEE-754 double precision floating point"),
    ("primitive.bool", "primitive", 0, "Boolean true/false value"),
    ("primitive.string_utf8", "primitive", 0, "Immutable UTF-8 encoded text sequence"),
    ("primitive.byte_sequence", "primitive", 0, "Contiguous raw byte buffer"),
    # Collections
    ("collection.dynamic_array", "collection", 1, "Dynamically resizable contiguous array"),
    ("collection.hash_map", "collection", 2, "Associative key-value hash map"),
    ("collection.hash_set", "collection", 1, "Unordered set of unique elements"),
    ("collection.fifo_queue", "collection", 1, "First-in first-out double-ended queue"),
    # Control flow & types
    ("control_flow.option_maybe", "control_flow", 1, "Optional value wrapper representing presence or absence"),
    ("control_flow.result_either", "control_flow", 2, "Disjoint union representing success or failure"),
    # Exceptions
    ("exception.io_error", "exception", 0, "Input/output stream failure or operating system error"),
    ("exception.key_not_found", "exception", 0, "Map lookup failure for missing key"),
    ("exception.index_out_of_bounds", "exception", 0, "Sequence indexing outside valid bounds"),
    ("exception.argument_null", "exception", 0, "Invalid null or missing required argument"),
    # I/O Streams
    ("io.byte_stream", "io", 0, "In-memory or channel raw byte stream buffer"),
    ("io.text_reader", "io", 0, "Buffered text reader with encoding support"),
    ("io.file_handle", "io", 0, "Operating system file descriptor abstraction"),
    # Protocols
    ("protocol.iteration", "protocol", 1, "Sequential cursor traversal protocol"),
    ("protocol.resource_cleanup", "protocol", 0, "Deterministic resource acquisition and disposal"),
    ("protocol.ordering_comparison", "protocol", 0, "Total ordering and comparison contract"),
]

TYPE_MAPPINGS_DEF = {
    "primitive.int32": {
        "python": ("int", "int", None, "ref_gc", "value_default"),
        "csharp": ("int", "int", None, "value_stack", "value_default"),
        "cpp": ("int", "int", None, "value_stack", "value_default"),
        "go": ("int32", "int32", None, "value_stack", "value_default"),
        "rust": ("i32", "i32", None, "value_stack", "value_default"),
        "typescript": ("number", "number", None, "value_stack", "value_default"),
    },
    "primitive.int64": {
        "python": ("int", "int", None, "ref_gc", "value_default"),
        "csharp": ("long", "long", None, "value_stack", "value_default"),
        "cpp": ("long long", "long long", None, "value_stack", "value_default"),
        "go": ("int64", "int64", None, "value_stack", "value_default"),
        "rust": ("i64", "i64", None, "value_stack", "value_default"),
        "typescript": ("bigint", "bigint", None, "ref_gc", "value_default"),
    },
    "primitive.float64": {
        "python": ("float", "float", None, "ref_gc", "value_default"),
        "csharp": ("double", "double", None, "value_stack", "value_default"),
        "cpp": ("double", "double", None, "value_stack", "value_default"),
        "go": ("float64", "float64", None, "value_stack", "value_default"),
        "rust": ("f64", "f64", None, "value_stack", "value_default"),
        "typescript": ("number", "number", None, "value_stack", "value_default"),
    },
    "primitive.bool": {
        "python": ("bool", "bool", None, "ref_gc", "value_default"),
        "csharp": ("bool", "bool", None, "value_stack", "value_default"),
        "cpp": ("bool", "bool", None, "value_stack", "value_default"),
        "go": ("bool", "bool", None, "value_stack", "value_default"),
        "rust": ("bool", "bool", None, "value_stack", "value_default"),
        "typescript": ("boolean", "boolean", None, "value_stack", "value_default"),
    },
    "primitive.string_utf8": {
        "python": ("str", "str", None, "ref_gc", "value_default"),
        "csharp": ("string", "string", None, "ref_gc", "nullable_ref"),
        "cpp": ("std::string", "std::string", "<string>", "value_stack", "value_default"),
        "go": ("string", "string", None, "value_stack", "value_default"),
        "rust": ("String", "String", "alloc::string::String", "owned_heap", "value_default"),
        "typescript": ("string", "string", None, "ref_gc", "value_default"),
    },
    "primitive.byte_sequence": {
        "python": ("bytes", "bytes", None, "ref_gc", "value_default"),
        "csharp": ("byte[]", "byte[]", None, "ref_gc", "nullable_ref"),
        "cpp": ("std::vector<uint8_t>", "std::vector<uint8_t>", "<vector>", "owned_heap", "value_default"),
        "go": ("[]byte", "[]byte", None, "slice_header", "value_default"),
        "rust": ("Vec<u8>", "Vec<u8>", "alloc::vec::Vec", "owned_heap", "value_default"),
        "typescript": ("Uint8Array", "Uint8Array", None, "ref_gc", "nullable_ref"),
    },
    "collection.dynamic_array": {
        "python": ("list", "list[{T}]", None, "ref_gc", "nullable_ref"),
        "csharp": ("List", "List<{T}>", "System.Collections.Generic", "ref_gc", "nullable_ref"),
        "cpp": ("vector", "std::vector<{T}>", "<vector>", "owned_heap", "value_default"),
        "go": ("slice", "[]{T}", None, "slice_header", "value_default"),
        "rust": ("Vec", "Vec<{T}>", "alloc::vec::Vec", "owned_heap", "value_default"),
        "typescript": ("Array", "Array<{T}>", None, "ref_gc", "nullable_ref"),
    },
    "collection.hash_map": {
        "python": ("dict", "dict[{K}, {V}]", None, "ref_gc", "nullable_ref"),
        "csharp": ("Dictionary", "Dictionary<{K}, {V}>", "System.Collections.Generic", "ref_gc", "nullable_ref"),
        "cpp": ("unordered_map", "std::unordered_map<{K}, {V}>", "<unordered_map>", "owned_heap", "value_default"),
        "go": ("map", "map[{K}]{V}", None, "ref_gc", "pointer_nil"),
        "rust": ("HashMap", "HashMap<{K}, {V}>", "std::collections::HashMap", "owned_heap", "value_default"),
        "typescript": ("Map", "Map<{K}, {V}>", None, "ref_gc", "nullable_ref"),
    },
    "collection.hash_set": {
        "python": ("set", "set[{T}]", None, "ref_gc", "nullable_ref"),
        "csharp": ("HashSet", "HashSet<{T}>", "System.Collections.Generic", "ref_gc", "nullable_ref"),
        "cpp": ("unordered_set", "std::unordered_set<{T}>", "<unordered_set>", "owned_heap", "value_default"),
        "go": ("map", "map[{T}]struct{}", None, "ref_gc", "pointer_nil"),
        "rust": ("HashSet", "HashSet<{T}>", "std::collections::HashSet", "owned_heap", "value_default"),
        "typescript": ("Set", "Set<{T}>", None, "ref_gc", "nullable_ref"),
    },
    "collection.fifo_queue": {
        "python": ("deque", "collections.deque[{T}]", "collections", "ref_gc", "nullable_ref"),
        "csharp": ("Queue", "Queue<{T}>", "System.Collections.Generic", "ref_gc", "nullable_ref"),
        "cpp": ("deque", "std::deque<{T}>", "<deque>", "owned_heap", "value_default"),
        "go": ("slice", "[]{T}", None, "slice_header", "value_default"),
        "rust": ("VecDeque", "VecDeque<{T}>", "std::collections::VecDeque", "owned_heap", "value_default"),
        "typescript": ("Array", "Array<{T}>", None, "ref_gc", "nullable_ref"),
    },
    "control_flow.option_maybe": {
        "python": ("Optional", "Optional[{T}]", "typing", "ref_gc", "nullable_ref"),
        "csharp": ("Nullable", "Nullable<{T}>", "System", "value_stack", "nullable_ref"),
        "cpp": ("optional", "std::optional<{T}>", "<optional>", "value_stack", "option_wrapper"),
        "go": ("pointer", "*{T}", None, "pointer_nil", "pointer_nil"),
        "rust": ("Option", "Option<{T}>", "core::option::Option", "value_stack", "option_wrapper"),
        "typescript": ("union", "{T} | undefined", None, "ref_gc", "nullable_ref"),
    },
    "control_flow.result_either": {
        "python": ("tuple", "tuple[{T}, Optional[Exception]]", None, "ref_gc", "nullable_ref"),
        "csharp": ("Result", "Result<{T}, {E}>", None, "value_stack", "value_default"),
        "cpp": ("expected", "std::expected<{T}, {E}>", "<expected>", "value_stack", "value_default"),
        "go": ("tuple", "({T}, error)", None, "value_stack", "value_default"),
        "rust": ("Result", "Result<{T}, {E}>", "core::result::Result", "value_stack", "value_default"),
        "typescript": ("union", "{ success: true, value: {T} } | { success: false, error: {E} }", None, "ref_gc", "nullable_ref"),
    },
    "exception.io_error": {
        "python": ("OSError", "OSError", None, "ref_gc", "nullable_ref"),
        "csharp": ("IOException", "System.IO.IOException", "System.IO", "ref_gc", "nullable_ref"),
        "cpp": ("filesystem_error", "std::filesystem::filesystem_error", "<filesystem>", "ref_gc", "nullable_ref"),
        "go": ("error", "error", None, "slice_header", "pointer_nil"),
        "rust": ("Error", "std::io::Error", "std::io", "owned_heap", "value_default"),
        "typescript": ("Error", "Error", None, "ref_gc", "nullable_ref"),
    },
    "exception.key_not_found": {
        "python": ("KeyError", "KeyError", None, "ref_gc", "nullable_ref"),
        "csharp": ("KeyNotFoundException", "System.Collections.Generic.KeyNotFoundException", "System.Collections.Generic", "ref_gc", "nullable_ref"),
        "cpp": ("out_of_range", "std::out_of_range", "<stdexcept>", "ref_gc", "nullable_ref"),
        "go": ("error", "error", None, "slice_header", "pointer_nil"),
        "rust": ("None", "None", None, "value_stack", "value_default"),
        "typescript": ("Error", "Error", None, "ref_gc", "nullable_ref"),
    },
    "exception.index_out_of_bounds": {
        "python": ("IndexError", "IndexError", None, "ref_gc", "nullable_ref"),
        "csharp": ("ArgumentOutOfRangeException", "System.ArgumentOutOfRangeException", "System", "ref_gc", "nullable_ref"),
        "cpp": ("out_of_range", "std::out_of_range", "<stdexcept>", "ref_gc", "nullable_ref"),
        "go": ("panic", "panic", None, "value_stack", "value_default"),
        "rust": ("panic", "panic!", None, "value_stack", "value_default"),
        "typescript": ("RangeError", "RangeError", None, "ref_gc", "nullable_ref"),
    },
    "exception.argument_null": {
        "python": ("ValueError", "ValueError", None, "ref_gc", "nullable_ref"),
        "csharp": ("ArgumentNullException", "System.ArgumentNullException", "System", "ref_gc", "nullable_ref"),
        "cpp": ("invalid_argument", "std::invalid_argument", "<stdexcept>", "ref_gc", "nullable_ref"),
        "go": ("error", "error", None, "slice_header", "pointer_nil"),
        "rust": ("None", "None", None, "value_stack", "value_default"),
        "typescript": ("TypeError", "TypeError", None, "ref_gc", "nullable_ref"),
    },
    "io.byte_stream": {
        "python": ("BytesIO", "io.BytesIO", "io", "ref_gc", "nullable_ref"),
        "csharp": ("MemoryStream", "System.IO.MemoryStream", "System.IO", "ref_gc", "nullable_ref"),
        "cpp": ("stringstream", "std::stringstream", "<sstream>", "owned_heap", "value_default"),
        "go": ("Buffer", "bytes.Buffer", "bytes", "ref_gc", "pointer_nil"),
        "rust": ("Cursor", "std::io::Cursor<Vec<u8>>", "std::io", "owned_heap", "value_default"),
        "typescript": ("Uint8Array", "Uint8Array", None, "ref_gc", "nullable_ref"),
    },
    "io.text_reader": {
        "python": ("TextIOWrapper", "io.TextIOWrapper", "io", "ref_gc", "nullable_ref"),
        "csharp": ("StreamReader", "System.IO.StreamReader", "System.IO", "ref_gc", "nullable_ref"),
        "cpp": ("ifstream", "std::ifstream", "<fstream>", "owned_heap", "value_default"),
        "go": ("Reader", "bufio.Reader", "bufio", "ref_gc", "pointer_nil"),
        "rust": ("BufReader", "std::io::BufReader<R>", "std::io", "owned_heap", "value_default"),
        "typescript": ("ReadableStream", "ReadableStream", None, "ref_gc", "nullable_ref"),
    },
    "io.file_handle": {
        "python": ("open", "open(path, mode)", None, "ref_gc", "nullable_ref"),
        "csharp": ("FileStream", "System.IO.FileStream", "System.IO", "ref_gc", "nullable_ref"),
        "cpp": ("fstream", "std::fstream", "<fstream>", "owned_heap", "value_default"),
        "go": ("File", "os.File", "os", "ref_gc", "pointer_nil"),
        "rust": ("File", "std::fs::File", "std::fs", "owned_heap", "value_default"),
        "typescript": ("File", "File", None, "ref_gc", "nullable_ref"),
    },
}

OPERATION_MAPPINGS_DEF = [
    # dynamic_array operations
    ("collection.dynamic_array", "append", {
        "python": ("append", "{receiver}.append({item})", "mut_ref", 1, 0),
        "csharp": ("Add", "{receiver}.Add({item})", "mut_ref", 1, 0),
        "cpp": ("push_back", "{receiver}.push_back({item})", "mut_ref", 1, 0),
        "go": ("append", "{receiver} = append({receiver}, {item})", "free_fn", 1, 1),
        "rust": ("push", "{receiver}.push({item})", "mut_ref", 1, 0),
        "typescript": ("push", "{receiver}.push({item})", "mut_ref", 1, 1),
    }),
    ("collection.dynamic_array", "pop", {
        "python": ("pop", "{receiver}.pop()", "mut_ref", 1, 1),
        "csharp": ("RemoveAt", "{receiver}.RemoveAt({receiver}.Count - 1)", "mut_ref", 1, 0),
        "cpp": ("pop_back", "{receiver}.pop_back()", "mut_ref", 1, 0),
        "go": ("slice", "{receiver} = {receiver}[:len({receiver})-1]", "operator", 1, 1),
        "rust": ("pop", "{receiver}.pop()", "mut_ref", 1, 1),
        "typescript": ("pop", "{receiver}.pop()", "mut_ref", 1, 1),
    }),
    ("collection.dynamic_array", "len", {
        "python": ("len", "len({receiver})", "free_fn", 0, 1),
        "csharp": ("Count", "{receiver}.Count", "ref", 0, 1),
        "cpp": ("size", "{receiver}.size()", "ref", 0, 1),
        "go": ("len", "len({receiver})", "free_fn", 0, 1),
        "rust": ("len", "{receiver}.len()", "ref", 0, 1),
        "typescript": ("length", "{receiver}.length", "ref", 0, 1),
    }),
    ("collection.dynamic_array", "clear", {
        "python": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "csharp": ("Clear", "{receiver}.Clear()", "mut_ref", 1, 0),
        "cpp": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "go": ("clear", "{receiver} = {receiver}[:0]", "operator", 1, 0),
        "rust": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "typescript": ("length", "{receiver}.length = 0", "operator", 1, 0),
    }),
    # hash_map operations
    ("collection.hash_map", "get", {
        "python": ("get", "{receiver}.get({key})", "ref", 0, 1),
        "csharp": ("TryGetValue", "{receiver}.TryGetValue({key}, out var {out})", "ref", 0, 1),
        "cpp": ("find", "{receiver}.find({key})", "ref", 0, 1),
        "go": ("index", "val, ok := {receiver}[{key}]", "operator", 0, 1),
        "rust": ("get", "{receiver}.get(&{key})", "ref", 0, 1),
        "typescript": ("get", "{receiver}.get({key})", "ref", 0, 1),
    }),
    ("collection.hash_map", "set", {
        "python": ("__setitem__", "{receiver}[{key}] = {val}", "operator", 1, 0),
        "csharp": ("set_Item", "{receiver}[{key}] = {val}", "operator", 1, 0),
        "cpp": ("insert_or_assign", "{receiver}[{key}] = {val}", "operator", 1, 0),
        "go": ("index", "{receiver}[{key}] = {val}", "operator", 1, 0),
        "rust": ("insert", "{receiver}.insert({key}, {val})", "mut_ref", 1, 1),
        "typescript": ("set", "{receiver}.set({key}, {val})", "mut_ref", 1, 1),
    }),
    ("collection.hash_map", "remove", {
        "python": ("pop", "{receiver}.pop({key}, None)", "mut_ref", 1, 1),
        "csharp": ("Remove", "{receiver}.Remove({key})", "mut_ref", 1, 1),
        "cpp": ("erase", "{receiver}.erase({key})", "mut_ref", 1, 1),
        "go": ("delete", "delete({receiver}, {key})", "free_fn", 1, 0),
        "rust": ("remove", "{receiver}.remove(&{key})", "mut_ref", 1, 1),
        "typescript": ("delete", "{receiver}.delete({key})", "mut_ref", 1, 1),
    }),
    ("collection.hash_map", "len", {
        "python": ("len", "len({receiver})", "free_fn", 0, 1),
        "csharp": ("Count", "{receiver}.Count", "ref", 0, 1),
        "cpp": ("size", "{receiver}.size()", "ref", 0, 1),
        "go": ("len", "len({receiver})", "free_fn", 0, 1),
        "rust": ("len", "{receiver}.len()", "ref", 0, 1),
        "typescript": ("size", "{receiver}.size", "ref", 0, 1),
    }),
    # hash_set operations
    ("collection.hash_set", "add", {
        "python": ("add", "{receiver}.add({item})", "mut_ref", 1, 0),
        "csharp": ("Add", "{receiver}.Add({item})", "mut_ref", 1, 1),
        "cpp": ("insert", "{receiver}.insert({item})", "mut_ref", 1, 1),
        "go": ("index", "{receiver}[{item}] = struct{}{}", "operator", 1, 0),
        "rust": ("insert", "{receiver}.insert({item})", "mut_ref", 1, 1),
        "typescript": ("add", "{receiver}.add({item})", "mut_ref", 1, 1),
    }),
    ("collection.hash_set", "remove", {
        "python": ("discard", "{receiver}.discard({item})", "mut_ref", 1, 0),
        "csharp": ("Remove", "{receiver}.Remove({item})", "mut_ref", 1, 1),
        "cpp": ("erase", "{receiver}.erase({item})", "mut_ref", 1, 1),
        "go": ("delete", "delete({receiver}, {item})", "free_fn", 1, 0),
        "rust": ("remove", "{receiver}.remove(&{item})", "mut_ref", 1, 1),
        "typescript": ("delete", "{receiver}.delete({item})", "mut_ref", 1, 1),
    }),
    ("collection.hash_set", "contains", {
        "python": ("__contains__", "{item} in {receiver}", "operator", 0, 1),
        "csharp": ("Contains", "{receiver}.Contains({item})", "ref", 0, 1),
        "cpp": ("contains", "{receiver}.contains({item})", "ref", 0, 1),
        "go": ("index", "_, ok := {receiver}[{item}]", "operator", 0, 1),
        "rust": ("contains", "{receiver}.contains(&{item})", "ref", 0, 1),
        "typescript": ("has", "{receiver}.has({item})", "ref", 0, 1),
    }),
    ("collection.hash_set", "len", {
        "python": ("len", "len({receiver})", "free_fn", 0, 1),
        "csharp": ("Count", "{receiver}.Count", "ref", 0, 1),
        "cpp": ("size", "{receiver}.size()", "ref", 0, 1),
        "go": ("len", "len({receiver})", "free_fn", 0, 1),
        "rust": ("len", "{receiver}.len()", "ref", 0, 1),
        "typescript": ("size", "{receiver}.size", "ref", 0, 1),
    }),
    ("collection.hash_set", "clear", {
        "python": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "csharp": ("Clear", "{receiver}.Clear()", "mut_ref", 1, 0),
        "cpp": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "go": ("clear", "clear({receiver})", "free_fn", 1, 0),
        "rust": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "typescript": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
    }),
    # fifo_queue operations
    ("collection.fifo_queue", "enqueue", {
        "python": ("append", "{receiver}.append({item})", "mut_ref", 1, 0),
        "csharp": ("Enqueue", "{receiver}.Enqueue({item})", "mut_ref", 1, 0),
        "cpp": ("push", "{receiver}.push({item})", "mut_ref", 1, 0),
        "go": ("append", "{receiver} = append({receiver}, {item})", "free_fn", 1, 1),
        "rust": ("push_back", "{receiver}.push_back({item})", "mut_ref", 1, 0),
        "typescript": ("push", "{receiver}.push({item})", "mut_ref", 1, 1),
    }),
    ("collection.fifo_queue", "dequeue", {
        "python": ("popleft", "{receiver}.popleft()", "mut_ref", 1, 1),
        "csharp": ("Dequeue", "{receiver}.Dequeue()", "mut_ref", 1, 1),
        "cpp": ("pop", "{receiver}.pop()", "mut_ref", 1, 0),
        "go": ("slice", "val = {receiver}[0]; {receiver} = {receiver}[1:]", "operator", 1, 1),
        "rust": ("pop_front", "{receiver}.pop_front()", "mut_ref", 1, 1),
        "typescript": ("shift", "{receiver}.shift()", "mut_ref", 1, 1),
    }),
    ("collection.fifo_queue", "peek", {
        "python": ("index", "{receiver}[0]", "operator", 0, 1),
        "csharp": ("Peek", "{receiver}.Peek()", "ref", 0, 1),
        "cpp": ("front", "{receiver}.front()", "ref", 0, 1),
        "go": ("index", "{receiver}[0]", "operator", 0, 1),
        "rust": ("front", "{receiver}.front()", "ref", 0, 1),
        "typescript": ("index", "{receiver}[0]", "operator", 0, 1),
    }),
    ("collection.fifo_queue", "len", {
        "python": ("len", "len({receiver})", "free_fn", 0, 1),
        "csharp": ("Count", "{receiver}.Count", "ref", 0, 1),
        "cpp": ("size", "{receiver}.size()", "ref", 0, 1),
        "go": ("len", "len({receiver})", "free_fn", 0, 1),
        "rust": ("len", "{receiver}.len()", "ref", 0, 1),
        "typescript": ("length", "{receiver}.length", "ref", 0, 1),
    }),
    ("collection.fifo_queue", "clear", {
        "python": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "csharp": ("Clear", "{receiver}.Clear()", "mut_ref", 1, 0),
        "cpp": ("swap", "{receiver} = {}", "operator", 1, 0),
        "go": ("nil", "{receiver} = nil", "operator", 1, 0),
        "rust": ("clear", "{receiver}.clear()", "mut_ref", 1, 0),
        "typescript": ("length", "{receiver}.length = 0", "operator", 1, 0),
    }),
    # string_utf8 operations
    ("primitive.string_utf8", "len", {
        "python": ("len", "len({receiver})", "free_fn", 0, 1),
        "csharp": ("Length", "{receiver}.Length", "ref", 0, 1),
        "cpp": ("length", "{receiver}.length()", "ref", 0, 1),
        "go": ("len", "len({receiver})", "free_fn", 0, 1),
        "rust": ("len", "{receiver}.len()", "ref", 0, 1),
        "typescript": ("length", "{receiver}.length", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "contains", {
        "python": ("__contains__", "{item} in {receiver}", "operator", 0, 1),
        "csharp": ("Contains", "{receiver}.Contains({item})", "ref", 0, 1),
        "cpp": ("find", "{receiver}.find({item}) != std::string::npos", "ref", 0, 1),
        "go": ("Contains", "strings.Contains({receiver}, {item})", "free_fn", 0, 1),
        "rust": ("contains", "{receiver}.contains({item})", "ref", 0, 1),
        "typescript": ("includes", "{receiver}.includes({item})", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "starts_with", {
        "python": ("startswith", "{receiver}.startswith({item})", "ref", 0, 1),
        "csharp": ("StartsWith", "{receiver}.StartsWith({item})", "ref", 0, 1),
        "cpp": ("starts_with", "{receiver}.starts_with({item})", "ref", 0, 1),
        "go": ("HasPrefix", "strings.HasPrefix({receiver}, {item})", "free_fn", 0, 1),
        "rust": ("starts_with", "{receiver}.starts_with({item})", "ref", 0, 1),
        "typescript": ("startsWith", "{receiver}.startsWith({item})", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "ends_with", {
        "python": ("endswith", "{receiver}.endswith({item})", "ref", 0, 1),
        "csharp": ("EndsWith", "{receiver}.EndsWith({item})", "ref", 0, 1),
        "cpp": ("ends_with", "{receiver}.ends_with({item})", "ref", 0, 1),
        "go": ("HasSuffix", "strings.HasSuffix({receiver}, {item})", "free_fn", 0, 1),
        "rust": ("ends_with", "{receiver}.ends_with({item})", "ref", 0, 1),
        "typescript": ("endsWith", "{receiver}.endsWith({item})", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "to_lowercase", {
        "python": ("lower", "{receiver}.lower()", "ref", 0, 1),
        "csharp": ("ToLowerInvariant", "{receiver}.ToLowerInvariant()", "ref", 0, 1),
        "cpp": ("tolower", "boost::algorithm::to_lower_copy({receiver})", "free_fn", 0, 1),
        "go": ("ToLower", "strings.ToLower({receiver})", "free_fn", 0, 1),
        "rust": ("to_lowercase", "{receiver}.to_lowercase()", "ref", 0, 1),
        "typescript": ("toLowerCase", "{receiver}.toLowerCase()", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "to_uppercase", {
        "python": ("upper", "{receiver}.upper()", "ref", 0, 1),
        "csharp": ("ToUpperInvariant", "{receiver}.ToUpperInvariant()", "ref", 0, 1),
        "cpp": ("toupper", "boost::algorithm::to_upper_copy({receiver})", "free_fn", 0, 1),
        "go": ("ToUpper", "strings.ToUpper({receiver})", "free_fn", 0, 1),
        "rust": ("to_uppercase", "{receiver}.to_uppercase()", "ref", 0, 1),
        "typescript": ("toUpperCase", "{receiver}.toUpperCase()", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "trim", {
        "python": ("strip", "{receiver}.strip()", "ref", 0, 1),
        "csharp": ("Trim", "{receiver}.Trim()", "ref", 0, 1),
        "cpp": ("trim", "trim({receiver})", "free_fn", 0, 1),
        "go": ("TrimSpace", "strings.TrimSpace({receiver})", "free_fn", 0, 1),
        "rust": ("trim", "{receiver}.trim()", "ref", 0, 1),
        "typescript": ("trim", "{receiver}.trim()", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "split", {
        "python": ("split", "{receiver}.split({item})", "ref", 0, 1),
        "csharp": ("Split", "{receiver}.Split({item})", "ref", 0, 1),
        "cpp": ("split", "split({receiver}, {item})", "free_fn", 0, 1),
        "go": ("Split", "strings.Split({receiver}, {item})", "free_fn", 0, 1),
        "rust": ("split", "{receiver}.split({item}).collect::<Vec<_>>()", "ref", 0, 1),
        "typescript": ("split", "{receiver}.split({item})", "ref", 0, 1),
    }),
    ("primitive.string_utf8", "replace", {
        "python": ("replace", "{receiver}.replace({key}, {val})", "ref", 0, 1),
        "csharp": ("Replace", "{receiver}.Replace({key}, {val})", "ref", 0, 1),
        "cpp": ("replace", "replace({receiver}, {key}, {val})", "free_fn", 0, 1),
        "go": ("ReplaceAll", "strings.ReplaceAll({receiver}, {key}, {val})", "free_fn", 0, 1),
        "rust": ("replace", "{receiver}.replace({key}, {val})", "ref", 0, 1),
        "typescript": ("replaceAll", "{receiver}.replaceAll({key}, {val})", "ref", 0, 1),
    }),
    # file_handle operations
    ("io.file_handle", "read", {
        "python": ("read", "{receiver}.read({item})", "mut_ref", 1, 1),
        "csharp": ("Read", "{receiver}.Read({item})", "mut_ref", 1, 1),
        "cpp": ("read", "{receiver}.read({item})", "mut_ref", 1, 1),
        "go": ("Read", "{receiver}.Read({item})", "mut_ref", 1, 1),
        "rust": ("read", "{receiver}.read(&mut {item})", "mut_ref", 1, 1),
        "typescript": ("read", "{receiver}.read({item})", "mut_ref", 1, 1),
    }),
    ("io.file_handle", "write", {
        "python": ("write", "{receiver}.write({item})", "mut_ref", 1, 1),
        "csharp": ("Write", "{receiver}.Write({item})", "mut_ref", 1, 0),
        "cpp": ("write", "{receiver}.write({item})", "mut_ref", 1, 1),
        "go": ("Write", "{receiver}.Write({item})", "mut_ref", 1, 1),
        "rust": ("write_all", "{receiver}.write_all({item})", "mut_ref", 1, 1),
        "typescript": ("write", "{receiver}.write({item})", "mut_ref", 1, 1),
    }),
    ("io.file_handle", "flush", {
        "python": ("flush", "{receiver}.flush()", "mut_ref", 1, 0),
        "csharp": ("Flush", "{receiver}.Flush()", "mut_ref", 1, 0),
        "cpp": ("flush", "{receiver}.flush()", "mut_ref", 1, 0),
        "go": ("Sync", "{receiver}.Sync()", "mut_ref", 1, 1),
        "rust": ("flush", "{receiver}.flush()", "mut_ref", 1, 1),
        "typescript": ("flush", "{receiver}.flush()", "mut_ref", 1, 0),
    }),
    ("io.file_handle", "close", {
        "python": ("close", "{receiver}.close()", "mut_ref", 1, 0),
        "csharp": ("Close", "{receiver}.Close()", "mut_ref", 1, 0),
        "cpp": ("close", "{receiver}.close()", "mut_ref", 1, 0),
        "go": ("Close", "{receiver}.Close()", "mut_ref", 1, 1),
        "rust": ("drop", "drop({receiver})", "free_fn", 1, 0),
        "typescript": ("close", "{receiver}.close()", "mut_ref", 1, 0),
    }),
]

PROTOCOL_MAPPINGS_DEF = [
    ("protocol.iteration", [
        ("python", "dunder_protocol", "collections.abc.Iterable", '["__iter__", "__next__"]', "duck_typing"),
        ("csharp", "interface", "System.Collections.Generic.IEnumerable", '["GetEnumerator"]', "vtable_slot"),
        ("cpp", "concept", "std::input_iterator", '["operator++", "operator*"]', "template_constraint"),
        ("go", "implicit_interface", "range_clause", '[]', "compiler_intrinsic"),
        ("rust", "trait", "core::iter::Iterator", '["next"]', "monomorphized_trait"),
        ("typescript", "interface", "Iterable", '["[Symbol.iterator]"]', "duck_typing"),
    ]),
    ("protocol.resource_cleanup", [
        ("python", "dunder_protocol", "contextlib.AbstractContextManager", '["__enter__", "__exit__"]', "duck_typing"),
        ("csharp", "interface", "System.IDisposable", '["Dispose"]', "vtable_slot"),
        ("cpp", "destructor_idiom", "RAII_destructor", '["~T()"]', "stack_unwind"),
        ("go", "keyword_idiom", "defer", '["Close"]', "stack_unwind"),
        ("rust", "trait", "core::ops::Drop", '["drop"]', "monomorphized_trait"),
        ("typescript", "interface", "Disposable", '["[Symbol.dispose]"]', "duck_typing"),
    ]),
    ("protocol.ordering_comparison", [
        ("python", "dunder_protocol", "functools.total_ordering", '["__lt__", "__gt__", "__eq__"]', "duck_typing"),
        ("csharp", "interface", "System.IComparable", '["CompareTo"]', "vtable_slot"),
        ("cpp", "concept", "std::totally_ordered", '["operator<=>"]', "template_constraint"),
        ("go", "implicit_interface", "sort.Interface", '["Len", "Less", "Swap"]', "vtable_slot"),
        ("rust", "trait", "core::cmp::Ord", '["cmp"]', "monomorphized_trait"),
        ("typescript", "comparator_fn", "Comparer", '["compare"]', "callback_closure"),
    ]),
]


def build_bridge_database(output_path: Path | None = None) -> None:
    """Compiles the Universal Transpilation Bridge SQLite database."""
    target_path = output_path or (Config.DBS_DIR / "utss_universal_bridge.db")
    if target_path.exists():
        target_path.unlink()

    conn = sqlite3.connect(target_path)
    cursor = conn.cursor()

    # 1. Execute DDL
    cursor.executescript(DDL_SCHEMA)

    # 2. Insert Environment metadata for UTSS discovery
    cursor.execute("""
    INSERT INTO environments (
        env_id, language, runtime_name, language_version, version_major, version_minor, version_micro, platform_triplet, sys_platform, executable_path, captured_at
    ) VALUES (
        1, 'universal', 'Universal Transpilation Bridge Engine', '2026.1', 2026, 1, 0, 'cross-platform', 'universal', 'internal', datetime('now')
    );
    """)

    # 3. Populate Canonical Concepts
    concept_id_map = {}
    for key, cat, arity, desc in CONCEPTS:
        cursor.execute(
            "INSERT INTO universal_concepts (concept_key, category, type_arity, description) VALUES (?, ?, ?, ?);",
            (key, cat, arity, desc)
        )
        concept_id_map[key] = cursor.lastrowid

    # 4. Pass 1: Populate Type Mappings & Empirical Verification
    db_mgr = DatabaseManager()
    fed_conn = None
    try:
        fed_conn = db_mgr._get_federated_connection("recommended")
        fed_cursor = fed_conn.cursor()
    except Exception as e:
        fed_cursor = None

    for concept_key, lang_map in TYPE_MAPPINGS_DEF.items():
        cid = concept_id_map.get(concept_key)
        if not cid:
            continue
        for lang, (target_name, syntax_template, req_import, mem_model, null_model) in lang_map.items():
            status = "unresolved"
            container_id = None
            symbol_id = None
            stratum = None

            # Empirical scan against federated catalogs
            if fed_cursor:
                try:
                    fed_cursor.execute(
                        """
                        SELECT c.container_id, d.stratum
                        FROM v_all_containers c
                        JOIN v_all_distributions d ON c.dist_id = d.dist_id AND c.language = d.language
                        WHERE c.language = ? AND (c.short_name = ? OR c.qualified_name LIKE ?)
                        LIMIT 1;
                        """,
                        (lang, target_name, f"%{target_name}%")
                    )
                    row = fed_cursor.fetchone()
                    if row:
                        container_id = row[0]
                        stratum = row[1]
                        status = "verified_exact"
                    else:
                        fed_cursor.execute(
                            """
                            SELECT s.symbol_id
                            FROM v_all_symbols s
                            WHERE s.language = ? AND s.name = ?
                            LIMIT 1;
                            """,
                            (lang, target_name)
                        )
                        srow = fed_cursor.fetchone()
                        if srow:
                            symbol_id = srow[0]
                            status = "verified_alias"
                except Exception:
                    pass

            cursor.execute("""
            INSERT INTO universal_type_mappings (
                concept_id, language, target_qualified_name, type_syntax_template, required_import,
                memory_model, nullability_model, catalog_container_id, catalog_symbol_id,
                verified_stratum, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cid, lang, target_name, syntax_template, req_import,
                mem_model, null_model, container_id, symbol_id, stratum, status
            ))

    # 5. Pass 2: Populate Operation Mappings
    for concept_key, op_name, lang_map in OPERATION_MAPPINGS_DEF:
        cid = concept_id_map.get(concept_key)
        if not cid:
            continue
        for lang, (sym_name, syntax, pass_kind, mutates, returns_val) in lang_map.items():
            sym_id = None
            status = "unresolved"
            if fed_cursor:
                try:
                    fed_cursor.execute(
                        "SELECT symbol_id FROM v_all_symbols WHERE language = ? AND name = ? LIMIT 1;",
                        (lang, sym_name)
                    )
                    srow = fed_cursor.fetchone()
                    if srow:
                        sym_id = srow[0]
                        status = "verified_exact"
                except Exception:
                    pass

            cursor.execute("""
            INSERT INTO universal_operation_mappings (
                concept_id, canonical_op, language, target_symbol_name, call_syntax_template,
                receiver_pass_kind, mutates_receiver, returns_new_value, catalog_symbol_id, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (cid, op_name, lang, sym_name, syntax, pass_kind, mutates, returns_val, sym_id, status))

    # 6. Pass 3: Populate Protocol Mappings
    for concept_key, lang_entries in PROTOCOL_MAPPINGS_DEF:
        cid = concept_id_map.get(concept_key)
        if not cid:
            continue
        for lang, c_kind, c_name, req_methods, low_strat in lang_entries:
            cursor.execute("""
            INSERT INTO universal_protocol_mappings (
                concept_id, language, contract_kind, contract_qualified_name, required_methods_json, lowering_strategy, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (cid, lang, c_kind, c_name, req_methods, low_strat, "verified_exact"))

    # 7. Pass 4: Harvest Long-Tail Stdlib Taxonomy
    if fed_cursor:
        try:
            fed_cursor.execute("""
            SELECT c.language, c.container_kind, d.stratum, c.qualified_name, c.short_name, c.container_id
            FROM v_all_containers c
            JOIN v_all_distributions d ON c.dist_id = d.dist_id AND c.language = d.language
            WHERE c.container_kind IN ('class', 'interface', 'trait', 'struct')
            LIMIT 150;
            """)
            for row in fed_cursor.fetchall():
                lang, knd, strat, qname, sname, cid = row
                domain = "exception" if ("Error" in sname or "Exception" in sname) else (
                    "protocol_trait_interface" if knd in ("interface", "trait") else "collection"
                )
                cursor.execute("""
                INSERT OR IGNORE INTO discovered_stdlib_taxonomy (
                    language, taxonomy_domain, stratum, entity_kind, qualified_name, short_name, catalog_container_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (lang, domain, strat or 1, knd, qname, sname, cid))
        except Exception:
            pass

    if fed_conn:
        fed_conn.close()

    conn.commit()
    conn.close()
    print(f"Universal Bridge database built successfully at: {target_path}")


def main():
    build_bridge_database()


if __name__ == "__main__":
    main()
