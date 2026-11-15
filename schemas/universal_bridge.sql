-- ==============================================================================
-- Universal Type & Symbol System (UTSS) - Universal Bridge Schema
-- DDL Specification for Universal Type Mapping & Cross-Language Transpilation
--
-- License: CC0-1.0 (Public Domain Dedication)
-- To the extent possible under law, the author(s) have dedicated all copyright
-- and related and neighboring rights to this software to the public domain worldwide.
-- This software is distributed without any warranty.
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. Language Catalog Registrations
-- ------------------------------------------------------------------------------
-- Registers connected language catalogs participating in the universal bridge.
CREATE TABLE IF NOT EXISTS bridge_languages (
    language_id         TEXT PRIMARY KEY,            -- 'python', 'csharp', 'rust', 'typescript', 'cpp', 'go'
    display_name        TEXT NOT NULL,               -- 'Python', 'C# .NET', 'Rust', etc.
    catalog_path        TEXT NOT NULL,               -- Relative path to sqlite .db catalog
    schema_version      TEXT NOT NULL DEFAULT '1.0.0',
    type_system_flavor  TEXT NOT NULL,               -- 'dynamic', 'nominal_static', 'affine_static', 'structural'
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------------------------
-- 2. Canonical Primitive & Abstract Types
-- ------------------------------------------------------------------------------
-- Language-neutral abstract types (e.g. 'i32', 'f64', 'bool', 'string', 'list', 'map', 'void')
CREATE TABLE IF NOT EXISTS canonical_types (
    canonical_type_id   TEXT PRIMARY KEY,            -- 'utss.primitive.i32', 'utss.primitive.string', etc.
    type_category       TEXT NOT NULL,               -- 'primitive_numeric', 'primitive_text', 'collection', 'callable', 'any'
    bit_width           INTEGER,                     -- e.g. 8, 16, 32, 64 (NULL for unbounded/dynamic)
    is_signed           INTEGER DEFAULT 0,           -- 1 if signed numeric
    is_nullable         INTEGER DEFAULT 0,           -- 1 if nullable by default
    description         TEXT
);

-- ------------------------------------------------------------------------------
-- 3. Cross-Language Type Mappings
-- ------------------------------------------------------------------------------
-- Maps native language types to canonical types and directly between languages.
CREATE TABLE IF NOT EXISTS type_mappings (
    mapping_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    source_type_expr    TEXT NOT NULL,               -- e.g. 'int' (Python), 'int' (C#), 'i64' (Rust), 'number' (TS)
    canonical_type_id   TEXT NOT NULL REFERENCES canonical_types(canonical_type_id),
    target_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    target_type_expr    TEXT NOT NULL,               -- Target concrete type syntax
    conversion_cost     INTEGER DEFAULT 0,           -- 0 = lossless/identity, 1 = widening, 2 = narrowing/boxing
    conversion_strategy TEXT NOT NULL DEFAULT 'direct', -- 'direct', 'cast', 'box', 'wrapper_adapter', 'custom_marshaler'
    marshal_template    TEXT,                        -- Code template for emission, e.g. 'Convert.ToInt32({expr})'
    UNIQUE(source_language, source_type_expr, target_language)
);

-- ------------------------------------------------------------------------------
-- 4. Cross-Language Symbol & API Equivalences
-- ------------------------------------------------------------------------------
-- Connects standard library functions, methods, and classes across languages.
CREATE TABLE IF NOT EXISTS symbol_equivalences (
    equivalence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_concept   TEXT NOT NULL,               -- e.g. 'math.sqrt', 'json.serialize', 'file.read_text'
    source_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    source_symbol_fqn   TEXT NOT NULL,               -- e.g. 'math.sqrt', 'System.Math.Sqrt', 'std::f64::sqrt'
    target_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    target_symbol_fqn   TEXT NOT NULL,               -- Target FQN
    equivalence_quality TEXT NOT NULL DEFAULT 'exact', -- 'exact', 'close_superset', 'partial_subset', 'emulated'
    parameter_reordering_json TEXT,                  -- JSON map if argument positions differ: {"0": 1, "1": 0}
    semantic_notes      TEXT,
    UNIQUE(source_language, source_symbol_fqn, target_language)
);

-- ------------------------------------------------------------------------------
-- 5. Universal Semantic Facets
-- ------------------------------------------------------------------------------
-- Captures pure behavior semantics independent of language runtime quirks.
CREATE TABLE IF NOT EXISTS semantic_facets (
    facet_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    language_id         TEXT NOT NULL REFERENCES bridge_languages(language_id),
    symbol_fqn          TEXT NOT NULL,
    is_pure             INTEGER DEFAULT 0,           -- 1 if mathematically pure (no side effects)
    is_idempotent       INTEGER DEFAULT 0,           -- 1 if repeating call yields same state
    allocates_heap      INTEGER DEFAULT 1,           -- 1 if invocation allocates heap memory
    can_throw           INTEGER DEFAULT 0,           -- 1 if can throw runtime exception/panic
    is_thread_safe      INTEGER DEFAULT 1,           -- 1 if thread safe for concurrent access
    time_complexity     TEXT,                        -- 'O(1)', 'O(n)', 'O(n log n)'
    space_complexity    TEXT,                        -- 'O(1)', 'O(n)'
    UNIQUE(language_id, symbol_fqn)
);

-- ------------------------------------------------------------------------------
-- 6. Generated Bridge Bindings & Trampolines
-- ------------------------------------------------------------------------------
-- Tracks emitted code generation artifacts (e.g. *.g.cs, *.rs, *.go wrappers).
CREATE TABLE IF NOT EXISTS bridge_bindings (
    binding_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    source_symbol_fqn   TEXT NOT NULL,
    target_language     TEXT NOT NULL REFERENCES bridge_languages(language_id),
    binding_artifact    TEXT NOT NULL,               -- Path to generated source file, e.g. 'UtssBridge.g.cs'
    binding_kind        TEXT NOT NULL,               -- 'invoker_stub', 'interop_marshaler', 'type_proxy'
    emitted_code        TEXT NOT NULL,               -- Emitted source binding text
    generated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ------------------------------------------------------------------------------
-- Indexes for Sub-Millisecond Cross-Language Lookups
-- ------------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_type_mappings_lookup 
    ON type_mappings(source_language, source_type_expr, target_language);

CREATE INDEX IF NOT EXISTS idx_symbol_equivalences_lookup 
    ON symbol_equivalences(source_language, source_symbol_fqn, target_language);

CREATE INDEX IF NOT EXISTS idx_symbol_equivalences_concept 
    ON symbol_equivalences(canonical_concept);

CREATE INDEX IF NOT EXISTS idx_semantic_facets_lookup 
    ON semantic_facets(language_id, symbol_fqn);
