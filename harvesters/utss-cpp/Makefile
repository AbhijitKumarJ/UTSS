CXX ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra -pthread -Iinclude -Ithird_party/sqlite3
LDFLAGS ?= -ldl -lpthread

SQLITE_OBJ = third_party/sqlite3/sqlite3.o
LIB_SRCS = src/schema.cpp src/stratum0_ambient.cpp src/stratum1_std.cpp src/stratum3_workspace.cpp src/queries.cpp
LIB_OBJS = $(LIB_SRCS:.cpp=.o)

BIN_DIR = bin
TARGET = $(BIN_DIR)/utss-cpp
TEST_TARGET = $(BIN_DIR)/test_utss

.PHONY: all clean test dirs

all: dirs $(TARGET) $(TEST_TARGET)

dirs:
	@mkdir -p $(BIN_DIR)

$(SQLITE_OBJ): third_party/sqlite3/sqlite3.c third_party/sqlite3/sqlite3.h
	gcc -O2 -c third_party/sqlite3/sqlite3.c -o $(SQLITE_OBJ)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(LIB_OBJS) $(SQLITE_OBJ) src/main.cpp
	$(CXX) $(CXXFLAGS) src/main.cpp $(LIB_OBJS) $(SQLITE_OBJ) -o $(TARGET) $(LDFLAGS)

$(TEST_TARGET): $(LIB_OBJS) $(SQLITE_OBJ) tests/test_main.cpp
	$(CXX) $(CXXFLAGS) tests/test_main.cpp $(LIB_OBJS) $(SQLITE_OBJ) -o $(TEST_TARGET) $(LDFLAGS)

test: $(TEST_TARGET)
	@./$(TEST_TARGET)

clean:
	rm -rf $(BIN_DIR) src/*.o
