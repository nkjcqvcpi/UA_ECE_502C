/*
 * Page Replacement Simulator — Homework 01
 * ECE 502C Operating Systems
 *
 * Algorithms
 * ----------
 *   FIFO      First-In First-Out          (complete example — read this first)
 *   LRU       Least Recently Used         (TODO: implement)
 *   TwoList   Active/Inactive two-list    (TODO: implement)
 *
 * Build
 * -----
 *   make
 *
 * Usage
 * -----
 *   ./page_replacement            # run all test cases (testcases.json)
 *   ./page_replacement --verbose  # verbose FIFO trace per case
 *   ./page_replacement --test path/to/cases.json
 */

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <list>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

// Minimal JSON parsing is done with nlohmann/json (single-header).
// If the header is not present, the build will fail with a clear message.
#include "json.hpp"
using json = nlohmann::json;


// ===========================================================================
// Abstract base class
// ===========================================================================

class PageReplacer {
public:
    explicit PageReplacer(int capacity) : capacity_(capacity) {
        assert(capacity > 0 && "capacity must be positive");
    }
    virtual ~PageReplacer() = default;

    /**
     * Simulate one memory reference to @page.
     * Returns true  — page fault  (page was not in memory; it has been loaded).
     * Returns false — page hit    (page was already in memory).
     */
    virtual bool access(int page) = 0;

    /** Return the pages currently held in memory frames. */
    virtual std::vector<int> frames() const = 0;

    // ------------------------------------------------------------------
    // Derived statistics — do not override
    // ------------------------------------------------------------------

    double fault_rate() const {
        return accesses_ ? static_cast<double>(faults_) / accesses_ : 0.0;
    }

    int faults()   const { return faults_;   }
    int accesses() const { return accesses_; }

protected:
    int capacity_;
    int faults_   = 0;
    int accesses_ = 0;
};


// ===========================================================================
// FIFO  — complete example
// ===========================================================================

/**
 * First-In First-Out page replacement.
 *
 * Every page in memory is ordered by its *arrival time*.  When a new page
 * must be loaded and memory is full, the page that has been resident the
 * longest (the "oldest") is evicted, regardless of recent access.
 *
 * Data structures
 * ---------------
 * frames_set_  : unordered_set<int>  — O(1) membership test.
 * order_       : deque<int>          — front = oldest (next eviction candidate).
 */
class FIFOReplacer : public PageReplacer {
public:
    explicit FIFOReplacer(int capacity) : PageReplacer(capacity) {}

    bool access(int page) override {
        ++accesses_;

        if (frames_set_.count(page)) {   // hit: nothing changes
            return false;
        }

        // page fault
        ++faults_;

        if (static_cast<int>(frames_set_.size()) == capacity_) {
            int victim = order_.front();
            order_.pop_front();
            frames_set_.erase(victim);
        }

        frames_set_.insert(page);
        order_.push_back(page);
        return true;
    }

    std::vector<int> frames() const override {
        return std::vector<int>(frames_set_.begin(), frames_set_.end());
    }

private:
    std::unordered_set<int> frames_set_;
    std::deque<int>         order_;
};


// ===========================================================================
// LRU  — TODO: implement
// ===========================================================================

/**
 * Least Recently Used page replacement.
 *
 * Evict the page whose *last access* was farthest in the past.
 *
 * Implementation hint
 * -------------------
 * Use a std::list<int> as an ordered sequence (head = LRU, tail = MRU)
 * together with an unordered_map<int, list<int>::iterator> for O(1) lookup:
 *
 *     cache_list_  : std::list<int>
 *         Ordered by recency — front is least recently used (eviction candidate),
 *         back is most recently used.
 *
 *     cache_map_   : std::unordered_map<int, std::list<int>::iterator>
 *         Maps page → iterator into cache_list_, enabling O(1) splice.
 *
 * Useful list operations
 * ----------------------
 *     cache_list_.push_back(page)          // insert at tail (MRU)
 *     cache_list_.erase(it)                // remove by iterator (O(1))
 *     cache_list_.splice(cache_list_.end(), cache_list_, it)
 *                                          // move existing node to tail (O(1))
 *     cache_list_.front()                  // LRU page (eviction candidate)
 *     cache_list_.pop_front()              // evict LRU page
 */
class LRUReplacer : public PageReplacer {
public:
    explicit LRUReplacer(int capacity) : PageReplacer(capacity) {
        // TODO: initialize your data structure(s) — nothing extra needed here
        //       for std::list + std::unordered_map.
    }

    /**
     * Record one memory reference to @page.
     *
     * Algorithm
     * ---------
     * 1. Increment accesses_.
     *
     * 2. Hit (page already in memory):
     *        - Move the page to the tail (most-recently-used position).
     *        - Return false.
     *
     * 3. Fault (page NOT in memory):
     *        - Increment faults_.
     *        - If memory is full, evict the LRU page (pop from front).
     *        - Insert the new page at the tail (most-recently-used position).
     *        - Return true.
     */
    bool access(int page) override {
        // TODO: implement
        throw std::logic_error("LRUReplacer::access not implemented");
    }

    /** Return pages in LRU order: index 0 = least recently used. */
    std::vector<int> frames() const override {
        // TODO: implement
        throw std::logic_error("LRUReplacer::frames not implemented");
    }

private:
    std::list<int>                                   cache_list_;
    std::unordered_map<int, std::list<int>::iterator> cache_map_;
};


// ===========================================================================
// Two-List  — TODO: implement
// ===========================================================================

/**
 * Two-list (active / inactive) page replacement.
 *
 * Inspired by the Linux kernel 2.4–2.6 page reclaim algorithm.  The core
 * idea is to distinguish *hot* pages (accessed more than once recently)
 * from *cold* pages (accessed only once, or not recently), so that a single
 * large sequential scan cannot flush all frequently-used pages out of memory.
 *
 * Memory layout
 * -------------
 * Total frames = capacity_.
 *
 *     Inactive list  — cold pages; primary eviction pool.
 *     Active   list  — hot pages; protected from immediate eviction.
 *
 * Capacity split:
 *     inactive_cap_ = std::max(1, capacity_ / 3)
 *     active_cap_   = capacity_ - inactive_cap_
 *
 * Page lifecycle
 * --------------
 * 1. New page (page fault)
 *        → loaded into the *tail* of the inactive list.
 *
 * 2. Page hit while on the inactive list  (second reference → "hot")
 *        → removed from inactive, inserted at *tail* of active list.
 *        → call balance_active_() to enforce the active size limit.
 *
 * 3. Page hit while on the active list
 *        → moved to the *tail* of active list  (refresh recency).
 *
 * 4. Eviction needed
 *        → victim taken from the *head* of the inactive list.
 *        → if inactive is empty, demote the *head* of active to the tail
 *          of inactive first, then evict from inactive.
 *
 * 5. Active list overflow  (balance_active_)
 *        → while len(active) > active_cap_:
 *              demote the head of active to the tail of inactive.
 *
 * Data structures
 * ---------------
 * Use two std::list<int>s (one per list) and two unordered_maps for O(1)
 * iterator lookup, plus a plain location map:
 *
 *     inactive_list_ / inactive_map_  — cold list, head = oldest
 *     active_list_   / active_map_    — hot list,  head = oldest
 *     location_      : unordered_map<int, std::string>
 *                      page → "active" | "inactive"
 */
class TwoListReplacer : public PageReplacer {
public:
    explicit TwoListReplacer(int capacity) : PageReplacer(capacity) {
        inactive_cap_ = std::max(1, capacity_ / 3);
        active_cap_   = capacity_ - inactive_cap_;
        // TODO: nothing else to initialize for std::list + unordered_map.
    }

    /**
     * Record one memory reference to @page.
     *
     * Algorithm  (three cases — use location_ to distinguish them)
     * -------------------------------------------------------------
     * Case A — page is on the active list (hot hit):
     *     Move page to tail of active.
     *     Return false.
     *
     * Case B — page is on the inactive list (cold hit / promotion):
     *     Remove page from inactive (list + map).
     *     Insert page at tail of active (list + map).
     *     Update location_[page] = "active".
     *     Call balance_active_().
     *     Return false.
     *
     * Case C — page fault (page not in memory at all):
     *     Increment faults_.
     *     If total frames are at capacity_, call evict_().
     *     Insert page at tail of inactive (list + map).
     *     Update location_[page] = "inactive".
     *     Return true.
     *
     * Remember to increment accesses_ at the top.
     */
    bool access(int page) override {
        // TODO: implement
        throw std::logic_error("TwoListReplacer::access not implemented");
    }

    /** Return all pages currently in memory (inactive + active). */
    std::vector<int> frames() const override {
        // TODO: implement
        throw std::logic_error("TwoListReplacer::frames not implemented");
    }

private:
    int inactive_cap_;
    int active_cap_;

    std::list<int>                                    inactive_list_;
    std::unordered_map<int, std::list<int>::iterator> inactive_map_;

    std::list<int>                                    active_list_;
    std::unordered_map<int, std::list<int>::iterator> active_map_;

    std::unordered_map<int, std::string> location_;   // "active" | "inactive"

    /**
     * Remove the victim page from the head of the inactive list.
     *
     * Steps
     * -----
     * 1. If inactive is empty, demote the oldest active page (head of active)
     *    to the tail of inactive first:
     *        - Pop head of active (list + map).
     *        - Push it to tail of inactive (list + map).
     *        - Update location_.
     *
     * 2. Pop the head of inactive (the eviction victim).
     * 3. Erase the victim from location_.
     */
    void evict_() {
        // TODO: implement
        throw std::logic_error("TwoListReplacer::evict_ not implemented");
    }

    /**
     * Enforce: active_list_.size() <= active_cap_.
     *
     * While the active list is too large:
     *     - Pop the head of active (oldest hot page).
     *     - Push it to the tail of inactive (demote).
     *     - Update location_.
     */
    void balance_active_() {
        // TODO: implement
        throw std::logic_error("TwoListReplacer::balance_active_ not implemented");
    }
};


// ===========================================================================
// Simulation harness
// ===========================================================================

static void simulate(PageReplacer& replacer, const std::vector<int>& refs,
                     bool verbose)
{
    for (int page : refs) {
        bool fault = replacer.access(page);
        if (verbose) {
            std::vector<int> f = replacer.frames();
            std::sort(f.begin(), f.end());
            std::string fs = "[";
            for (int i = 0; i < (int)f.size(); ++i) {
                if (i) fs += ", ";
                fs += std::to_string(f[i]);
            }
            fs += "]";
            std::cout << "  page " << page << "  " << (fault ? "FAULT" : "hit  ")
                      << "  frames=" << fs << "\n";
        }
    }
}


static void run_test_cases(const std::string& path, bool verbose)
{
    std::ifstream f(path);
    if (!f) {
        std::cerr << "Cannot open " << path << "\n";
        return;
    }
    json cases = json::parse(f);

    struct AlgEntry {
        std::string name;
        std::string key;
        std::function<std::unique_ptr<PageReplacer>(int)> make;
    };

    std::vector<AlgEntry> algorithms = {
        {"FIFO   ", "FIFO",    [](int c){ return std::make_unique<FIFOReplacer>(c);    }},
        {"LRU    ", "LRU",     [](int c){ return std::make_unique<LRUReplacer>(c);     }},
        {"TwoList", "TwoList", [](int c){ return std::make_unique<TwoListReplacer>(c); }},
    };

    int passed = 0, total = 0;

    for (auto& tc : cases) {
        std::string name     = tc["name"];
        std::string category = tc["category"];
        std::string desc     = tc["description"];
        int         capacity = tc["capacity"];
        std::vector<int> refs = tc["refs"].get<std::vector<int>>();
        json expected = tc.value("expected", json::object());

        std::cout << "\n[" << category << "] " << name
                  << "  (capacity=" << capacity << ", refs=" << refs.size() << ")\n"
                  << "  " << desc << "\n";

        for (auto& alg : algorithms) {
            auto replacer = alg.make(capacity);
            bool not_impl = false;

            try {
                simulate(*replacer, refs,
                         verbose && alg.key == "FIFO");
            } catch (const std::logic_error&) {
                not_impl = true;
            }

            if (not_impl) {
                std::string exp_str;
                if (expected.contains(alg.key)) {
                    exp_str = "  (expected " + std::to_string(expected[alg.key].get<int>()) + ")";
                }
                std::cout << "  " << alg.name
                          << "  (not implemented yet)" << exp_str << "\n";
                continue;
            }

            int got = replacer->faults();
            std::string check;
            if (expected.contains(alg.key)) {
                int exp = expected[alg.key].get<int>();
                ++total;
                if (got == exp) {
                    check = "  [OK]";
                    ++passed;
                } else {
                    check = "  [FAIL: expected " + std::to_string(exp) + "]";
                }
            }

            // fault_rate as percentage
            double fr = replacer->fault_rate() * 100.0;
            char buf[64];
            std::snprintf(buf, sizeof(buf), "%.2f%%", fr);

            std::cout << "  " << alg.name
                      << "  faults=" << got
                      << "  fault_rate=" << buf
                      << check << "\n";
        }
    }

    std::string sep(60, '=');
    std::cout << "\n" << sep << "\n"
              << "Result: " << passed << "/" << total << " checks passed.\n"
              << sep << "\n";
}


int main(int argc, char* argv[])
{
    std::string test_file = "../testcases.json";
    bool verbose = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--verbose") {
            verbose = true;
        } else if (arg == "--test" && i + 1 < argc) {
            test_file = argv[++i];
        } else if (arg == "--test") {
            // use default
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            return 1;
        }
    }

    run_test_cases(test_file, verbose);
    return 0;
}
