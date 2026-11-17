def _copy(seq):
    """Manual element-by-element copy."""
    out = []
    for item in seq:
        out.append(item)
    return out


def _cmp(value):
    """
    Normalize a value for comparison — MUST match search.py exactly.
    - strings → lowercase
    - numbers → unchanged
    """
    if isinstance(value, str):
        return value.lower()
    return value


def _key(obj, field):
    """Extract the normalized comparable value from a Song."""
    return _cmp(getattr(obj, field))


def bubble_sort(songs, key="song_id"):
    """
    Bubble sort with early-exit optimization — O(n²) worst, O(n) best.

    Returns
    -------
    (sorted_copy, comparisons)
    """
    arr = _copy(songs)
    n = len(arr)
    comparisons = 0

    for i in range(n):
        swapped = False
        for j in range(n - i - 1):
            comparisons += 1
            if _key(arr[j], key) > _key(arr[j + 1], key):
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break

    return arr, comparisons


def merge_sort(songs, key="song_id"):
    """
    Top-down merge sort — O(n log n) guaranteed, stable.

    Returns
    -------
    (sorted_copy, comparisons)
    """
    arr = _copy(songs)
    comparisons = [0]

    def _merge(left, right):
        merged = []
        i = 0
        j = 0
        nl = len(left)
        nr = len(right)

        while i < nl and j < nr:
            comparisons[0] += 1
            if _key(left[i], key) <= _key(right[j], key):
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1

        while i < nl:
            merged.append(left[i])
            i += 1
        while j < nr:
            merged.append(right[j])
            j += 1
        return merged

    def _sort(seq):
        n = len(seq)
        if n <= 1:
            return seq
        mid = n // 2
        return _merge(_sort(seq[:mid]), _sort(seq[mid:]))

    return _sort(arr), comparisons[0]