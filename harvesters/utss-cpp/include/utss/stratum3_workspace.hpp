#pragma once

#include "schema.hpp"
#include <string>
#include <map>
#include <cstdint>

namespace utss {

struct WorkspaceHarvestResult {
    int64_t dist_id{0};
    int files_processed{0};
    int containers_harvested{0};
    int symbols_harvested{0};
    int callables_harvested{0};
    int parameters_harvested{0};
    int state_members_harvested{0};
    int aliases_harvested{0};
};

extern const std::map<std::string, std::string> EMBEDDED_DEMO_WORKSPACE;

class WorkspaceAstCataloger {
public:
    WorkspaceAstCataloger(sqlite3* db, int64_t env_id);

    WorkspaceHarvestResult harvest_embedded_demo();
    WorkspaceHarvestResult harvest_directory(const std::string& dir_path, const std::string& dist_name = "workspace", const std::string& dist_version = "0.1.0");

private:
    WorkspaceHarvestResult harvest_files(int64_t dist_id, const std::map<std::string, std::string>& files);
    int64_t ensure_distribution(const std::string& dist_name, const std::string& dist_version, const std::string& summary);

    sqlite3* db_;
    int64_t env_id_;
};

} // namespace utss
