#pragma once

#include "schema.hpp"
#include <string>
#include <vector>

namespace utss {

void print_spectrum_summary(sqlite3* db);
void print_ambient_summary(sqlite3* db);
void print_stdlib_summary(sqlite3* db);
void print_workspace_symbols(sqlite3* db);
void print_cpp_facets(sqlite3* db);

} // namespace utss
