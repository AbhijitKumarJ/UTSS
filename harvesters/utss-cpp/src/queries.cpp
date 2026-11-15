#include "../include/utss/queries.hpp"
#include <iostream>
#include <iomanip>

namespace utss {

void print_spectrum_summary(sqlite3* db) {
    std::cout << "\n=== Spectrum Summary by Stratum ===" << std::endl;
    std::string sql = R"SQL(
        SELECT
            d.stratum,
            d.dist_name,
            d.dist_version,
            COUNT(DISTINCT c.container_id) AS total_containers,
            COUNT(DISTINCT s.symbol_id) AS total_symbols,
            COUNT(DISTINCT cal.symbol_id) AS total_callables,
            COUNT(DISTINCT p.param_id) AS total_parameters,
            COUNT(DISTINCT a.alias_id) AS total_aliases
        FROM distributions d
        LEFT JOIN containers c ON c.dist_id = d.dist_id
        LEFT JOIN symbols s ON s.container_id = c.container_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        LEFT JOIN parameters p ON p.callable_symbol_id = cal.symbol_id
        LEFT JOIN symbol_aliases a ON a.source_container_id = c.container_id
        GROUP BY d.dist_id
        ORDER BY d.stratum, d.dist_name;
    )SQL";

    Statement stmt(db, sql);
    std::cout << std::left
              << std::setw(9)  << "Stratum"
              << std::setw(20) << "Distribution"
              << std::setw(14) << "Version"
              << std::setw(13) << "Containers"
              << std::setw(11) << "Symbols"
              << std::setw(12) << "Callables"
              << std::setw(13) << "Parameters"
              << std::setw(10) << "Aliases"
              << "\n"
              << std::string(102, '-') << "\n";

    while (stmt.step()) {
        std::cout << std::left
                  << std::setw(9)  << stmt.column_int(0)
                  << std::setw(20) << stmt.column_text(1)
                  << std::setw(14) << stmt.column_text(2)
                  << std::setw(13) << stmt.column_int(3)
                  << std::setw(11) << stmt.column_int(4)
                  << std::setw(12) << stmt.column_int(5)
                  << std::setw(13) << stmt.column_int(6)
                  << std::setw(10) << stmt.column_int(7)
                  << "\n";
    }
}

void print_ambient_summary(sqlite3* db) {
    std::cout << "\n=== Stratum 0 Ambient Summary ===" << std::endl;
    std::string sql = R"SQL(
        SELECT
            s.symbol_kind,
            COUNT(*) AS item_count,
            GROUP_CONCAT(s.name, ', ') AS sample_items
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        WHERE d.stratum = 0
        GROUP BY s.symbol_kind
        ORDER BY item_count DESC;
    )SQL";

    Statement stmt(db, sql);
    std::cout << std::left
              << std::setw(18) << "Symbol Kind"
              << std::setw(12) << "Count"
              << "Sample Items\n"
              << std::string(80, '-') << "\n";

    while (stmt.step()) {
        std::string samples = stmt.column_text(2);
        if (samples.length() > 50) samples = samples.substr(0, 47) + "...";
        std::cout << std::left
                  << std::setw(18) << stmt.column_text(0)
                  << std::setw(12) << stmt.column_int(1)
                  << samples << "\n";
    }
}

void print_stdlib_summary(sqlite3* db) {
    std::cout << "\n=== Stratum 1 Standard Library Breakdown ===" << std::endl;
    std::string sql = R"SQL(
        SELECT
            c.qualified_name AS module_name,
            c.container_kind,
            COUNT(s.symbol_id) AS symbol_count,
            COUNT(cal.symbol_id) AS callable_count
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN symbols s ON s.container_id = c.container_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        WHERE d.stratum = 1
        GROUP BY c.container_id
        ORDER BY symbol_count DESC, c.qualified_name;
    )SQL";

    Statement stmt(db, sql);
    std::cout << std::left
              << std::setw(30) << "Module / Header"
              << std::setw(16) << "Container Kind"
              << std::setw(14) << "Symbols"
              << std::setw(12) << "Callables"
              << "\n"
              << std::string(72, '-') << "\n";

    while (stmt.step()) {
        std::cout << std::left
                  << std::setw(30) << stmt.column_text(0)
                  << std::setw(16) << stmt.column_text(1)
                  << std::setw(14) << stmt.column_int(2)
                  << std::setw(12) << stmt.column_int(3)
                  << "\n";
    }
}

void print_workspace_symbols(sqlite3* db) {
    std::cout << "\n=== Stratum 3 Workspace Symbols & AST Coordinates ===" << std::endl;
    std::string sql = R"SQL(
        SELECT
            c.qualified_name AS container,
            s.name AS symbol_name,
            s.symbol_kind,
            f.access_specifier,
            s.start_line,
            s.start_col,
            s.end_line,
            s.end_col,
            cal.raw_signature,
            cal.return_type_expr
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN cpp_symbol_facets f ON f.symbol_id = s.symbol_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        WHERE d.stratum = 3
        ORDER BY c.qualified_name, s.start_line, s.name;
    )SQL";

    Statement stmt(db, sql);
    std::cout << std::left
              << std::setw(28) << "Container"
              << std::setw(22) << "Symbol"
              << std::setw(14) << "Kind"
              << std::setw(10) << "Access"
              << std::setw(12) << "Span (L:C)"
              << std::setw(18) << "Return Type"
              << "Signature\n"
              << std::string(120, '-') << "\n";

    while (stmt.step()) {
        std::string span = "L" + std::to_string(stmt.column_int(4)) + ":C" + std::to_string(stmt.column_int(5)) +
                           "-L" + std::to_string(stmt.column_int(6)) + ":C" + std::to_string(stmt.column_int(7));
        std::string sig = stmt.column_text(8);
        if (sig.length() > 40) sig = sig.substr(0, 37) + "...";

        std::cout << std::left
                  << std::setw(28) << stmt.column_text(0)
                  << std::setw(22) << stmt.column_text(1)
                  << std::setw(14) << stmt.column_text(2)
                  << std::setw(10) << stmt.column_text(3)
                  << std::setw(12) << span
                  << std::setw(18) << stmt.column_text(9)
                  << sig << "\n";
    }
}

void print_cpp_facets(sqlite3* db) {
    std::cout << "\n=== C++ Container & Symbol Fidelity Facets ===" << std::endl;
    std::string sql = R"SQL(
        SELECT
            c.qualified_name AS container,
            cf.item_kind AS container_kind,
            cf.base_classes_json,
            s.name AS symbol,
            sf.member_kind,
            sf.access_specifier,
            sf.is_virtual,
            sf.is_pure_virtual,
            sf.is_override,
            sf.is_const
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN cpp_container_facets cf ON cf.container_id = c.container_id
        JOIN cpp_symbol_facets sf ON sf.symbol_id = s.symbol_id
        ORDER BY c.qualified_name, s.name
        LIMIT 30;
    )SQL";

    Statement stmt(db, sql);
    std::cout << std::left
              << std::setw(26) << "Container"
              << std::setw(14) << "Kind"
              << std::setw(22) << "Symbol"
              << std::setw(14) << "Member Kind"
              << std::setw(10) << "Access"
              << std::setw(9)  << "Virtual"
              << std::setw(8)  << "Pure"
              << std::setw(10) << "Override"
              << std::setw(7)  << "Const"
              << "\n"
              << std::string(110, '-') << "\n";

    while (stmt.step()) {
        std::cout << std::left
                  << std::setw(26) << stmt.column_text(0)
                  << std::setw(14) << stmt.column_text(1)
                  << std::setw(22) << stmt.column_text(3)
                  << std::setw(14) << stmt.column_text(4)
                  << std::setw(10) << stmt.column_text(5)
                  << std::setw(9)  << (stmt.column_int(6) ? "yes" : "no")
                  << std::setw(8)  << (stmt.column_int(7) ? "yes" : "no")
                  << std::setw(10) << (stmt.column_int(8) ? "yes" : "no")
                  << std::setw(7)  << (stmt.column_int(9) ? "yes" : "no")
                  << "\n";
    }
}

} // namespace utss
