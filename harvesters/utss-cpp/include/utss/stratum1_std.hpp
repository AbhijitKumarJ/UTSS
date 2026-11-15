#pragma once

#include "schema.hpp"
#include <cstdint>

namespace utss {

struct Stratum1HarvestResult {
    int64_t dist_id{0};
    int containers_harvested{0};
    int symbols_harvested{0};
    int callables_harvested{0};
    int parameters_harvested{0};
};

Stratum1HarvestResult harvest_stratum1_std(sqlite3* db, int64_t env_id, bool is_full);

} // namespace utss
