# Technical Specification: Universal Bridge Database Schema & Pipeline

This document defines the schema, data models, and population algorithm for **`dbs/utss_universal_bridge.db`**, the empirical core powering cross-language type mapping, operation translation, and protocol normalization across Python, C#, C++, Go, Rust, and TypeScript.

---

## 1. Architectural Role

The Universal Bridge Database is an empirical SQLite store compiled by `server/analysis/build_bridge_db.py`. It bridges high-level compiler Intermediate Representation (IR) concepts to concrete standard library types and method signatures in all 6 target languages.

```
┌────────────────────────────────────────────────────────┐
│               Universal Concept (IR)                   │
│           concept_key: 'collection.dynamic_array'      │
│           category: 'collection', type_arity: 1        │
└───────────┬────────────────────────────────────────────┘
            │
            ├────────────────────────────────────────────┐
            ▼                                            ▼
┌────────────────────────────────────────┐  ┌────────────────────────────────────────┐
│       universal_type_mappings          │  │     universal_operation_mappings       │
│ • Python: builtins.list[T]             │  │ • canonical_op: 'append'               │
│ • C#:     System.Collections...List<T> │  │ • Python: list.append(x) (mut_ref)     │
│ • C++:    std::vector<T>               │  │ • C#:     List.Add(item) (ref)         │
│ • Rust:   alloc::vec::Vec<T>           │  │ • C++:    vector.push_back(val) (ref)  │
│ • Go:     []T                          │  │ • Rust:   Vec.push(val) (mut_ref)      │
│ • TS:     Array<T>                     │  │ • Go:     append(s, x) (free_fn)       │
└────────────────────────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. Relational DDL Schema

### Table 1: `universal_concepts`
Language-agnostic IR concepts covering primitives, collections, control flow, exceptions, I/O, and protocols.

```sql
CREATE TABLE universal_concepts (
    concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_key TEXT NOT NULL UNIQUE,       -- e.g. 'primitive.int32', 'collection.dynamic_array'
    category TEXT NOT NULL,                 -- 'primitive', 'collection', 'control_flow', 'exception', 'io', 'protocol'
    type_arity INTEGER NOT NULL DEFAULT 0,  -- 0 = concrete, 1 = <T>, 2 = <K, V>
    description TEXT NOT NULL
);
```

### Table 2: `universal_type_mappings`
Maps each universal concept to its corresponding target type in each language, enriched with empirical metadata from the catalog.

```sql
CREATE TABLE universal_type_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,                 -- 'python', 'csharp', 'cpp', 'go', 'rust', 'typescript'
    target_qualified_name TEXT NOT NULL,
    fallback_candidates_json TEXT NOT NULL DEFAULT '[]',
    type_syntax_template TEXT NOT NULL,     -- e.g. 'Vec<{T}>', 'List<{T}>', 'std::vector<{T}>'
    required_import TEXT,                   -- e.g. 'System.Collections.Generic', '<vector>', 'alloc::vec::Vec'
    memory_model TEXT NOT NULL,             -- 'value_stack', 'ref_gc', 'owned_heap', 'rc_box', 'slice_header'
    nullability_model TEXT NOT NULL,        -- 'nullable_ref', 'option_wrapper', 'value_default', 'pointer_nil'
    
    -- Empirical verification fields populated from language catalog scan:
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    resolved_qualified_name TEXT,
    verified_stratum INTEGER,
    verified_requires_import INTEGER,
    verification_status TEXT NOT NULL DEFAULT 'unresolved', -- 'verified_exact', 'verified_alias', 'unresolved'
    layer2_facet_json TEXT,
    notes TEXT,
    UNIQUE(concept_id, language)
);
```

### Table 3: `universal_operation_mappings`
Maps canonical operations (e.g. `append`, `push`, `get`, `len`, `clear`) to live method names, call syntax templates, and receiver semantics.

```sql
CREATE TABLE universal_operation_mappings (
    op_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    canonical_op TEXT NOT NULL,             -- 'append', 'prepend', 'pop', 'get', 'set', 'len', 'clear'
    language TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,       -- 'append', 'Add', 'push_back', 'push'
    call_syntax_template TEXT NOT NULL,     -- '{receiver}.Add({item})', 'append({receiver}, {item})'
    receiver_pass_kind TEXT NOT NULL,       -- 'val', 'ref', 'mut_ref', 'pointer', 'free_fn', 'operator'
    mutates_receiver INTEGER NOT NULL DEFAULT 0,
    returns_new_value INTEGER NOT NULL DEFAULT 0,
    
    -- Empirical verification fields from callables and parameters:
    catalog_symbol_id INTEGER,
    verified_qualified_name TEXT,
    verified_raw_signature TEXT,
    verified_return_type TEXT,
    verified_overload_count INTEGER NOT NULL DEFAULT 0,
    verified_pass_kinds_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, canonical_op, language)
);
```

### Table 4: `universal_protocol_mappings`
Maps behavioral contracts across dynamic protocols, interfaces, traits, and concepts.

```sql
CREATE TABLE universal_protocol_mappings (
    proto_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES universal_concepts(concept_id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    contract_kind TEXT NOT NULL,            -- 'dunder_protocol', 'interface', 'trait', 'implicit_interface', 'concept'
    contract_qualified_name TEXT NOT NULL,  -- e.g. 'System.Collections.Generic.IEnumerable', 'core::iter::Iterator'
    required_methods_json TEXT NOT NULL,    -- '["__iter__", "__next__"]', '["GetEnumerator"]', '["next"]'
    lowering_strategy TEXT NOT NULL,        -- 'runtime_dispatch', 'vtable_slot', 'monomorphized_trait', 'duck_typing'
    
    -- Empirical verification fields:
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    implementing_count INTEGER NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'unresolved',
    UNIQUE(concept_id, language)
);
```

### Table 5: `discovered_stdlib_taxonomy`
Autonomous catalog of long-tail standard library types (all unmapped exceptions, collections, streams, and traits) for complete transpilation coverage.

```sql
CREATE TABLE discovered_stdlib_taxonomy (
    discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    taxonomy_domain TEXT NOT NULL,          -- 'exception', 'collection', 'io_stream', 'protocol_trait_interface'
    stratum INTEGER NOT NULL,
    entity_kind TEXT NOT NULL,              -- 'class', 'struct', 'interface', 'trait'
    qualified_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    catalog_container_id INTEGER,
    catalog_symbol_id INTEGER,
    public_method_count INTEGER NOT NULL DEFAULT 0,
    layer2_metadata_json TEXT,
    UNIQUE(language, taxonomy_domain, qualified_name)
);
```

---

## 3. Four-Pass Automated Extraction Pipeline

The populator (`server/analysis/build_bridge_db.py`) runs four sequential passes across all 6 databases:

```
Pass 1: Concept & Type Resolution
  │  Scans containers & symbols for target types.
  │  Matches qualified_name and symbol_aliases.
  ▼
Pass 2: Operation & Signature Binding
  │  Scans callables, callable_overloads, and parameters.
  │  Extracts exact raw_signature and return_type_expr.
  ▼
Pass 3: Protocol & Contract Verification
  │  Scans implemented_interfaces_json, py_symbol_facets,
  │  rust_container_facets, and cpp_symbol_facets.
  ▼
Pass 4: Autonomous Stdlib Taxonomist
     Harvests all unmapped collections, exceptions, and I/O streams.
```

---

## 4. Canonical Concepts Inventory

The database initializes with verified canonical concepts across 6 domains:

1. **Primitives**:
   - `primitive.int32` (i32, int, int32, number)
   - `primitive.int64` (i64, long, int64, bigint)
   - `primitive.float64` (f64, double, float64, number)
   - `primitive.bool` (bool, boolean)
   - `primitive.string_utf8` (str, string, String, std::string)
   - `primitive.byte_sequence` (bytes, byte[], Vec<u8>, []byte, Uint8Array)
2. **Collections**:
   - `collection.dynamic_array` (list, List<T>, Vec<T>, std::vector<T>, []T, Array<T>)
   - `collection.hash_map` (dict, Dictionary<K,V>, HashMap<K,V>, std::unordered_map<K,V>, map[K]V, Map<K,V>)
   - `collection.hash_set` (set, HashSet<T>, HashSet<T>, std::unordered_set<T>, map[T]struct{}, Set<T>)
   - `collection.fifo_queue` (collections.deque, Queue<T>, VecDeque<T>, std::deque<T>)
3. **Control Flow & Wrappers**:
   - `control_flow.option_maybe` (Optional[T], Nullable<T>/?, Option<T>, std::optional<T>, *T, T | undefined)
   - `control_flow.result_either` (Result<T,E>, (T, error), exceptions)
4. **Exceptions**:
   - `exception.io_error` (IOError/OSError, IOException, std::io::Error, std::filesystem_error)
   - `exception.key_not_found` (KeyError, KeyNotFoundException, None/error)
   - `exception.index_out_of_bounds` (IndexError, ArgumentOutOfRangeException, panic)
   - `exception.argument_null` (ValueError/TypeError, ArgumentNullException)
5. **I/O Streams**:
   - `io.byte_stream` (io.BytesIO, System.IO.MemoryStream, Vec<u8> cursor, bytes.Buffer)
   - `io.text_reader` (io.TextIOWrapper, System.IO.StreamReader, std::io::BufReader)
   - `io.file_handle` (open(), FileStream, std::fs::File, std::fstream, os.File)
6. **Protocols**:
   - `protocol.iteration` (__iter__/__next__, IEnumerable<T>/IEnumerator<T>, Iterator, std::input_iterator, range)
   - `protocol.resource_cleanup` (__enter__/__exit__, IDisposable/using, Drop, RAII destructor, defer)
   - `protocol.ordering_comparison` (__lt__/__gt__, IComparable<T>, Ord/PartialOrd, std::totally_ordered)
