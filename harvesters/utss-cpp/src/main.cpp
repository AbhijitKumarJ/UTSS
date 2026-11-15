#include "../include/utss/schema.hpp"
#include "../include/utss/stratum0_ambient.hpp"
#include "../include/utss/stratum1_std.hpp"
#include "../include/utss/stratum3_workspace.hpp"
#include "../include/utss/queries.hpp"
#include <iostream>
#include <string>
#include <vector>
#include <filesystem>

namespace fs = std::filesystem;

void print_usage() {
    std::cout << R"USAGE(
UTSS C/C++ Cataloger (utss-cpp)

Usage:
  utss-cpp harvest [options]
  utss-cpp report  --db <path>
  utss-cpp query   --db <path> [options]

Harvest Options:
  --db <path>             SQLite database file path (default: catalog_cpp_demo.db)
  --reset                 Drop existing tables and recreate schema
  --stratum0              Harvest Stratum 0 (Ambient Scope: keywords, primitives, builtins)
  --std-recommended       Harvest Stratum 1 (Curated Tier-1 C++ standard library)
  --std-full              Harvest Stratum 1 (Full ISO C++20 standard library, 64 headers)
  --demo-workspace        Harvest Stratum 3 (Embedded C++ demo workspace: commerce_engine)
  --workspace-dir <dir>   Harvest Stratum 3 from a physical codebase directory

Query Options:
  --spectrum              Display spectrum summary breakdown across all Strata (0, 1, 3)
  --ambient               Display breakdown of ambient keywords, primitives, and globals
  --stdlib                Display breakdown of harvested standard library modules
  --workspace-symbols     Display workspace symbols with 1-based AST source span coordinates
  --cpp-facets            Display C++ container and symbol fidelity facets
)USAGE" << std::endl;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage();
        return 0;
    }

    std::string command = argv[1];
    if (command == "--help" || command == "-h" || command == "help") {
        print_usage();
        return 0;
    }

    std::string db_path = "catalog_cpp_demo.db";
    bool reset = false;
    bool stratum0 = false;
    bool std_rec = false;
    bool std_full = false;
    bool demo_ws = false;
    std::string ws_dir = "";

    bool q_spectrum = false;
    bool q_ambient = false;
    bool q_stdlib = false;
    bool q_workspace_symbols = false;
    bool q_cpp_facets = false;

    for (int i = 2; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--db" && i + 1 < argc) {
            db_path = argv[++i];
        } else if (arg == "--reset") {
            reset = true;
        } else if (arg == "--stratum0") {
            stratum0 = true;
        } else if (arg == "--std-recommended") {
            std_rec = true;
        } else if (arg == "--std-full") {
            std_full = true;
        } else if (arg == "--demo-workspace") {
            demo_ws = true;
        } else if (arg == "--workspace-dir" && i + 1 < argc) {
            ws_dir = argv[++i];
        } else if (arg == "--spectrum") {
            q_spectrum = true;
        } else if (arg == "--ambient") {
            q_ambient = true;
        } else if (arg == "--stdlib") {
            q_stdlib = true;
        } else if (arg == "--workspace-symbols") {
            q_workspace_symbols = true;
        } else if (arg == "--cpp-facets") {
            q_cpp_facets = true;
        }
    }

    try {
        if (command == "harvest") {
            std::cout << "[UTSS.C++] Opening SQLite database: " << db_path << std::endl;
            utss::Database db(db_path);

            if (reset) {
                std::cout << "[UTSS.C++] Resetting schema (dropping existing tables)..." << std::endl;
                utss::reset_schema(db.handle());
            } else {
                utss::init_schema(db.handle());
            }

            int64_t env_id = 1;

            if (stratum0) {
                std::cout << "[UTSS.C++] Harvesting Stratum 0 (Ambient Scope)..." << std::endl;
                auto res0 = utss::harvest_stratum0_ambient(db.handle());
                env_id = res0.env_id;
                std::cout << "  -> Harvested " << res0.keyword_count << " keywords, "
                          << res0.primitive_count << " primitives, "
                          << res0.builtin_count << " built-ins." << std::endl;
            } else {
                auto res0 = utss::harvest_stratum0_ambient(db.handle());
                env_id = res0.env_id;
            }

            if (std_rec) {
                std::cout << "[UTSS.C++] Harvesting Stratum 1 (Curated Tier-1 Standard Library)..." << std::endl;
                auto res1 = utss::harvest_stratum1_std(db.handle(), env_id, false);
                std::cout << "  -> Harvested " << res1.containers_harvested << " containers, "
                          << res1.symbols_harvested << " symbols, "
                          << res1.callables_harvested << " callables, "
                          << res1.parameters_harvested << " parameters." << std::endl;
            } else if (std_full) {
                std::cout << "[UTSS.C++] Harvesting Stratum 1 (Full ISO C++20 Standard Library Distribution)..." << std::endl;
                auto res1 = utss::harvest_stratum1_std(db.handle(), env_id, true);
                std::cout << "  -> Harvested " << res1.containers_harvested << " containers, "
                          << res1.symbols_harvested << " symbols, "
                          << res1.callables_harvested << " callables, "
                          << res1.parameters_harvested << " parameters." << std::endl;
            }

            if (demo_ws) {
                std::cout << "[UTSS.C++] Harvesting Stratum 3 (Embedded Demo Workspace: commerce_engine)..." << std::endl;
                utss::WorkspaceAstCataloger cataloger(db.handle(), env_id);
                auto res3 = cataloger.harvest_embedded_demo();
                std::cout << "  -> Harvested " << res3.files_processed << " files: "
                          << res3.containers_harvested << " containers, "
                          << res3.symbols_harvested << " symbols, "
                          << res3.callables_harvested << " callables, "
                          << res3.parameters_harvested << " parameters, "
                          << res3.state_members_harvested << " state members, "
                          << res3.aliases_harvested << " aliases." << std::endl;
            } else if (!ws_dir.empty()) {
                std::cout << "[UTSS.C++] Harvesting Stratum 3 from workspace directory: " << ws_dir << "..." << std::endl;
                utss::WorkspaceAstCataloger cataloger(db.handle(), env_id);
                auto res3 = cataloger.harvest_directory(ws_dir);
                std::cout << "  -> Harvested " << res3.files_processed << " files: "
                          << res3.containers_harvested << " containers, "
                          << res3.symbols_harvested << " symbols, "
                          << res3.callables_harvested << " callables, "
                          << res3.parameters_harvested << " parameters, "
                          << res3.state_members_harvested << " state members, "
                          << res3.aliases_harvested << " aliases." << std::endl;
            }

            std::cout << "[UTSS.C++] Harvesting successfully completed for '" << db_path << "'." << std::endl;
        } else if (command == "report") {
            if (!fs::exists(db_path)) {
                std::cerr << "Error: Database file not found: " << db_path << std::endl;
                return 1;
            }
            utss::Database db(db_path);
            std::cout << "\n================================================================================" << std::endl;
            std::cout << "                 UTSS C/C++ CATALOG AUDIT REPORT" << std::endl;
            std::cout << "                 Database: " << fs::absolute(db_path).string() << std::endl;
            std::cout << "================================================================================" << std::endl;
            utss::print_spectrum_summary(db.handle());
        } else if (command == "query") {
            if (!fs::exists(db_path)) {
                std::cerr << "Error: Database file not found: " << db_path << std::endl;
                return 1;
            }
            utss::Database db(db_path);
            if (q_spectrum) utss::print_spectrum_summary(db.handle());
            if (q_ambient) utss::print_ambient_summary(db.handle());
            if (q_stdlib) utss::print_stdlib_summary(db.handle());
            if (q_workspace_symbols) utss::print_workspace_symbols(db.handle());
            if (q_cpp_facets) utss::print_cpp_facets(db.handle());
        } else {
            std::cerr << "Unknown command: " << command << std::endl;
            print_usage();
            return 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
