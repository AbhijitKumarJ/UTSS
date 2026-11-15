-- ==============================================================================
-- Universal Type & Symbol System (UTSS) - OLAP Analytical Schema
-- Views and Aggregations for DuckDB & Multi-Catalog Reporting
--
-- License: CC0-1.0 (Public Domain Dedication)
-- ==============================================================================

-- Unified Cross-Catalog Symbol View
CREATE VIEW IF NOT EXISTS v_unified_symbols AS
SELECT 
    'python' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM python_db.symbols s
JOIN python_db.containers c ON s.container_id = c.container_id
JOIN python_db.distributions d ON c.dist_id = d.dist_id

UNION ALL

SELECT 
    'csharp' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM csharp_db.symbols s
JOIN csharp_db.containers c ON s.container_id = c.container_id
JOIN csharp_db.distributions d ON c.dist_id = d.dist_id

UNION ALL

SELECT 
    'rust' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM rust_db.symbols s
JOIN rust_db.containers c ON s.container_id = c.container_id
JOIN rust_db.distributions d ON c.dist_id = d.dist_id

UNION ALL

SELECT 
    'typescript' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM ts_db.symbols s
JOIN ts_db.containers c ON s.container_id = c.container_id
JOIN ts_db.distributions d ON c.dist_id = d.dist_id

UNION ALL

SELECT 
    'cpp' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM cpp_db.symbols s
JOIN cpp_db.containers c ON s.container_id = c.container_id
JOIN cpp_db.distributions d ON c.dist_id = d.dist_id

UNION ALL

SELECT 
    'go' AS language,
    s.symbol_id,
    s.name,
    s.symbol_kind,
    d.stratum,
    c.short_name AS container_name,
    c.qualified_name AS container_fqn
FROM go_db.symbols s
JOIN go_db.containers c ON s.container_id = c.container_id
JOIN go_db.distributions d ON c.dist_id = d.dist_id;

-- Stratum Distribution Metrics
CREATE VIEW IF NOT EXISTS v_stratum_summary AS
SELECT 
    language,
    stratum,
    COUNT(*) AS total_symbols
FROM v_unified_symbols
GROUP BY language, stratum
ORDER BY language, stratum;
