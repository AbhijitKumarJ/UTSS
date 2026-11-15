#include "../include/utss/stratum0_ambient.hpp"
#include <string>
#include <vector>

namespace utss {

Stratum0HarvestResult harvest_stratum0_ambient(sqlite3* db) {
    Stratum0HarvestResult res;

    std::string compiler_name = "g++";
    int major = __GNUC__;
    int minor = __GNUC_MINOR__;
    int patch = __GNUC_PATCHLEVEL__;
    std::string version = std::to_string(major) + "." + std::to_string(minor) + "." + std::to_string(patch);
    std::string triplet = "x86_64-linux-gnu";
    std::string sys_platform = "linux";
    std::string exec_path = "/usr/bin/g++";

    // 1. Insert environment
    Statement ins_env(db, R"SQL(
        INSERT INTO environments (
            language, runtime_name, language_version, version_major, version_minor, version_micro, platform_triplet, sys_platform, executable_path
        ) VALUES ('cpp', ?, 'C++20', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
        DO UPDATE SET captured_at = CURRENT_TIMESTAMP;
    )SQL");
    ins_env.bind_text(1, compiler_name);
    ins_env.bind_int(2, major);
    ins_env.bind_int(3, minor);
    ins_env.bind_int(4, patch);
    ins_env.bind_text(5, triplet);
    ins_env.bind_text(6, sys_platform);
    ins_env.bind_text(7, exec_path);
    ins_env.execute();

    Statement sel_env(db, "SELECT env_id FROM environments WHERE language='cpp' AND runtime_name=? AND language_version='C++20';");
    sel_env.bind_text(1, compiler_name);
    if (sel_env.step()) {
        res.env_id = sel_env.column_int64(0);
    }

    // 2. Insert distribution
    Statement ins_dist(db, R"SQL(
        INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
        VALUES (?, 0, '<ambient>', ?, 'C++20 ISO fundamental types, keywords, built-in constants and macros')
        ON CONFLICT(env_id, stratum, dist_name, dist_version)
        DO UPDATE SET summary = excluded.summary;
    )SQL");
    ins_dist.bind_int64(1, res.env_id);
    ins_dist.bind_text(2, version);
    ins_dist.execute();

    Statement sel_dist(db, "SELECT dist_id FROM distributions WHERE env_id=? AND stratum=0 AND dist_name='<ambient>';");
    sel_dist.bind_int64(1, res.env_id);
    if (sel_dist.step()) {
        res.dist_id = sel_dist.column_int64(0);
    }

    // 3. Insert container
    Statement ins_cont(db, R"SQL(
        INSERT INTO containers (dist_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring)
        VALUES (?, 'ambient_scope', '<ambient>', '<ambient>', 0, 'public', 'C++ root ambient scope')
        ON CONFLICT(dist_id, qualified_name)
        DO UPDATE SET docstring = excluded.docstring;
    )SQL");
    ins_cont.bind_int64(1, res.dist_id);
    ins_cont.execute();

    Statement sel_cont(db, "SELECT container_id FROM containers WHERE dist_id=? AND qualified_name='<ambient>';");
    sel_cont.bind_int64(1, res.dist_id);
    if (sel_cont.step()) {
        res.container_id = sel_cont.column_int64(0);
    }

    Statement ins_cont_facet(db, R"SQL(
        INSERT OR REPLACE INTO cpp_container_facets (container_id, item_kind, is_template, is_final, is_abstract)
        VALUES (?, 'ambient_scope', 0, 0, 0);
    )SQL");
    ins_cont_facet.bind_int64(1, res.container_id);
    ins_cont_facet.execute();

    // Prepare Symbol Insertions
    Statement ins_sym(db, R"SQL(
        INSERT INTO symbols (container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring)
        VALUES (?, ?, ?, ?, 'public', ?, ?)
        ON CONFLICT(container_id, name)
        DO UPDATE SET symbol_kind = excluded.symbol_kind;
    )SQL");

    Statement sel_sym(db, "SELECT symbol_id FROM symbols WHERE container_id=? AND name=?;");

    Statement ins_sym_facet(db, R"SQL(
        INSERT OR REPLACE INTO cpp_symbol_facets (
            symbol_id, member_kind, access_specifier, is_virtual, is_pure_virtual, is_override, is_const, is_noexcept, is_constexpr, is_inline, is_static, attributes_json
        ) VALUES (?, ?, 'public', 0, 0, 0, ?, 0, ?, 0, 0, ?);
    )SQL");

    Statement ins_state(db, R"SQL(
        INSERT OR REPLACE INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    )SQL");

    // A. 97 C++20 Keywords
    const std::vector<std::string> keywords = {
        "alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit",
        "atomic_noexcept", "auto", "bitand", "bitor", "bool", "break", "case", "catch",
        "char", "char8_t", "char16_t", "char32_t", "class", "compl", "concept", "const",
        "consteval", "constexpr", "constinit", "const_cast", "continue", "co_await",
        "co_return", "co_yield", "decltype", "default", "delete", "do", "double",
        "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", "float",
        "for", "friend", "goto", "if", "inline", "int", "long", "mutable", "namespace",
        "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq",
        "private", "protected", "public", "reflexpr", "register", "reinterpret_cast",
        "requires", "return", "short", "signed", "sizeof", "static", "static_assert",
        "static_cast", "struct", "switch", "synchronized", "template", "this",
        "thread_local", "throw", "true", "try", "typedef", "typeid", "typename",
        "union", "unsigned", "using", "virtual", "void", "volatile", "wchar_t",
        "while", "xor", "xor_eq"
    };

    for (const auto& kw : keywords) {
        ins_sym.reset();
        ins_sym.bind_int64(1, res.container_id);
        ins_sym.bind_text(2, kw);
        ins_sym.bind_text(3, "<ambient>::" + kw);
        ins_sym.bind_text(4, "keyword");
        ins_sym.bind_text(5, "ambient_keyword");
        ins_sym.bind_text(6, "C++20 keyword '" + kw + "'");
        ins_sym.execute();

        sel_sym.reset();
        sel_sym.bind_int64(1, res.container_id);
        sel_sym.bind_text(2, kw);
        if (sel_sym.step()) {
            int64_t sym_id = sel_sym.column_int64(0);
            ins_sym_facet.reset();
            ins_sym_facet.bind_int64(1, sym_id);
            ins_sym_facet.bind_text(2, "keyword");
            ins_sym_facet.bind_int(3, 1);
            ins_sym_facet.bind_int(4, 0);
            std::string attr = R"(["keyword"])";
            ins_sym_facet.bind_text(5, attr);
            ins_sym_facet.execute();
        }
        res.keyword_count++;
    }

    // B. 24 Fundamental Primitive Types
    struct PrimInfo {
        std::string name;
        std::string doc;
    };
    const std::vector<PrimInfo> primitives = {
        {"void", "Type with an empty set of values"},
        {"bool", "Boolean type capable of holding true or false"},
        {"char", "Type for character representation (at least 8 bits)"},
        {"signed char", "Explicit signed 8-bit integer type"},
        {"unsigned char", "Explicit unsigned 8-bit integer type"},
        {"char8_t", "Type for UTF-8 character representation"},
        {"char16_t", "Type for UTF-16 character representation"},
        {"char32_t", "Type for UTF-32 character representation"},
        {"wchar_t", "Type for wide character representation"},
        {"short", "Signed integer type at least 16 bits"},
        {"unsigned short", "Unsigned integer type at least 16 bits"},
        {"int", "Basic signed integer type at least 16 bits (commonly 32 bits)"},
        {"unsigned int", "Basic unsigned integer type at least 16 bits (commonly 32 bits)"},
        {"long", "Signed integer type at least 32 bits"},
        {"unsigned long", "Unsigned integer type at least 32 bits"},
        {"long long", "Signed integer type at least 64 bits"},
        {"unsigned long long", "Unsigned integer type at least 64 bits"},
        {"float", "Single precision floating point type"},
        {"double", "Double precision floating point type"},
        {"long double", "Extended precision floating point type"},
        {"std::nullptr_t", "Type of the null pointer literal nullptr"},
        {"size_t", "Unsigned integer type of the result of sizeof operator"},
        {"ptrdiff_t", "Signed integer type of the result of subtracting two pointers"},
        {"intptr_t", "Signed integer type capable of holding a pointer"}
    };

    for (const auto& prim : primitives) {
        ins_sym.reset();
        ins_sym.bind_int64(1, res.container_id);
        ins_sym.bind_text(2, prim.name);
        ins_sym.bind_text(3, "<ambient>::" + prim.name);
        ins_sym.bind_text(4, "primitive_type");
        ins_sym.bind_text(5, "ambient_primitive");
        ins_sym.bind_text(6, prim.doc);
        ins_sym.execute();

        sel_sym.reset();
        sel_sym.bind_int64(1, res.container_id);
        sel_sym.bind_text(2, prim.name);
        if (sel_sym.step()) {
            int64_t sym_id = sel_sym.column_int64(0);
            ins_sym_facet.reset();
            ins_sym_facet.bind_int64(1, sym_id);
            ins_sym_facet.bind_text(2, "primitive");
            ins_sym_facet.bind_int(3, 1);
            ins_sym_facet.bind_int(4, 0);
            std::string attr = R"(["primitive"])";
            ins_sym_facet.bind_text(5, attr);
            ins_sym_facet.execute();
        }
        res.primitive_count++;
    }

    // C. Built-in Constants, Macros & Literals
    struct BuiltinInfo {
        std::string name;
        std::string type;
        std::string val;
        std::string doc;
    };
    const std::vector<BuiltinInfo> builtins = {
        {"nullptr", "std::nullptr_t", "nullptr", "Null pointer constant"},
        {"true", "bool", "1", "Boolean true literal"},
        {"false", "bool", "0", "Boolean false literal"},
        {"NULL", "void*", "0", "Standard C null pointer constant"},
        {"__cplusplus", "long", "202002L", "ISO C++ standard conformance version macro"},
        {"__FILE__", "const char*", "__FILE__", "Current source file path macro"},
        {"__LINE__", "int", "__LINE__", "Current source line number macro"},
        {"__DATE__", "const char*", "\"Mmm dd yyyy\"", "Compilation date macro"},
        {"__TIME__", "const char*", "\"hh:mm:ss\"", "Compilation time macro"},
        {"__func__", "const char*", "__func__", "Current function name string"}
    };

    for (const auto& b : builtins) {
        ins_sym.reset();
        ins_sym.bind_int64(1, res.container_id);
        ins_sym.bind_text(2, b.name);
        ins_sym.bind_text(3, "<ambient>::" + b.name);
        ins_sym.bind_text(4, "constant");
        ins_sym.bind_text(5, "ambient_builtin");
        ins_sym.bind_text(6, b.doc);
        ins_sym.execute();

        sel_sym.reset();
        sel_sym.bind_int64(1, res.container_id);
        sel_sym.bind_text(2, b.name);
        if (sel_sym.step()) {
            int64_t sym_id = sel_sym.column_int64(0);
            ins_sym_facet.reset();
            ins_sym_facet.bind_int64(1, sym_id);
            ins_sym_facet.bind_text(2, "constant");
            ins_sym_facet.bind_int(3, 1);
            ins_sym_facet.bind_int(4, 1);
            std::string attr = R"(["constexpr", "builtin"])";
            ins_sym_facet.bind_text(5, attr);
            ins_sym_facet.execute();

            ins_state.reset();
            ins_state.bind_int64(1, sym_id);
            ins_state.bind_text(2, b.type);
            ins_state.bind_text(3, b.type);
            ins_state.bind_int(4, 1);
            ins_state.bind_int(5, 0);
            ins_state.bind_text(6, b.val);
            ins_state.bind_text(7, "read_only");
            ins_state.execute();
        }
        res.builtin_count++;
    }

    return res;
}

} // namespace utss
