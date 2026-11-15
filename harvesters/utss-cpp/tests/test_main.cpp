#include "../include/utss/schema.hpp"
#include "../include/utss/stratum0_ambient.hpp"
#include "../include/utss/stratum1_std.hpp"
#include "../include/utss/stratum3_workspace.hpp"
#include <iostream>
#include <cassert>
#include <algorithm>

void test_schema_init_and_reset() {
    std::cout << "[Test 1] Testing schema initialization and reset..." << std::flush;
    utss::Database db(":memory:");
    utss::init_schema(db.handle());

    utss::Statement stmt(db.handle(), "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';");
    std::vector<std::string> tables;
    while (stmt.step()) {
        tables.push_back(stmt.column_text(0));
    }

    for (const auto& expected : utss::EXPECTED_TABLES) {
        assert(std::find(tables.begin(), tables.end(), expected) != tables.end() && "Missing expected table");
    }

    utss::reset_schema(db.handle());
    utss::Statement stmt2(db.handle(), "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';");
    std::vector<std::string> tables2;
    while (stmt2.step()) {
        tables2.push_back(stmt2.column_text(0));
    }
    for (const auto& expected : utss::EXPECTED_TABLES) {
        assert(std::find(tables2.begin(), tables2.end(), expected) != tables2.end() && "Missing expected table after reset");
    }
    std::cout << " PASSED" << std::endl;
}

void test_stratum0_ambient() {
    std::cout << "[Test 2] Testing Stratum 0 Ambient harvesting..." << std::flush;
    utss::Database db(":memory:");
    utss::init_schema(db.handle());

    auto res = utss::harvest_stratum0_ambient(db.handle());
    assert(res.keyword_count >= 90 && "Expected >= 90 keywords");
    assert(res.primitive_count >= 20 && "Expected >= 20 primitives");
    assert(res.builtin_count >= 8 && "Expected >= 8 built-ins");

    // Check specific symbol
    utss::Statement stmt(db.handle(), "SELECT symbol_kind FROM symbols WHERE name='template';");
    assert(stmt.step() && "Keyword 'template' must exist");
    assert(stmt.column_text(0) == "keyword");

    utss::Statement stmt2(db.handle(), "SELECT symbol_kind FROM symbols WHERE name='nullptr';");
    assert(stmt2.step() && "Constant 'nullptr' must exist");
    assert(stmt2.column_text(0) == "constant");

    std::cout << " PASSED" << std::endl;
}

void test_stratum1_std() {
    std::cout << "[Test 3] Testing Stratum 1 Standard Library harvesting..." << std::flush;
    utss::Database db(":memory:");
    utss::init_schema(db.handle());

    auto res0 = utss::harvest_stratum0_ambient(db.handle());
    auto res1 = utss::harvest_stratum1_std(db.handle(), res0.env_id, false);

    assert(res1.containers_harvested >= 10 && "Expected >= 10 stdlib containers");
    assert(res1.symbols_harvested >= 10 && "Expected >= 10 stdlib symbols");
    assert(res1.callables_harvested >= 8 && "Expected >= 8 stdlib callables");
    assert(res1.parameters_harvested >= 5 && "Expected >= 5 stdlib parameters");

    // Check std::make_unique function
    utss::Statement stmt(db.handle(), "SELECT raw_signature FROM callables cal JOIN symbols s ON cal.symbol_id=s.symbol_id WHERE s.name='make_unique';");
    assert(stmt.step() && "make_unique must exist in callables");
    assert(stmt.column_text(0).find("unique_ptr") != std::string::npos);

    std::cout << " PASSED" << std::endl;
}

void test_stratum3_workspace() {
    std::cout << "[Test 4] Testing Stratum 3 Pure AST Workspace harvesting..." << std::flush;
    utss::Database db(":memory:");
    utss::init_schema(db.handle());

    auto res0 = utss::harvest_stratum0_ambient(db.handle());
    utss::WorkspaceAstCataloger cataloger(db.handle(), res0.env_id);
    auto res3 = cataloger.harvest_embedded_demo();

    assert(res3.files_processed == 3 && "Expected 3 files processed");
    assert(res3.containers_harvested >= 5 && "Expected >= 5 containers");
    assert(res3.symbols_harvested >= 20 && "Expected >= 20 symbols");
    assert(res3.callables_harvested >= 8 && "Expected >= 8 callables");
    assert(res3.state_members_harvested >= 5 && "Expected >= 5 state members");
    assert(res3.aliases_harvested >= 4 && "Expected >= 4 aliases");

    // Check Order class container & coordinates
    utss::Statement stmt(db.handle(), "SELECT container_kind, start_line, end_line FROM containers WHERE short_name='Order' AND container_kind='class';");
    assert(stmt.step() && "Order class container must exist");
    assert(stmt.column_text(0) == "class");
    assert(stmt.column_int(1) > 0 && "start_line must be positive 1-based");
    assert(stmt.column_int(2) >= stmt.column_int(1) && "end_line must be >= start_line");

    // Check pure virtual process_order in IOrderService
    utss::Statement stmt2(db.handle(), R"SQL(
        SELECT sf.is_pure_virtual, sf.is_virtual, sf.access_specifier
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN cpp_symbol_facets sf ON sf.symbol_id = s.symbol_id
        WHERE s.name='process_order' AND c.short_name='IOrderService';
    )SQL");
    assert(stmt2.step() && "process_order in IOrderService must exist");
    assert(stmt2.column_int(0) == 1 && "is_pure_virtual must be 1 for IOrderService::process_order");
    assert(stmt2.column_int(1) == 1 && "is_virtual must be 1");
    assert(stmt2.column_text(2) == "public");

    // Check override process_order in OrderService
    utss::Statement stmt3(db.handle(), R"SQL(
        SELECT sf.is_override, sf.access_specifier
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN cpp_symbol_facets sf ON sf.symbol_id = s.symbol_id
        WHERE s.name='process_order' AND c.short_name='OrderService';
    )SQL");
    assert(stmt3.step() && "process_order in OrderService must exist");
    assert(stmt3.column_int(0) == 1 && "is_override must be 1 for OrderService::process_order");

    std::cout << " PASSED" << std::endl;
}

int main() {
    std::cout << "==================================================" << std::endl;
    std::cout << "      UTSS C/C++ TEST SUITE EXECUTION" << std::endl;
    std::cout << "==================================================" << std::endl;

    try {
        test_schema_init_and_reset();
        test_stratum0_ambient();
        test_stratum1_std();
        test_stratum3_workspace();
    } catch (const std::exception& e) {
        std::cerr << "\nTest failure with exception: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "==================================================" << std::endl;
    std::cout << " [SUCCESS] All 4 C/C++ Test Cases Passed Cleanly!" << std::endl;
    std::cout << "==================================================" << std::endl;
    return 0;
}
