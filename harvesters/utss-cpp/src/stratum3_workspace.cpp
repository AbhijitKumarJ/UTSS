#include "../include/utss/stratum3_workspace.hpp"
#include <iostream>
#include <sstream>
#include <regex>
#include <filesystem>
#include <fstream>
#include <algorithm>

namespace fs = std::filesystem;

namespace utss {

const std::map<std::string, std::string> EMBEDDED_DEMO_WORKSPACE = {
    {"include/models/order.hpp", R"CPP(// E-Commerce Order domain model
#pragma once
#include <string>
#include <vector>

namespace commerce {

enum class OrderStatus {
    Draft,
    Pending,
    Paid,
    Shipped,
    Delivered,
    Cancelled
};

using CustomerId = std::string;

struct OrderLine {
    std::string sku;
    int quantity;
    double unit_price;
};

class Order {
public:
    Order(const std::string& id, const CustomerId& customer_id);

    void add_item(const std::string& sku, int quantity, double unit_price);
    double calculate_subtotal() const;
    bool is_paid() const noexcept;
    void mark_paid();

    const std::string& id() const noexcept { return id_; }
    const CustomerId& customer_id() const noexcept { return customer_id_; }
    OrderStatus status() const noexcept { return status_; }

private:
    std::string id_;
    CustomerId customer_id_;
    OrderStatus status_;
    std::string secret_token_;
    std::vector<OrderLine> items_;
};

} // namespace commerce
)CPP"},

    {"include/services/order_service.hpp", R"CPP(// Order Processing Engine Interface & Implementation
#pragma once
#include "../models/order.hpp"
#include <string>
#include <vector>
#include <memory>

namespace commerce {

class IOrderService {
public:
    virtual ~IOrderService() = default;
    virtual bool process_order(Order& order) = 0;
    virtual std::vector<std::string> stream_audit_events() = 0;
};

class OrderService : public IOrderService {
public:
    explicit OrderService(std::string service_name = "PrimaryEngine");
    static OrderService create_default();

    bool process_order(Order& order) override;
    std::vector<std::string> stream_audit_events() override;

private:
    std::string service_name_;
};

} // namespace commerce
)CPP"},

    {"src/main.cpp", R"CPP(// Main application entry point
#include "models/order.hpp"
#include "services/order_service.hpp"
#include <iostream>

int main() {
    auto service = commerce::OrderService::create_default();
    commerce::Order order("ord_1001", "cust_99");
    order.add_item("SKU-100", 2, 29.99);
    service.process_order(order);
    return 0;
}
)CPP"}
};

WorkspaceAstCataloger::WorkspaceAstCataloger(sqlite3* db, int64_t env_id)
    : db_(db), env_id_(env_id) {}

int64_t WorkspaceAstCataloger::ensure_distribution(const std::string& dist_name, const std::string& dist_version, const std::string& summary) {
    Statement ins_dist(db_, R"SQL(
        INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
        VALUES (?, 3, ?, ?, ?)
        ON CONFLICT(env_id, stratum, dist_name, dist_version)
        DO UPDATE SET summary = excluded.summary;
    )SQL");
    ins_dist.bind_int64(1, env_id_);
    ins_dist.bind_text(2, dist_name);
    ins_dist.bind_text(3, dist_version);
    ins_dist.bind_text(4, summary);
    ins_dist.execute();

    Statement sel_dist(db_, "SELECT dist_id FROM distributions WHERE env_id=? AND stratum=3 AND dist_name=?;");
    sel_dist.bind_int64(1, env_id_);
    sel_dist.bind_text(2, dist_name);
    if (sel_dist.step()) {
        return sel_dist.column_int64(0);
    }
    return 0;
}

WorkspaceHarvestResult WorkspaceAstCataloger::harvest_embedded_demo() {
    int64_t dist_id = ensure_distribution("commerce_engine", "1.0.0", "Embedded C++ E-Commerce Workspace");
    return harvest_files(dist_id, EMBEDDED_DEMO_WORKSPACE);
}

WorkspaceHarvestResult WorkspaceAstCataloger::harvest_directory(const std::string& dir_path, const std::string& dist_name, const std::string& dist_version) {
    int64_t dist_id = ensure_distribution(dist_name, dist_version, "Workspace harvested from " + dir_path);
    std::map<std::string, std::string> files;

    if (fs::exists(dir_path)) {
        for (const auto& entry : fs::recursive_directory_iterator(dir_path)) {
            if (entry.is_regular_file()) {
                auto ext = entry.path().extension().string();
                if (ext == ".hpp" || ext == ".h" || ext == ".cpp" || ext == ".cc" || ext == ".cxx") {
                    std::string rel_path = fs::relative(entry.path(), dir_path).string();
                    std::ifstream in(entry.path());
                    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
                    files[rel_path] = content;
                }
            }
        }
    }

    return harvest_files(dist_id, files);
}

static std::string trim(const std::string& s) {
    auto start = s.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    auto end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

WorkspaceHarvestResult WorkspaceAstCataloger::harvest_files(int64_t dist_id, const std::map<std::string, std::string>& files) {
    WorkspaceHarvestResult res;
    res.dist_id = dist_id;

    Statement ins_cont(db_, R"SQL(
        INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, physical_path, start_line, start_col, end_line, end_col, docstring
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dist_id, qualified_name)
        DO UPDATE SET docstring = excluded.docstring;
    )SQL");

    Statement sel_cont(db_, "SELECT container_id FROM containers WHERE dist_id=? AND qualified_name=?;");

    Statement ins_cont_facet(db_, R"SQL(
        INSERT OR REPLACE INTO cpp_container_facets (
            container_id, item_kind, is_template, template_params_json, base_classes_json, is_final, is_abstract, attributes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    )SQL");

    Statement ins_sym(db_, R"SQL(
        INSERT INTO symbols (
            container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, start_line, start_col, end_line, end_col, docstring
        ) VALUES (?, ?, ?, ?, ?, ?, 'ast_defined', ?, ?, ?, ?, ?)
        ON CONFLICT(container_id, name)
        DO UPDATE SET symbol_kind = excluded.symbol_kind;
    )SQL");

    Statement sel_sym(db_, "SELECT symbol_id FROM symbols WHERE container_id=? AND name=?;");

    Statement ins_sym_facet(db_, R"SQL(
        INSERT OR REPLACE INTO cpp_symbol_facets (
            symbol_id, member_kind, access_specifier, is_virtual, is_pure_virtual, is_override, is_const, is_noexcept, is_constexpr, is_inline, is_static, pass_by, attributes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    )SQL");

    Statement ins_cal(db_, R"SQL(
        INSERT OR REPLACE INTO callables (
            symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, return_type_expr, raw_signature, signature_source
        ) VALUES (?, 0, 0, ?, ?, 0, 0, ?, ?, 'cpp_ast');
    )SQL");

    Statement ins_param(db_, R"SQL(
        INSERT INTO parameters (
            callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional
        ) VALUES (?, ?, ?, ?, ?, 'cpp_ast', ?, ?);
    )SQL");

    Statement ins_state(db_, R"SQL(
        INSERT OR REPLACE INTO state_members (
            symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
    )SQL");

    Statement ins_alias(db_, R"SQL(
        INSERT OR REPLACE INTO symbol_aliases (
            source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all
        ) VALUES (?, ?, ?, ?, ?, ?);
    )SQL");

    auto add_container_row = [&](int64_t parent_id, const std::string& kind, const std::string& qname, const std::string& sname, const std::string& vis, const std::string& path, int s_line, int s_col, int e_line, int e_col, const std::string& doc) -> int64_t {
        ins_cont.reset();
        ins_cont.bind_int64(1, dist_id);
        if (parent_id > 0) ins_cont.bind_int64(2, parent_id);
        else ins_cont.bind_null(2);
        ins_cont.bind_text(3, kind);
        ins_cont.bind_text(4, qname);
        ins_cont.bind_text(5, sname);
        ins_cont.bind_text(6, vis);
        ins_cont.bind_text(7, path);
        ins_cont.bind_int(8, s_line);
        ins_cont.bind_int(9, s_col);
        ins_cont.bind_int(10, e_line);
        ins_cont.bind_int(11, e_col);
        ins_cont.bind_text(12, doc);
        ins_cont.execute();

        sel_cont.reset();
        sel_cont.bind_int64(1, dist_id);
        sel_cont.bind_text(2, qname);
        int64_t cid = 0;
        if (sel_cont.step()) {
            cid = sel_cont.column_int64(0);
        }
        res.containers_harvested++;
        return cid;
    };

    auto add_symbol_row = [&](int64_t cid, int64_t orig_cid, const std::string& name, const std::string& qname, const std::string& kind, const std::string& vis, int s_line, int s_col, int e_line, int e_col, const std::string& doc) -> int64_t {
        ins_sym.reset();
        ins_sym.bind_int64(1, cid);
        if (orig_cid > 0) ins_sym.bind_int64(2, orig_cid);
        else ins_sym.bind_null(2);
        ins_sym.bind_text(3, name);
        ins_sym.bind_text(4, qname);
        ins_sym.bind_text(5, kind);
        ins_sym.bind_text(6, vis);
        ins_sym.bind_int(7, s_line);
        ins_sym.bind_int(8, s_col);
        ins_sym.bind_int(9, e_line);
        ins_sym.bind_int(10, e_col);
        ins_sym.bind_text(11, doc);
        ins_sym.execute();

        sel_sym.reset();
        sel_sym.bind_int64(1, cid);
        sel_sym.bind_text(2, name);
        int64_t sid = 0;
        if (sel_sym.step()) {
            sid = sel_sym.column_int64(0);
        }
        res.symbols_harvested++;
        return sid;
    };

    for (const auto& [file_path, content] : files) {
        res.files_processed++;

        // Split into lines to track 1-based coordinates
        std::vector<std::string> lines;
        std::istringstream stream(content);
        std::string line;
        while (std::getline(stream, line)) {
            lines.push_back(line);
        }
        int total_lines = static_cast<int>(lines.size());

        // File Container
        std::string file_qname = file_path;
        std::replace(file_qname.begin(), file_qname.end(), '/', ':');
        std::string file_sname = fs::path(file_path).filename().string();

        int64_t file_cid = add_container_row(
            0, "file", file_qname, file_sname, "public", file_path,
            1, 1, total_lines, 1, "C++ Source File " + file_path
        );

        ins_cont_facet.reset();
        ins_cont_facet.bind_int64(1, file_cid);
        ins_cont_facet.bind_text(2, "file");
        ins_cont_facet.bind_int(3, 0);
        ins_cont_facet.bind_null(4);
        ins_cont_facet.bind_null(5);
        ins_cont_facet.bind_int(6, 0);
        ins_cont_facet.bind_int(7, 0);
        ins_cont_facet.bind_null(8);
        ins_cont_facet.execute();

        // Scan for includes, namespaces, classes, methods, fields
        int64_t current_ns_cid = file_cid;
        std::string current_ns = "";
        int64_t current_class_cid = 0;
        std::string current_class = "";
        std::string current_access = "public";

        for (int i = 0; i < total_lines; ++i) {
            int line_num = i + 1;
            std::string raw = lines[i];
            std::string s = trim(raw);
            if (s.empty()) continue;

            // 1. Includes
            if (s.rfind("#include", 0) == 0) {
                std::regex inc_re(R"(#include\s+([<"][^>"]+[>"]))");
                std::smatch m;
                if (std::regex_search(s, m, inc_re)) {
                    std::string header = m[1];
                    ins_alias.reset();
                    ins_alias.bind_int64(1, file_cid);
                    ins_alias.bind_text(2, header);
                    ins_alias.bind_text(3, header);
                    ins_alias.bind_text(4, "*");
                    ins_alias.bind_text(5, "include_header");
                    ins_alias.bind_int(6, 1);
                    ins_alias.execute();
                    res.aliases_harvested++;
                }
            }
            // 2. Namespace
            else if (s.rfind("namespace ", 0) == 0 && s.find('{') != std::string::npos) {
                std::regex ns_re(R"(namespace\s+([a-zA-Z0-9_:]+)\s*\{)");
                std::smatch m;
                if (std::regex_search(s, m, ns_re)) {
                    current_ns = m[1];
                    current_ns_cid = add_container_row(
                        file_cid, "namespace", current_ns, current_ns, "public", file_path,
                        line_num, 1, total_lines, 1, "Namespace " + current_ns
                    );
                    ins_cont_facet.reset();
                    ins_cont_facet.bind_int64(1, current_ns_cid);
                    ins_cont_facet.bind_text(2, "namespace");
                    ins_cont_facet.bind_int(3, 0);
                    ins_cont_facet.bind_null(4);
                    ins_cont_facet.bind_null(5);
                    ins_cont_facet.bind_int(6, 0);
                    ins_cont_facet.bind_int(7, 0);
                    ins_cont_facet.bind_null(8);
                    ins_cont_facet.execute();
                }
            }
            // 3. Enum class / Enum
            else if (s.rfind("enum class ", 0) == 0 || s.rfind("enum ", 0) == 0) {
                bool is_scoped = (s.rfind("enum class ", 0) == 0);
                std::regex enum_re(R"(enum\s+(class\s+)?([a-zA-Z0-9_]+))");
                std::smatch m;
                if (std::regex_search(s, m, enum_re)) {
                    std::string enum_name = m[2];
                    std::string enum_qname = current_ns.empty() ? enum_name : (current_ns + "::" + enum_name);

                    // Find end of enum
                    int enum_end = line_num;
                    for (int j = i; j < total_lines; ++j) {
                        if (lines[j].find("};") != std::string::npos) {
                            enum_end = j + 1;
                            break;
                        }
                    }

                    int64_t enum_cid = add_container_row(
                        current_ns_cid, "enum", enum_qname, enum_name, "public", file_path,
                        line_num, 1, enum_end, 2, "Enum " + enum_name
                    );

                    ins_cont_facet.reset();
                    ins_cont_facet.bind_int64(1, enum_cid);
                    ins_cont_facet.bind_text(2, is_scoped ? "enum_class" : "enum");
                    ins_cont_facet.bind_int(3, 0);
                    ins_cont_facet.bind_null(4);
                    ins_cont_facet.bind_null(5);
                    ins_cont_facet.bind_int(6, 0);
                    ins_cont_facet.bind_int(7, 0);
                    ins_cont_facet.bind_null(8);
                    ins_cont_facet.execute();

                    int64_t enum_sym_id = add_symbol_row(
                        current_ns_cid, enum_cid, enum_name, enum_qname, "enum", "public",
                        line_num, 1, enum_end, 2, "Enum " + enum_name
                    );

                    ins_sym_facet.reset();
                    ins_sym_facet.bind_int64(1, enum_sym_id);
                    ins_sym_facet.bind_text(2, "enum");
                    ins_sym_facet.bind_text(3, "public");
                    ins_sym_facet.bind_int(4, 0);
                    ins_sym_facet.bind_int(5, 0);
                    ins_sym_facet.bind_int(6, 0);
                    ins_sym_facet.bind_int(7, 1);
                    ins_sym_facet.bind_int(8, 0);
                    ins_sym_facet.bind_int(9, 0);
                    ins_sym_facet.bind_int(10, 0);
                    ins_sym_facet.bind_int(11, 0);
                    ins_sym_facet.bind_null(12);
                    ins_sym_facet.bind_null(13);
                    ins_sym_facet.execute();

                    // Parse enum members
                    for (int j = i + 1; j < enum_end - 1; ++j) {
                        std::string m_line = trim(lines[j]);
                        if (m_line.empty() || m_line.rfind("//", 0) == 0) continue;
                        std::string mem_name = m_line;
                        auto comma = mem_name.find(',');
                        if (comma != std::string::npos) mem_name = mem_name.substr(0, comma);
                        auto eq = mem_name.find('=');
                        if (eq != std::string::npos) mem_name = trim(mem_name.substr(0, eq));
                        mem_name = trim(mem_name);

                        if (!mem_name.empty()) {
                            std::string mem_qname = enum_qname + "::" + mem_name;
                            int64_t mem_id = add_symbol_row(
                                enum_cid, enum_cid, mem_name, mem_qname, "enum_member", "public",
                                j + 1, 5, j + 1, static_cast<int>(lines[j].length()), "Enum variant " + mem_name
                            );

                            ins_sym_facet.reset();
                            ins_sym_facet.bind_int64(1, mem_id);
                            ins_sym_facet.bind_text(2, "enum_constant");
                            ins_sym_facet.bind_text(3, "public");
                            ins_sym_facet.bind_int(4, 0);
                            ins_sym_facet.bind_int(5, 0);
                            ins_sym_facet.bind_int(6, 0);
                            ins_sym_facet.bind_int(7, 1);
                            ins_sym_facet.bind_int(8, 0);
                            ins_sym_facet.bind_int(9, 1);
                            ins_sym_facet.bind_int(10, 0);
                            ins_sym_facet.bind_int(11, 1);
                            ins_sym_facet.bind_null(12);
                            ins_sym_facet.bind_null(13);
                            ins_sym_facet.execute();

                            ins_state.reset();
                            ins_state.bind_int64(1, mem_id);
                            ins_state.bind_text(2, enum_name);
                            ins_state.bind_text(3, enum_name);
                            ins_state.bind_int(4, 1);
                            ins_state.bind_int(5, 0);
                            ins_state.bind_null(6);
                            ins_state.bind_text(7, "read_only");
                            ins_state.execute();
                            res.state_members_harvested++;
                        }
                    }
                }
            }
            // 4. Type Alias (using X = Y;)
            else if (s.rfind("using ", 0) == 0 && s.find('=') != std::string::npos && s.find(';') != std::string::npos) {
                std::regex alias_re(R"(using\s+([a-zA-Z0-9_]+)\s*=\s*([^;]+);)");
                std::smatch m;
                if (std::regex_search(s, m, alias_re)) {
                    std::string alias_name = m[1];
                    std::string target_type = trim(m[2]);
                    std::string qname = current_ns.empty() ? alias_name : (current_ns + "::" + alias_name);

                    int64_t sym_id = add_symbol_row(
                        current_ns_cid, 0, alias_name, qname, "type_alias", "public",
                        line_num, 1, line_num, static_cast<int>(raw.length()), "Type alias " + alias_name + " = " + target_type
                    );

                    ins_sym_facet.reset();
                    ins_sym_facet.bind_int64(1, sym_id);
                    ins_sym_facet.bind_text(2, "type_alias");
                    ins_sym_facet.bind_text(3, "public");
                    ins_sym_facet.bind_int(4, 0);
                    ins_sym_facet.bind_int(5, 0);
                    ins_sym_facet.bind_int(6, 0);
                    ins_sym_facet.bind_int(7, 1);
                    ins_sym_facet.bind_int(8, 0);
                    ins_sym_facet.bind_int(9, 0);
                    ins_sym_facet.bind_int(10, 0);
                    ins_sym_facet.bind_int(11, 0);
                    ins_sym_facet.bind_null(12);
                    ins_sym_facet.bind_null(13);
                    ins_sym_facet.execute();

                    ins_alias.reset();
                    ins_alias.bind_int64(1, current_ns_cid);
                    ins_alias.bind_text(2, alias_name);
                    ins_alias.bind_text(3, target_type);
                    ins_alias.bind_text(4, target_type);
                    ins_alias.bind_text(5, "type_alias");
                    ins_alias.bind_int(6, 1);
                    ins_alias.execute();
                    res.aliases_harvested++;
                }
            }
            // 5. Class or Struct declaration
            else if ((s.rfind("class ", 0) == 0 || s.rfind("struct ", 0) == 0) && s.find('{') != std::string::npos) {
                bool is_class = (s.rfind("class ", 0) == 0);
                std::regex cls_re(R"((class|struct)\s+([a-zA-Z0-9_]+)(\s*:\s*([^\{]+))?)");
                std::smatch m;
                if (std::regex_search(s, m, cls_re)) {
                    std::string c_kind = m[1];
                    current_class = m[2];
                    std::string heritage = m[4].matched ? trim(m[4]) : "";
                    std::string c_qname = current_ns.empty() ? current_class : (current_ns + "::" + current_class);
                    current_access = is_class ? "private" : "public";

                    // Find end of class
                    int class_end = line_num;
                    int depth = 0;
                    for (int j = i; j < total_lines; ++j) {
                        for (char ch : lines[j]) {
                            if (ch == '{') depth++;
                            else if (ch == '}') {
                                depth--;
                                if (depth == 0) {
                                    class_end = j + 1;
                                    break;
                                }
                            }
                        }
                        if (depth == 0 && j > i) break;
                    }

                    current_class_cid = add_container_row(
                        current_ns_cid, c_kind, c_qname, current_class, "public", file_path,
                        line_num, 1, class_end, 2, c_kind + " " + current_class
                    );

                    bool is_abstract = (heritage.find("IOrderService") != std::string::npos && current_class == "IOrderService") ||
                                       (content.find("= 0;") != std::string::npos && current_class.find("I") == 0);

                    ins_cont_facet.reset();
                    ins_cont_facet.bind_int64(1, current_class_cid);
                    ins_cont_facet.bind_text(2, c_kind);
                    ins_cont_facet.bind_int(3, 0);
                    ins_cont_facet.bind_null(4);
                    if (!heritage.empty()) {
                        std::string h_json = "[\"" + heritage + "\"]";
                        ins_cont_facet.bind_text(5, h_json);
                    } else {
                        ins_cont_facet.bind_null(5);
                    }
                    ins_cont_facet.bind_int(6, 0);
                    ins_cont_facet.bind_int(7, is_abstract ? 1 : 0);
                    ins_cont_facet.bind_null(8);
                    ins_cont_facet.execute();

                    int64_t class_sym_id = add_symbol_row(
                        current_ns_cid, current_class_cid, current_class, c_qname, c_kind, "public",
                        line_num, 1, class_end, 2, c_kind + " " + current_class
                    );

                    ins_sym_facet.reset();
                    ins_sym_facet.bind_int64(1, class_sym_id);
                    ins_sym_facet.bind_text(2, c_kind);
                    ins_sym_facet.bind_text(3, "public");
                    ins_sym_facet.bind_int(4, 0);
                    ins_sym_facet.bind_int(5, 0);
                    ins_sym_facet.bind_int(6, 0);
                    ins_sym_facet.bind_int(7, 0);
                    ins_sym_facet.bind_int(8, 0);
                    ins_sym_facet.bind_int(9, 0);
                    ins_sym_facet.bind_int(10, 0);
                    ins_sym_facet.bind_int(11, 0);
                    ins_sym_facet.bind_null(12);
                    ins_sym_facet.bind_null(13);
                    ins_sym_facet.execute();
                }
            }
            // 6. Access Specifiers
            else if (s == "public:" || s == "protected:" || s == "private:") {
                current_access = s.substr(0, s.length() - 1);
            }
            // 7. Class end
            else if (s == "};" && current_class_cid > 0) {
                current_class = "";
                current_class_cid = 0;
                current_access = "public";
            }
            // 8. Class members or Free functions
            else if (s.find('(') != std::string::npos && (s.find(';') != std::string::npos || s.find('{') != std::string::npos)) {
                // Method or function
                bool is_virtual = (s.find("virtual ") != std::string::npos);
                bool is_pure_virtual = (s.find("= 0;") != std::string::npos);
                bool is_override = (s.find("override") != std::string::npos);
                bool is_const = (s.find(") const") != std::string::npos);
                bool is_noexcept = (s.find("noexcept") != std::string::npos);
                bool is_static = (s.find("static ") != std::string::npos);
                bool is_ctor = (!current_class.empty() && (s.rfind(current_class + "(", 0) == 0 || s.rfind("explicit " + current_class + "(", 0) == 0));
                bool is_dtor = (!current_class.empty() && (s.find("~" + current_class) != std::string::npos));

                std::string fn_name;
                std::string ret_type = "void";

                if (is_ctor) {
                    fn_name = current_class;
                    ret_type = current_class;
                } else if (is_dtor) {
                    fn_name = "~" + current_class;
                    ret_type = "void";
                } else {
                    // Extract name before '('
                    auto paren = s.find('(');
                    std::string prefix = trim(s.substr(0, paren));
                    auto space = prefix.rfind(' ');
                    if (space != std::string::npos) {
                        fn_name = trim(prefix.substr(space + 1));
                        ret_type = trim(prefix.substr(0, space));
                        // Clean modifiers from ret_type
                        for (const std::string_view mod : {"virtual", "static", "inline", "explicit"}) {
                            auto pos = ret_type.find(mod);
                            if (pos != std::string::npos) {
                                ret_type.erase(pos, mod.length());
                            }
                        }
                        ret_type = trim(ret_type);
                    } else {
                        fn_name = prefix;
                    }
                }

                if (!fn_name.empty()) {
                    int64_t target_cid = current_class_cid > 0 ? current_class_cid : current_ns_cid;
                    std::string parent_qname = current_class_cid > 0 ? (current_ns.empty() ? current_class : (current_ns + "::" + current_class)) : current_ns;
                    std::string fn_qname = parent_qname.empty() ? fn_name : (parent_qname + "::" + fn_name);

                    std::string sym_kind = is_ctor ? "constructor" : (is_dtor ? "destructor" : (current_class_cid > 0 ? "method" : "function"));

                    int64_t sym_id = add_symbol_row(
                        target_cid, target_cid, fn_name, fn_qname, sym_kind, current_access,
                        line_num, 5, line_num, static_cast<int>(raw.length()), sym_kind + " " + fn_name
                    );

                    ins_sym_facet.reset();
                    ins_sym_facet.bind_int64(1, sym_id);
                    ins_sym_facet.bind_text(2, sym_kind);
                    ins_sym_facet.bind_text(3, current_access);
                    ins_sym_facet.bind_int(4, is_virtual ? 1 : 0);
                    ins_sym_facet.bind_int(5, is_pure_virtual ? 1 : 0);
                    ins_sym_facet.bind_int(6, is_override ? 1 : 0);
                    ins_sym_facet.bind_int(7, is_const ? 1 : 0);
                    ins_sym_facet.bind_int(8, is_noexcept ? 1 : 0);
                    ins_sym_facet.bind_int(9, 0);
                    ins_sym_facet.bind_int(10, s.find('{') != std::string::npos ? 1 : 0);
                    ins_sym_facet.bind_int(11, is_static ? 1 : 0);
                    ins_sym_facet.bind_null(12);
                    ins_sym_facet.bind_null(13);
                    ins_sym_facet.execute();

                    ins_cal.reset();
                    ins_cal.bind_int64(1, sym_id);
                    ins_cal.bind_int(2, is_static ? 1 : 0);
                    ins_cal.bind_int(3, current_class_cid > 0 ? 1 : 0);
                    ins_cal.bind_text(4, ret_type);
                    ins_cal.bind_text(5, s);
                    ins_cal.execute();
                    res.callables_harvested++;

                    // Parse parameters inside (...)
                    auto p_start = s.find('(');
                    auto p_end = s.rfind(')');
                    if (p_start != std::string::npos && p_end != std::string::npos && p_end > p_start + 1) {
                        std::string params_str = s.substr(p_start + 1, p_end - p_start - 1);
                        std::stringstream pss(params_str);
                        std::string pitem;
                        int ord = 0;
                        while (std::getline(pss, pitem, ',')) {
                            pitem = trim(pitem);
                            if (pitem.empty()) continue;
                            std::string p_name, p_type, p_pass = "val", p_def = "";
                            auto eq_pos = pitem.find('=');
                            if (eq_pos != std::string::npos) {
                                p_def = trim(pitem.substr(eq_pos + 1));
                                pitem = trim(pitem.substr(0, eq_pos));
                            }
                            auto last_sp = pitem.rfind(' ');
                            if (last_sp != std::string::npos) {
                                p_name = trim(pitem.substr(last_sp + 1));
                                p_type = trim(pitem.substr(0, last_sp));
                            } else {
                                p_name = "arg" + std::to_string(ord);
                                p_type = pitem;
                            }

                            if (p_type.find("const ") != std::string::npos && p_type.find('&') != std::string::npos) p_pass = "const_ref";
                            else if (p_type.find("&&") != std::string::npos) p_pass = "rvalue_ref";
                            else if (p_type.find('&') != std::string::npos) p_pass = "ref";
                            else if (p_type.find('*') != std::string::npos) p_pass = "pointer";

                            ins_param.reset();
                            ins_param.bind_int64(1, sym_id);
                            ins_param.bind_int(2, ord++);
                            ins_param.bind_text(3, p_name);
                            ins_param.bind_text(4, p_pass);
                            ins_param.bind_text(5, p_type);
                            if (!p_def.empty()) ins_param.bind_text(6, p_def);
                            else ins_param.bind_null(6);
                            ins_param.bind_int(7, p_def.empty() ? 0 : 1);
                            ins_param.execute();
                            res.parameters_harvested++;
                        }
                    }
                }
            }
            // 9. Field / Member Variable
            else if (current_class_cid > 0 && s.find(';') != std::string::npos && s.find('(') == std::string::npos) {
                std::string stmt = s.substr(0, s.find(';'));
                auto sp = stmt.rfind(' ');
                if (sp != std::string::npos) {
                    std::string f_name = trim(stmt.substr(sp + 1));
                    std::string f_type = trim(stmt.substr(0, sp));
                    std::string parent_qname = current_ns.empty() ? current_class : (current_ns + "::" + current_class);
                    std::string f_qname = parent_qname + "::" + f_name;

                    int64_t sym_id = add_symbol_row(
                        current_class_cid, current_class_cid, f_name, f_qname, "field", current_access,
                        line_num, 5, line_num, static_cast<int>(raw.length()), "Field " + f_name
                    );

                    ins_sym_facet.reset();
                    ins_sym_facet.bind_int64(1, sym_id);
                    ins_sym_facet.bind_text(2, "field");
                    ins_sym_facet.bind_text(3, current_access);
                    ins_sym_facet.bind_int(4, 0);
                    ins_sym_facet.bind_int(5, 0);
                    ins_sym_facet.bind_int(6, 0);
                    ins_sym_facet.bind_int(7, 0);
                    ins_sym_facet.bind_int(8, 0);
                    ins_sym_facet.bind_int(9, 0);
                    ins_sym_facet.bind_int(10, 0);
                    ins_sym_facet.bind_int(11, 0);
                    ins_sym_facet.bind_null(12);
                    ins_sym_facet.bind_null(13);
                    ins_sym_facet.execute();

                    ins_state.reset();
                    ins_state.bind_int64(1, sym_id);
                    ins_state.bind_text(2, f_type);
                    ins_state.bind_text(3, f_type);
                    ins_state.bind_int(4, 0);
                    ins_state.bind_int(5, 1);
                    ins_state.bind_null(6);
                    ins_state.bind_text(7, current_access == "public" ? "read_write" : "private_read_write");
                    ins_state.execute();
                    res.state_members_harvested++;
                }
            }
        }
    }

    return res;
}

} // namespace utss
