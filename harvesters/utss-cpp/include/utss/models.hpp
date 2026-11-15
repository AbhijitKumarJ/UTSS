#pragma once

#include <string>
#include <optional>
#include <vector>
#include <cstdint>

namespace utss {

struct Environment {
    int64_t env_id{0};
    std::string language;
    std::string runtime_name;
    std::string language_version;
    int version_major{0};
    int version_minor{0};
    int version_micro{0};
    std::string platform_triplet;
    std::string sys_platform;
    std::string executable_path;
};

struct Distribution {
    int64_t dist_id{0};
    int64_t env_id{0};
    int stratum{0};
    std::string dist_name;
    std::string dist_version;
    std::optional<std::string> summary;
};

struct Container {
    int64_t container_id{0};
    int64_t dist_id{0};
    std::optional<int64_t> parent_container_id;
    std::string container_kind;
    std::string qualified_name;
    std::string short_name;
    int requires_import{1};
    std::string visibility{"public"};
    int is_hidden{0};
    std::optional<std::string> physical_path;
    std::optional<std::string> stub_path;
    std::optional<std::string> sha256_hash;
    std::optional<int> start_line;
    std::optional<int> start_col;
    std::optional<int> end_line;
    std::optional<int> end_col;
    std::optional<std::string> docstring;
};

struct Symbol {
    int64_t symbol_id{0};
    int64_t container_id{0};
    std::optional<int64_t> origin_container_id;
    std::string name;
    std::string qualified_name;
    std::string symbol_kind;
    std::string visibility{"public"};
    std::string provenance;
    int is_hidden{0};
    std::optional<int> start_line;
    std::optional<int> start_col;
    std::optional<int> end_line;
    std::optional<int> end_col;
    std::optional<std::string> docstring;
};

struct Callable {
    int64_t symbol_id{0};
    int is_async{0};
    int is_generator{0};
    int is_static{0};
    int is_class_bound{0};
    int has_overloads{0};
    int overload_count{0};
    std::optional<std::string> type_params_json;
    std::optional<std::string> return_type_expr;
    std::optional<std::string> raw_signature;
    std::string signature_source;
};

struct Parameter {
    int64_t param_id{0};
    int64_t callable_symbol_id{0};
    std::optional<int64_t> overload_id;
    int ordinal{0};
    std::string name;
    std::string pass_kind;
    std::optional<std::string> type_expr;
    std::optional<std::string> type_source;
    std::optional<std::string> default_expr;
    int is_optional{0};
};

struct StateMember {
    int64_t symbol_id{0};
    std::optional<std::string> declared_type_expr;
    std::string runtime_type_name;
    int is_constant{0};
    int is_mutable{0};
    std::optional<std::string> literal_value_repr;
    std::string access_mode{"read_write"};
};

struct SymbolAlias {
    int64_t alias_id{0};
    int64_t source_container_id{0};
    std::string exposed_name;
    std::string target_module_name;
    std::string target_symbol_name;
    std::string alias_kind;
    int is_in_dunder_all{0};
};

struct CppContainerFacet {
    int64_t container_id{0};
    std::string item_kind;
    int is_template{0};
    std::optional<std::string> template_params_json;
    std::optional<std::string> base_classes_json;
    int is_final{0};
    int is_abstract{0};
    std::optional<std::string> attributes_json;
};

struct CppSymbolFacet {
    int64_t symbol_id{0};
    std::string member_kind;
    std::string access_specifier{"public"};
    int is_virtual{0};
    int is_pure_virtual{0};
    int is_override{0};
    int is_const{0};
    int is_noexcept{0};
    int is_constexpr{0};
    int is_inline{0};
    int is_static{0};
    std::optional<std::string> pass_by;
    std::optional<std::string> attributes_json;
};

} // namespace utss
