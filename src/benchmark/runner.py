"""
Benchmark runner for SONIQ's Data Run Log report.
Measures every algorithm against Random / Sorted / Reverse-Sorted inputs
at sizes 100 – 30,000.
"""

from src.data.generator import generate_songs
from src.algorithms.search import linear_search, binary_search
from src.algorithms.sort import bubble_sort, merge_sort
from src.timer.timer import Timer

# Friendly labels → generator order codes
_ORDER_MAP = {
    "Random": "random",
    "Sorted": "sorted_id",
    "Reverse-Sorted": "reverse_id",
}


def _run_single(algo, base_songs, size, order):
    """Run one algorithm on a fresh copy of the dataset. Returns a dict."""
    result = {"algorithm": algo, "size": size, "order": order}

    if algo == "Linear Search":
        target = base_songs[len(base_songs) // 2].song_id
        songs = list(base_songs)
        with Timer() as t:
            idx, comps = linear_search(songs, target, "song_id")
        result.update(
            time_us=t.elapsed_us,
            comparisons=comps,
            status="✓ Found" if idx >= 0 else "✗ Not found",
        )

    elif algo == "Binary Search":
        target = base_songs[len(base_songs) // 2].song_id
        songs = list(base_songs)
        with Timer() as t:
            idx, comps = binary_search(songs, target, "song_id")
        result.update(
            time_us=t.elapsed_us,
            comparisons=comps,
            status="✓ Found" if idx >= 0 else "✗ Not found",
        )

    elif algo == "Bubble Sort":
        songs = list(base_songs)
        with Timer() as t:
            _, comps = bubble_sort(songs, "song_id")
        result.update(time_us=t.elapsed_us, comparisons=comps, status="✓ Sorted")

    elif algo == "Merge Sort":
        songs = list(base_songs)
        with Timer() as t:
            _, comps = merge_sort(songs, "song_id")
        result.update(time_us=t.elapsed_us, comparisons=comps, status="✓ Sorted")

    return result


def run_benchmark(
    sizes, orders, algorithms, on_progress=None, on_result=None, should_stop=None
):
    """
    Execute the full benchmark matrix.

    sizes       : list of ints, e.g. [1000, 10000, 30000]
    orders      : list of str  — from {"Random", "Sorted", "Reverse-Sorted"}
    algorithms  : list of str  — from {"Linear Search", "Binary Search",
                                       "Bubble Sort", "Merge Sort"}
    on_progress : fn(completed, total, message)
    on_result   : fn(result_dict)          ← called after each run
    should_stop : fn() -> bool             ← check between runs
    """
    tasks = [(s, o, a) for s in sizes for o in orders for a in algorithms]
    total = len(tasks)

    # Cache datasets so every algorithm in a cell tests the SAME data
    dataset_cache = {}

    for i, (size, order, algo) in enumerate(tasks):
        if should_stop and should_stop():
            break

        if on_progress:
            on_progress(i, total, f"Running {algo} | {size:,} rows | {order}")

        cache_key = (size, order)
        if cache_key not in dataset_cache:
            dataset_cache[cache_key] = generate_songs(size, order=_ORDER_MAP[order])

        result = _run_single(algo, dataset_cache[cache_key], size, order)

        if on_result:
            on_result(result)

        if on_progress:
            on_progress(i + 1, total, f"Done: {algo} | {size:,} rows | {order}")