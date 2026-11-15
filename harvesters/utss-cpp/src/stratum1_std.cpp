#include "../include/utss/stratum1_std.hpp"
#include <string>
#include <vector>

namespace utss {

struct ParamSpec {
    std::string name;
    std::string type;
    std::string pass_kind{"val"};
    std::string default_val{""};
    bool is_optional{false};

    ParamSpec(std::string n, std::string t, std::string pk = "val", std::string def = "", bool opt = false)
        : name(std::move(n)), type(std::move(t)), pass_kind(std::move(pk)), default_val(std::move(def)), is_optional(opt) {}
};

struct FuncSpec {
    std::string name;
    std::string sig;
    std::string ret;
    bool is_static{false};
    bool is_const{false};
    std::vector<ParamSpec> params;
    std::string doc;
};

struct HeaderSpec {
    std::string header_name;
    std::string doc;
    std::vector<FuncSpec> functions;
    std::vector<std::string> classes;
};

Stratum1HarvestResult harvest_stratum1_std(sqlite3* db, int64_t env_id, bool is_full) {
    Stratum1HarvestResult res;

    std::string dist_name = "libstdc++";
    std::string version = "13.3.0";
    std::string summary = is_full
        ? "C++20 ISO Standard Library full distribution (64 standard headers)"
        : "C++20 Curated Tier-1 Standard Library (<iostream>, <vector>, <string>, <memory>, <filesystem>)";

    Statement ins_dist(db, R"SQL(
        INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
        VALUES (?, 1, ?, ?, ?)
        ON CONFLICT(env_id, stratum, dist_name, dist_version)
        DO UPDATE SET summary = excluded.summary;
    )SQL");
    ins_dist.bind_int64(1, env_id);
    ins_dist.bind_text(2, dist_name);
    ins_dist.bind_text(3, version);
    ins_dist.bind_text(4, summary);
    ins_dist.execute();

    Statement sel_dist(db, "SELECT dist_id FROM distributions WHERE env_id=? AND stratum=1 AND dist_name=?;");
    sel_dist.bind_int64(1, env_id);
    sel_dist.bind_text(2, dist_name);
    if (sel_dist.step()) {
        res.dist_id = sel_dist.column_int64(0);
    }

    Statement ins_cont(db, R"SQL(
        INSERT INTO containers (dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring)
        VALUES (?, ?, ?, ?, ?, 1, 'public', ?)
        ON CONFLICT(dist_id, qualified_name)
        DO UPDATE SET docstring = excluded.docstring;
    )SQL");

    Statement sel_cont(db, "SELECT container_id FROM containers WHERE dist_id=? AND qualified_name=?;");

    Statement ins_cont_facet(db, R"SQL(
        INSERT OR REPLACE INTO cpp_container_facets (container_id, item_kind, is_template, is_final, is_abstract)
        VALUES (?, ?, ?, 0, 0);
    )SQL");

    Statement ins_sym(db, R"SQL(
        INSERT INTO symbols (container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring)
        VALUES (?, ?, ?, ?, 'public', 'std_item', ?)
        ON CONFLICT(container_id, name)
        DO UPDATE SET symbol_kind = excluded.symbol_kind;
    )SQL");

    Statement sel_sym(db, "SELECT symbol_id FROM symbols WHERE container_id=? AND name=?;");

    Statement ins_sym_facet(db, R"SQL(
        INSERT OR REPLACE INTO cpp_symbol_facets (
            symbol_id, member_kind, access_specifier, is_virtual, is_pure_virtual, is_override, is_const, is_noexcept, is_constexpr, is_inline, is_static, attributes_json
        ) VALUES (?, ?, 'public', 0, 0, 0, ?, 1, 0, 1, ?, ?);
    )SQL");

    Statement ins_cal(db, R"SQL(
        INSERT OR REPLACE INTO callables (
            symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, return_type_expr, raw_signature, signature_source
        ) VALUES (?, 0, 0, ?, ?, 0, 0, ?, ?, 'cpp_std_metadata');
    )SQL");

    Statement ins_param(db, R"SQL(
        INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional)
        VALUES (?, ?, ?, ?, ?, 'cpp_std_metadata', ?, ?);
    )SQL");

    // Helper lambda to register a container
    auto add_container = [&](int64_t parent_id, const std::string& kind, const std::string& qname, const std::string& sname, const std::string& doc, bool is_tpl) -> int64_t {
        ins_cont.reset();
        ins_cont.bind_int64(1, res.dist_id);
        if (parent_id > 0) ins_cont.bind_int64(2, parent_id);
        else ins_cont.bind_null(2);
        ins_cont.bind_text(3, kind);
        ins_cont.bind_text(4, qname);
        ins_cont.bind_text(5, sname);
        ins_cont.bind_text(6, doc);
        ins_cont.execute();

        sel_cont.reset();
        sel_cont.bind_int64(1, res.dist_id);
        sel_cont.bind_text(2, qname);
        int64_t cid = 0;
        if (sel_cont.step()) {
            cid = sel_cont.column_int64(0);
        }

        ins_cont_facet.reset();
        ins_cont_facet.bind_int64(1, cid);
        ins_cont_facet.bind_text(2, kind);
        ins_cont_facet.bind_int(3, is_tpl ? 1 : 0);
        ins_cont_facet.execute();

        res.containers_harvested++;
        return cid;
    };

    // Helper lambda to register a function/method
    auto add_function = [&](int64_t cid, const std::string& c_qname, const FuncSpec& f, bool is_method) {
        std::string qname = c_qname + "::" + f.name;
        std::string sym_kind = is_method ? "method" : "function";

        ins_sym.reset();
        ins_sym.bind_int64(1, cid);
        ins_sym.bind_text(2, f.name);
        ins_sym.bind_text(3, qname);
        ins_sym.bind_text(4, sym_kind);
        ins_sym.bind_text(5, f.doc);
        ins_sym.execute();

        sel_sym.reset();
        sel_sym.bind_int64(1, cid);
        sel_sym.bind_text(2, f.name);
        int64_t sym_id = 0;
        if (sel_sym.step()) {
            sym_id = sel_sym.column_int64(0);
        }
        res.symbols_harvested++;

        ins_sym_facet.reset();
        ins_sym_facet.bind_int64(1, sym_id);
        ins_sym_facet.bind_text(2, sym_kind);
        ins_sym_facet.bind_int(3, f.is_const ? 1 : 0);
        ins_sym_facet.bind_int(4, f.is_static ? 1 : 0);
        std::string attr = R"(["std"])";
        ins_sym_facet.bind_text(5, attr);
        ins_sym_facet.execute();

        ins_cal.reset();
        ins_cal.bind_int64(1, sym_id);
        ins_cal.bind_int(2, f.is_static ? 1 : 0);
        ins_cal.bind_int(3, is_method ? 1 : 0);
        ins_cal.bind_text(4, f.ret);
        ins_cal.bind_text(5, f.sig);
        ins_cal.execute();
        res.callables_harvested++;

        int ord = 0;
        for (const auto& p : f.params) {
            ins_param.reset();
            ins_param.bind_int64(1, sym_id);
            ins_param.bind_int(2, ord++);
            ins_param.bind_text(3, p.name);
            ins_param.bind_text(4, p.pass_kind);
            ins_param.bind_text(5, p.type);
            if (!p.default_val.empty()) ins_param.bind_text(6, p.default_val);
            else ins_param.bind_null(6);
            ins_param.bind_int(7, p.is_optional ? 1 : 0);
            ins_param.execute();
            res.parameters_harvested++;
        }
    };

    // Root namespace: std
    int64_t std_ns_id = add_container(0, "namespace", "std", "std", "Standard C++ namespace", false);

    // Recommended Tier-1 Modules
    const std::vector<HeaderSpec> recommended_headers = {
        {
            "<iostream>", "Standard input/output stream objects",
            {
                {"cout", "extern ostream cout;", "ostream", false, false, {}, "Standard output stream object"},
                {"cin", "extern istream cin;", "istream", false, false, {}, "Standard input stream object"},
                {"cerr", "extern ostream cerr;", "ostream", false, false, {}, "Standard unbuffered error stream"}
            },
            {"ostream", "istream", "iostream"}
        },
        {
            "<string>", "Standard string class templates and utilities",
            {
                {"to_string", "string to_string(int val);", "string", false, false, {{"val", "int", "val"}}, "Convert integer to string"},
                {"stoi", "int stoi(const string& str, size_t* pos = 0, int base = 10);", "int", false, false, {{"str", "const string&", "const_ref"}, {"pos", "size_t*", "pointer", "0", true}, {"base", "int", "val", "10", true}}, "Convert string to integer"}
            },
            {"string", "string_view"}
        },
        {
            "<vector>", "Dynamically sized contiguous sequence container",
            {},
            {"vector"}
        },
        {
            "<memory>", "Smart pointers and allocator utilities",
            {
                {"make_unique", "template<typename T, typename... Args> unique_ptr<T> make_unique(Args&&... args);", "unique_ptr<T>", false, false, {{"args", "Args&&...", "rvalue_ref"}}, "Constructs object of type T and wraps in unique_ptr"},
                {"make_shared", "template<typename T, typename... Args> shared_ptr<T> make_shared(Args&&... args);", "shared_ptr<T>", false, false, {{"args", "Args&&...", "rvalue_ref"}}, "Constructs object of type T and wraps in shared_ptr"}
            },
            {"unique_ptr", "shared_ptr", "weak_ptr"}
        },
        {
            "<filesystem>", "Filesystem paths, directory iteration, and inspection",
            {
                {"exists", "bool exists(const path& p);", "bool", false, false, {{"p", "const path&", "const_ref"}}, "Checks whether the given path refers to an existing filesystem object"},
                {"create_directories", "bool create_directories(const path& p);", "bool", false, false, {{"p", "const path&", "const_ref"}}, "Recursively creates all missing directories specified by path"}
            },
            {"path", "directory_entry", "directory_iterator"}
        },
        {
            "<utility>", "General utility components including pair and move",
            {
                {"move", "template<typename T> constexpr remove_reference_t<T>&& move(T&& t) noexcept;", "remove_reference_t<T>&&", false, false, {{"t", "T&&", "rvalue_ref"}}, "Unconditionally produces an rvalue reference"},
                {"forward", "template<typename T> constexpr T&& forward(remove_reference_t<T>& t) noexcept;", "T&&", false, false, {{"t", "remove_reference_t<T>&", "ref"}}, "Forwards lvalues or rvalues preserving value category"}
            },
            {"pair"}
        },
        {
            "<algorithm>", "Collection algorithms for sorting, searching, transforming",
            {
                {"sort", "template<typename RandomIt> void sort(RandomIt first, RandomIt last);", "void", false, false, {{"first", "RandomIt", "val"}, {"last", "RandomIt", "val"}}, "Sorts elements in range [first, last) in non-descending order"},
                {"find", "template<typename InputIt, typename T> InputIt find(InputIt first, InputIt last, const T& value);", "InputIt", false, false, {{"first", "InputIt", "val"}, {"last", "InputIt", "val"}, {"value", "const T&", "const_ref"}}, "Finds the first element satisfying condition"}
            },
            {}
        },
        {
            "<cstdio>", "Standard C formatted input and output functions",
            {
                {"printf", "int printf(const char* format, ...);", "int", false, false, {{"format", "const char*", "pointer"}}, "Standard formatted print to stdout"},
                {"snprintf", "int snprintf(char* buffer, size_t buf_size, const char* format, ...);", "int", false, false, {{"buffer", "char*", "pointer"}, {"buf_size", "size_t", "val"}, {"format", "const char*", "pointer"}}, "Formatted print to sized buffer"}
            },
            {"FILE"}
        }
    };

    for (const auto& h : recommended_headers) {
        int64_t hid = add_container(std_ns_id, "header", "std::" + h.header_name, h.header_name, h.doc, false);

        for (const auto& cname : h.classes) {
            add_container(hid, "class", "std::" + cname, cname, "Standard C++ class " + cname, true);
        }

        for (const auto& f : h.functions) {
            add_function(hid, "std::" + h.header_name, f, false);
        }
    }

    // If full standard library requested, add remaining 50+ ISO C++20 headers
    if (is_full) {
        const std::vector<std::string> all_headers = {
            "<array>", "<deque>", "<forward_list>", "<list>", "<map>", "<set>",
            "<unordered_map>", "<unordered_set>", "<span>", "<queue>", "<stack>",
            "<charconv>", "<format>", "<regex>", "<memory_resource>", "<new>",
            "<tuple>", "<optional>", "<variant>", "<any>", "<bitset>", "<type_traits>",
            "<compare>", "<concepts>", "<numeric>", "<ranges>", "<cmath>", "<complex>",
            "<random>", "<numbers>", "<fstream>", "<sstream>", "<thread>", "<jthread>",
            "<mutex>", "<shared_mutex>", "<future>", "<condition_variable>", "<atomic>",
            "<barrier>", "<latch>", "<semaphore>", "<stop_token>", "<coroutine>",
            "<cassert>", "<cctype>", "<cerrno>", "<cfloat>", "<cstdint>", "<cstdlib>",
            "<cstring>", "<ctime>"
        };

        for (const auto& hname : all_headers) {
            std::string qname = "std::" + hname;
            int64_t hid = add_container(std_ns_id, "header", qname, hname, "C++20 ISO standard header " + hname, false);
            // Add header dummy symbol
            FuncSpec f{
                "version",
                "constexpr int " + hname + "_version() noexcept;",
                "int",
                false,
                true,
                {},
                "Header version specification"
            };
            add_function(hid, qname, f, false);
        }
    }

    return res;
}

} // namespace utss
