#!/usr/bin/env python3
"""
Page Replacement Simulator — Homework 01
ECE 502C Operating Systems

Algorithms
----------
  FIFO      First-In First-Out          (complete example — read this first)
  LRU       Least Recently Used         (TODO: implement)
  TwoList   Active/Inactive two-list    (TODO: implement)

Usage
-----
  python3 page_replacement.py                       # run all test cases
  python3 page_replacement.py --verbose             # verbose FIFO trace per case
  python3 page_replacement.py --test my_cases.json  # use a custom test file
"""

import argparse
import json
from abc import ABC, abstractmethod
from collections import deque, OrderedDict


# ===========================================================================
# Abstract base class
# ===========================================================================

class PageReplacer(ABC):
    """
    Interface for page-replacement algorithms.

    Subclasses manage a fixed pool of *capacity* page frames.
    Call access(page) for every memory reference in the workload.
    """

    def __init__(self, capacity: int) -> None:
        assert capacity > 0, "capacity must be positive"
        self.capacity = capacity
        self._faults   = 0
        self._accesses = 0

    @abstractmethod
    def access(self, page: int) -> bool:
        """
        Simulate one memory reference to *page*.

        Returns True  — page fault  (page was not in memory; it has been loaded now).
        Returns False — page hit    (page was already in memory).
        """

    @abstractmethod
    def frames(self) -> list[int]:
        """Return the list of pages currently held in memory frames."""

    # ------------------------------------------------------------------
    # Derived statistics — do not override
    # ------------------------------------------------------------------

    @property
    def fault_rate(self) -> float:
        return self._faults / self._accesses if self._accesses else 0.0

    def stats(self) -> str:
        return (
            f"accesses={self._accesses:5d}  "
            f"faults={self._faults:5d}  "
            f"fault_rate={self.fault_rate:.2%}"
        )


# ===========================================================================
# FIFO  — complete example
# ===========================================================================

class FIFOReplacer(PageReplacer):
    """
    First-In First-Out page replacement.

    Every page in memory is ordered by its *arrival time*.  When a new page
    must be loaded and memory is full, the page that has been resident the
    longest (the "oldest" one) is evicted, regardless of how recently it was
    last accessed.

    Data structures
    ---------------
    self._frames : set[int]
        Pages currently in memory.  O(1) membership test.

    self._order : deque[int]
        Arrival order — front element is the oldest (next eviction candidate).
        Pages are appended to the right on each fault.
    """

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._frames: set[int]    = set()
        self._order:  deque[int]  = deque()

    # ------------------------------------------------------------------

    def access(self, page: int) -> bool:
        self._accesses += 1

        if page in self._frames:          # ---- hit: nothing changes ----
            return False

        # ---- page fault ----
        self._faults += 1

        if len(self._frames) == self.capacity:   # memory full → evict
            victim = self._order.popleft()        # oldest page
            self._frames.remove(victim)

        self._frames.add(page)
        self._order.append(page)
        return True

    def frames(self) -> list[int]:
        return list(self._frames)


# ===========================================================================
# LRU  — TODO: implement
# ===========================================================================

class LRUReplacer(PageReplacer):
    """
    Least Recently Used page replacement.

    Evict the page whose *last access* was farthest in the past.

    Implementation hint
    -------------------
    Use a single collections.OrderedDict as an *ordered set*:

        key   = page number
        value = None  (we only care about key order)

    Maintain the invariant:
        - *Most recently used* page is at the RIGHT (tail) end.
        - *Least recently used* page is at the LEFT (head) end.

    Useful OrderedDict operations
    ------------------------------
        d[key] = None          # insert a new key at the tail
        d.move_to_end(key)     # move existing key to the tail  (last=True default)
        d.popitem(last=False)  # remove & return the (key, value) at the head (LRU)
        key in d               # O(1) membership test
        len(d)                 # number of entries
    """

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._cache: OrderedDict[int, None] = OrderedDict()

    # ------------------------------------------------------------------

    def access(self, page: int) -> bool:
        """
        Record one memory reference to *page*.

        Algorithm
        ---------
        1. Increment self._accesses.

        2. Hit (page already in memory):
               - Mark the page as most-recently-used (move to tail).
               - Return False.

        3. Fault (page NOT in memory):
               - Increment self._faults.
               - If memory is full, evict the LRU page (pop from head).
               - Insert the new page at the tail (most-recently-used position).
               - Return True.
        """
        self._accesses += 1

        if page in self._cache:           # ---- hit: refresh to MRU ----
            self._cache.move_to_end(page)
            return False

        # ---- page fault ----
        self._faults += 1

        if len(self._cache) == self.capacity:   # memory full → evict LRU
            self._cache.popitem(last=False)

        self._cache[page] = None              # insert at tail (MRU)
        return True

    def frames(self) -> list[int]:
        """Return pages in LRU order: index 0 = least recently used."""
        return list(self._cache.keys())


# ===========================================================================
# Two-List  — TODO: implement
# ===========================================================================

class TwoListReplacer(PageReplacer):
    """
    Two-list (active / inactive) page replacement.

    Inspired by the Linux kernel 2.4–2.6 page reclaim algorithm.  The core
    idea is to distinguish *hot* pages (accessed more than once recently)
    from *cold* pages (accessed only once, or not recently), so that a single
    large sequential scan cannot flush all frequently-used pages out of memory.

    Memory layout
    -------------
    Total frames = capacity.

        Inactive list  — cold pages; primary eviction pool.
        Active   list  — hot pages; protected from immediate eviction.

    Capacity split:
        inactive_cap = max(1, capacity // 3)
        active_cap   = capacity - inactive_cap

    Page lifecycle
    --------------
    1. New page (page fault)
           → loaded into the *tail* of the inactive list.

    2. Page hit while on the inactive list  (second reference → "hot")
           → removed from inactive, inserted at *tail* of active list.
           → call _balance_active() to enforce the active size limit.

    3. Page hit while on the active list
           → moved to the *tail* of active list  (refresh recency).

    4. Eviction needed
           → victim taken from the *head* of the inactive list.
           → if inactive is empty, demote the *head* of active to the tail
             of inactive first, then evict from inactive.

    5. Active list overflow  (_balance_active)
           → while len(active) > active_cap:
                 demote the head of active to the tail of inactive.

    Data structures
    ---------------
    Use two OrderedDicts — one for each list.  Head = oldest (popitem(last=False)).

        self._inactive : OrderedDict[int, None]
        self._active   : OrderedDict[int, None]
        self._location : dict[int, str]    # page → "active" | "inactive"
    """

    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self.inactive_cap = max(1, capacity // 3)
        self.active_cap   = capacity - self.inactive_cap

        self._inactive: OrderedDict[int, None] = OrderedDict()
        self._active:   OrderedDict[int, None] = OrderedDict()
        self._location: dict[int, str]         = {}  # page → "active" | "inactive"

    # ------------------------------------------------------------------

    def access(self, page: int) -> bool:
        """
        Record one memory reference to *page*.

        Algorithm  (three cases — use self._location to distinguish them)
        -----------------------------------------------------------------
        Case A — page is on the active list (hot hit):
            Move page to tail of active.
            Return False.

        Case B — page is on the inactive list (cold hit / promotion):
            Remove page from inactive.
            Insert page at tail of active.
            Update self._location[page] = "active".
            Call self._balance_active().
            Return False.

        Case C — page fault (page not in memory at all):
            Increment self._faults.
            If total frames are at capacity, call self._evict().
            Insert page at tail of inactive.
            Update self._location[page] = "inactive".
            Return True.

        Remember to increment self._accesses at the top.
        """
        self._accesses += 1

        loc = self._location.get(page)

        if loc == "active":               # Case A — hot hit
            self._active.move_to_end(page)
            return False

        if loc == "inactive":             # Case B — cold hit → promote
            del self._inactive[page]
            self._active[page] = None
            self._location[page] = "active"
            self._balance_active()
            return False

        # Case C — page fault
        self._faults += 1
        total = len(self._inactive) + len(self._active)
        if total == self.capacity:
            self._evict()
        self._inactive[page] = None
        self._location[page] = "inactive"
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _evict(self) -> None:
        """
        Remove the victim page from the head of the inactive list.

        Steps
        -----
        1. If inactive is empty, demote the oldest active page (head of active)
           to the tail of inactive first:
               - Pop head of active  (popitem(last=False)).
               - Append it to tail of inactive.
               - Update self._location.

        2. Pop the head of inactive  (the eviction victim).
        3. Delete the victim from self._location.
        """
        if not self._inactive:            # inactive empty → demote oldest active
            oldest_active, _ = self._active.popitem(last=False)
            self._inactive[oldest_active] = None
            self._location[oldest_active] = "inactive"

        victim, _ = self._inactive.popitem(last=False)
        del self._location[victim]

    def _balance_active(self) -> None:
        """
        Enforce: len(active) <= self.active_cap.

        While the active list is too large:
            - Pop the head of active  (oldest hot page).
            - Append it to the tail of inactive  (demote).
            - Update self._location.
        """
        while len(self._active) > self.active_cap:
            oldest, _ = self._active.popitem(last=False)
            self._inactive[oldest] = None
            self._location[oldest] = "inactive"

    def frames(self) -> list[int]:
        """Return all pages currently in memory (active + inactive)."""
        return list(self._inactive.keys()) + list(self._active.keys())


# ===========================================================================
# Simulation harness
# ===========================================================================

def simulate(replacer: PageReplacer, page_refs: list[int], *, verbose: bool = False) -> None:
    """Drive *replacer* through the reference string *page_refs*."""
    for page in page_refs:
        fault = replacer.access(page)
        if verbose:
            tag = "FAULT" if fault else "hit  "
            print(f"  page {page:3d}  {tag}  frames={sorted(replacer.frames())}")



def run_test_cases(path: str, *, verbose: bool = False) -> None:
    """
    Load test cases from *path* (JSON) and run all three algorithms on each one.

    Each test-case entry must have:
        name        str            — short identifier
        category    str            — "normal" or "extreme"
        description str            — one-sentence description
        capacity    int            — number of page frames
        refs        list[int]      — page-reference string
        expected    dict[str, int] — expected fault count per algorithm
                                     keys: "FIFO", "LRU", "TwoList"
    """
    with open(path) as f:
        cases: list[dict] = json.load(f)

    ALGORITHMS: list[tuple[str, type]] = [
        ("FIFO   ", FIFOReplacer),
        ("LRU    ", LRUReplacer),
        ("TwoList", TwoListReplacer),
    ]

    passed = total = 0

    for tc in cases:
        name     = tc["name"]
        category = tc["category"]
        desc     = tc["description"]
        capacity = tc["capacity"]
        refs     = tc["refs"]
        expected = tc.get("expected", {})

        print(f"\n[{category}] {name}  (capacity={capacity}, refs={len(refs)})")
        print(f"  {desc}")

        for alg_name, cls in ALGORITHMS:
            key      = alg_name.strip()
            exp      = expected.get(key)
            replacer = cls(capacity)
            try:
                simulate(replacer, refs,
                         verbose=(verbose and key == "FIFO"))
                got    = replacer._faults
                check  = ""
                if exp is not None:
                    total += 1
                    if got == exp:
                        check = "  [OK]"
                        passed += 1
                    else:
                        check = f"  [FAIL: expected {exp}]"
                print(f"  {alg_name}  faults={got:3d}  fault_rate={replacer.fault_rate:.2%}{check}")
            except NotImplementedError:
                exp_str = f"  (expected {exp})" if exp is not None else ""
                print(f"  {alg_name}  (not implemented yet){exp_str}")

    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} checks passed.")
    print(f"{'='*60}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Page-replacement algorithm simulator")
    ap.add_argument("--verbose", action="store_true",
                    help="print every reference and the resulting frame state")
    ap.add_argument("--test", metavar="FILE", nargs="?",
                    const="testcases.json",
                    help="run predefined test cases from FILE (default: testcases.json)")
    args = ap.parse_args()

    run_test_cases(args.test or "testcases.json", verbose=args.verbose)


if __name__ == "__main__":
    main()
