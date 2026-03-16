CXX      := g++
CXXFLAGS := -std=c++17 -Wall -O2

BUILD := build

.PHONY: all clean

all: $(BUILD)/page_replacement

$(BUILD)/page_replacement: page_replacement.cpp json.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ $<

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)
