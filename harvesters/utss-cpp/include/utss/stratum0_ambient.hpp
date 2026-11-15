#pragma once

#include "schema.hpp"
#include <cstdint>

namespace utss {

struct Stratum0HarvestResult {
    int64_t env_id{0};
    int64_t dist_id{0};
    int64_t container_id{0};
    int keyword_count{0};
    int primitive_count{0};
    int builtin_count{0};
};

Stratum0HarvestResult harvest_stratum0_ambient(sqlite3* db);

} // namespace utss
