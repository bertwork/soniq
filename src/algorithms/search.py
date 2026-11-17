def _cmp(value):
    """
    Normalize a value for comparison.
    - strings → lowercase  (case-insensitive matching)
    - numbers → unchanged
    """
    if isinstance(value, str):
        return value.lower()
    return value


def linear_search(songs, target, key="song_id"):
    """
    Sequential scan — O(n).  Case-insensitive for text fields.

    Returns
    -------
    (index, comparisons)
    """
    target_c = _cmp(target)
    comparisons = 0
    n = len(songs)
    for i in range(n):
        comparisons += 1
        if _cmp(getattr(songs[i], key)) == target_c:
            return i, comparisons
    return -1, comparisons


def binary_search(songs, target, key="song_id"):
    """
    Iterative halving search — O(log n).  Case-insensitive for text fields.

    Requires `songs` to be sorted ASCENDING by the *normalized* form of `key`
    (which is what sort.py guarantees).  If data is not sorted, results
    are unreliable — this is intentional and is one of the benchmark's data
    points.

    Returns
    -------
    (index, comparisons)
    """
    target_c = _cmp(target)
    lo = 0
    hi = len(songs) - 1
    comparisons = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        comparisons += 1
        val_c = _cmp(getattr(songs[mid], key))
        if val_c == target_c:
            return mid, comparisons
        if val_c < target_c:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1, comparisons