# Homework: Page Replacement Algorithms

## Learning Goals

* Understand why page replacement is needed and how policy affects performance
* Implement **LRU** (Least Recently Used) using an efficient ordered data structure
* Implement the **two-list (active/inactive) algorithm** inspired by the classic Linux kernel
* Observe how different workloads (sequential scans, hotspot access, random) change which policy wins

## Development Environment

This homework is available in **two languages** — choose one:

| Language | Directory | Build |
|----------|-----------|-------|
| Python 3 | `python/` | No build step needed |
| C++ (17) | `cpp/`    | `make` (output in `cpp/build/`) |

Both versions use the **same test cases** from `testcases.json` and implement the same three algorithms.

## Background

When physical memory is full and a new page must be loaded, the OS must choose a *victim* page to evict.  The replacement policy determines which page is chosen, and a poor choice leads to extra disk I/O and poor application performance.

### FIFO (provided as example)

Always evict the page that has been resident in memory the longest, regardless of how recently it was accessed.  Simple to implement, but ignores recency entirely.

> **Belady's anomaly**: FIFO can actually produce *more* faults when given *more* frames — a counterintuitive result demonstrated in the `beladys_anomaly_3frames` / `beladys_anomaly_4frames` test cases.

### LRU (TODO)

Evict the page whose *last access* was farthest in the past.  Under typical workloads this approximates the optimal (OPT) algorithm, because recently-used pages are likely to be used again soon (temporal locality).

**Python hint**: use a single `collections.OrderedDict` as an *ordered set* (head = LRU, tail = MRU).

**C++ hint**: use a `std::list<int>` for ordering (front = LRU, back = MRU) plus an `unordered_map<int, list<int>::iterator>` for O(1) lookup and `splice`.

### Two-List / Active–Inactive (TODO)

Used in the Linux 2.4–2.6 kernel to defend against the *single large scan* problem: a process reading a huge file once would flush all hot pages out of a plain LRU cache.

The idea is to split memory into two lists:

| List | Role | Eviction priority |
|------|------|-------------------|
| **Inactive** | "cold" pages — seen only once recently | Evicted first (head = oldest cold page) |
| **Active** | "hot" pages — accessed more than once recently | Protected; only demoted when active list is too large |

**Page lifecycle**

```
                  ┌──────────────────────────────────────┐
                  │ INACTIVE LIST          ACTIVE LIST   │
  page fault ─►  │ [oldest] ← → [newest]  [oldest] ← → [newest]  │
                  │                                        │
  second access ──────────────────────────────────────────►  (promote to active tail)
  active hit  ───────────────────────────────────────────►   (refresh to active tail)
  evict victim ◄─ │ (pop inactive head)                   │
  active full ────────────────────►  (demote active head to inactive tail)
                  └──────────────────────────────────────┘
```

Capacity split: `inactive_cap = max(1, capacity // 3)`,  `active_cap = capacity - inactive_cap`.

## Repository Structure

```
01_page_replacement/
├── testcases.json      ← shared test cases (both languages)
├── python/
│   └── page_replacement.py    ← skeleton (TODO: LRU, TwoList)
└── cpp/
    ├── page_replacement.cpp   ← skeleton (TODO: LRU, TwoList)
    ├── Makefile
    └── json.hpp               ← nlohmann/json single-header (bundled)
```

## The Starter Code

`page_replacement.py` / `page_replacement.cpp` each contain:

* `PageReplacer` — abstract base class defining the interface.
* `FIFOReplacer` — **complete implementation** showing how to use the API.
* `LRUReplacer` — skeleton with `TODO` markers for you to fill in.
* `TwoListReplacer` — skeleton with `TODO` markers for you to fill in.
* `simulate()` / `run_test_cases()` — harness code (do not modify).

`testcases.json` — **predefined test cases** with hand-verified expected fault counts.
* 5 normal cases covering everyday access patterns.
* 4 extreme cases exposing corner cases and the unique behaviors of each algorithm.

## Requirements

The assignment expects you to submit your **source code** (either .py or .cpp) and a **writeup** (PDF, 1-2 pages) describing your implementation, test results, and answers to the discussion questions below.

| # | Requirement | Points |
|---|-------------|--------|
| 1 | Implement `LRUReplacer.access()` correctly. | 40% |
| 2 | Implement `TwoListReplacer.access()` correctly. | 40% |
| 3 | Testing and writeup. | 20% |

### Correctness criteria

All predefined test cases should pass (`Result: xx/xx checks passed`).

### Writeup requirements

1. A short description of your LRU and TwoList implementation.
2. A short description of your testing, e.g., additional test cases you tried beyond `testcases.json`.
3. Answers to the discussion questions below.

### Discussion questions

1. In the `lru_beats_fifo` test case, FIFO evicts pages 0 and 1 even though they are accessed again shortly after.  Why does FIFO make the wrong choice here, and why does LRU make the right one?

2. In the `twolist_approximation_cost` test case, TwoList incurs *more* faults than LRU.  Trace through the reference string step by step and explain exactly which eviction decision costs TwoList the extra fault.

3. Compare FIFO, LRU, and TwoList on the `beladys_anomaly_3frames` and `beladys_anomaly_4frames` cases.  Why does FIFO get *more* faults with *more* frames?  Why are LRU and TwoList immune to this anomaly?

4. In `repeated_scan_resistance`, TwoList achieves 28 faults while FIFO and LRU both reach 40.  Explain how the active/inactive split protects the hot working set (pages 0–3) across the three large scans.  What would happen if the active list capacity were reduced to zero?

5. (Bonus) In `working_set_shift`, all three algorithms produce the same fault count despite having very different eviction strategies.  Explain why they converge here.  Does this hold for *any* gradually-shifting workload, or can you construct a counter-example where they diverge?


## How to Run

### Python

Run all predefined test cases (recommended starting point):
```bash
cd python/
python3 page_replacement.py --test
```

Run with a verbose per-reference trace for each test case:
```bash
python3 page_replacement.py --test --verbose
```

### C++

Build and run:
```bash
cd cpp/
make
./build/page_replacement           # reads ../testcases.json
./build/page_replacement --verbose # verbose FIFO trace per case
```

Or build without `make`:
```bash
g++ -std=c++17 -O2 -o build/page_replacement page_replacement.cpp
./build/page_replacement
```

### Hand-checkable FIFO trace

The following sequence (capacity=4, loop workload, pages 0–5, 18 references) can be traced by hand:

```
  page   0  FAULT  frames=[0]
  page   1  FAULT  frames=[0, 1]
  page   2  FAULT  frames=[0, 1, 2]
  page   3  FAULT  frames=[0, 1, 2, 3]
  page   4  FAULT  frames=[1, 2, 3, 4]   ← capacity reached; page 0 evicted
  page   5  FAULT  frames=[2, 3, 4, 5]   ← page 1 evicted
  page   0  FAULT  frames=[0, 3, 4, 5]   ← page 2 evicted
  ...                                      (every reference is a fault)
```

*(The `frames=` set is displayed sorted; fault/hit markers are what matters.)*
