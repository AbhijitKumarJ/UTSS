#include "../include/utss/schema.hpp"
#include <iostream>

namespace utss {

void init_schema(sqlite3* db) {
    char* errmsg = nullptr;
    int rc = sqlite3_exec(db, SCHEMA_SQL, nullptr, nullptr, &errmsg);
    if (rc != SQLITE_OK) {
        std::string err = errmsg ? errmsg : "unknown sqlite error";
        sqlite3_free(errmsg);
        throw std::runtime_error("Failed to initialize UTSS schema: " + err);
    }
}

void reset_schema(sqlite3* db) {
    for (auto it = EXPECTED_TABLES.rbegin(); it != EXPECTED_TABLES.rend(); ++it) {
        std::string drop_sql = "DROP TABLE IF EXISTS " + *it + ";";
        char* errmsg = nullptr;
        int rc = sqlite3_exec(db, drop_sql.c_str(), nullptr, nullptr, &errmsg);
        if (rc != SQLITE_OK) {
            std::string err = errmsg ? errmsg : "unknown sqlite error";
            sqlite3_free(errmsg);
            throw std::runtime_error("Failed to drop table " + *it + ": " + err);
        }
    }
    init_schema(db);
}

Database::Database(const std::string& path) {
    int rc = sqlite3_open(path.c_str(), &db_);
    if (rc != SQLITE_OK) {
        std::string err = db_ ? sqlite3_errmsg(db_) : "Failed to allocate sqlite3 handle";
        if (db_) sqlite3_close(db_);
        throw std::runtime_error("Failed to open database '" + path + "': " + err);
    }
    exec("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;");
}

Database::~Database() {
    if (db_) {
        sqlite3_close(db_);
        db_ = nullptr;
    }
}

void Database::exec(const std::string& sql) {
    char* errmsg = nullptr;
    int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &errmsg);
    if (rc != SQLITE_OK) {
        std::string err = errmsg ? errmsg : "unknown error";
        sqlite3_free(errmsg);
        throw std::runtime_error("Database::exec failed: " + err + " for SQL: " + sql);
    }
}

int64_t Database::last_insert_rowid() const {
    return sqlite3_last_insert_rowid(db_);
}

Statement::Statement(sqlite3* db, const std::string& sql) {
    int rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt_, nullptr);
    if (rc != SQLITE_OK) {
        throw std::runtime_error("Statement prepare failed: " + std::string(sqlite3_errmsg(db)) + " for SQL: " + sql);
    }
}

Statement::~Statement() {
    if (stmt_) {
        sqlite3_finalize(stmt_);
        stmt_ = nullptr;
    }
}

void Statement::reset() {
    sqlite3_reset(stmt_);
    sqlite3_clear_bindings(stmt_);
}

void Statement::bind_null(int idx) {
    sqlite3_bind_null(stmt_, idx);
}

void Statement::bind_int(int idx, int val) {
    sqlite3_bind_int(stmt_, idx, val);
}

void Statement::bind_int64(int idx, int64_t val) {
    sqlite3_bind_int64(stmt_, idx, val);
}

void Statement::bind_text(int idx, const std::string& val) {
    sqlite3_bind_text(stmt_, idx, val.c_str(), -1, SQLITE_TRANSIENT);
}

void Statement::bind_opt_text(int idx, const std::string* val) {
    if (val) {
        sqlite3_bind_text(stmt_, idx, val->c_str(), -1, SQLITE_TRANSIENT);
    } else {
        sqlite3_bind_null(stmt_, idx);
    }
}

bool Statement::step() {
    int rc = sqlite3_step(stmt_);
    if (rc == SQLITE_ROW) return true;
    if (rc == SQLITE_DONE) return false;
    throw std::runtime_error("Statement step failed: " + std::to_string(rc));
}

void Statement::execute() {
    int rc = sqlite3_step(stmt_);
    if (rc != SQLITE_DONE && rc != SQLITE_ROW) {
        throw std::runtime_error("Statement execute failed: " + std::to_string(rc));
    }
}

int Statement::column_int(int col) const {
    return sqlite3_column_int(stmt_, col);
}

int64_t Statement::column_int64(int col) const {
    return sqlite3_column_int64(stmt_, col);
}

std::string Statement::column_text(int col) const {
    const unsigned char* txt = sqlite3_column_text(stmt_, col);
    return txt ? reinterpret_cast<const char*>(txt) : "";
}

bool Statement::column_is_null(int col) const {
    return sqlite3_column_type(stmt_, col) == SQLITE_NULL;
}

} // namespace utss
