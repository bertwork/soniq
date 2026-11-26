import time

# ---------- Timer ----------
def timed(func, *args):
    """Run func(*args). Returns (result, microseconds)."""
    start = time.perf_counter()
    result = func(*args)
    elapsed_us = (time.perf_counter() - start) * 1_000_000

    return result, elapsed_us


# ---------- Searching ----------
# Search is case-insensitive, so both sides are lowercased.
# Returns the position of the song, or -1 if it is not found.

def linear_search(songs, key, target):
    target = target.lower()
    comparisons = 0

    for i in range(len(songs)):
        comparisons += 1  # one comparison per song looked at
        if songs[i][key].lower() == target:
            return i, comparisons
    return -1, comparisons


def binary_search(songs, key, target):
    """songs MUST already be sorted by `key`"""
    target = target.lower()
    comparisons = 0
    low, high = 0, len(songs) - 1

    while low <= high:
        mid = (low + high) // 2
        value = songs[mid][key].lower()
        comparisons += 1  # rule: one comparison per loop

        if value == target:
            return mid, comparisons
        
        elif value < target:
            low = mid + 1  # target is in the right half

        else:
            high = mid - 1  # target is in the left half
            
    return -1, comparisons


# ---------- Sorting (slow): Bubble Sort ----------
def bubble_sort(songs, key):
    """Sorts IN PLACE, so pass a copy. Stops early if a pass makes no swaps."""
    comparisons = 0
    n = len(songs)

    for i in range(n - 1):
        swapped = False
        
        for j in range(n - 1 - i):  # the last i items are already in place
            comparisons += 1

            if songs[j][key] > songs[j + 1][key]:
                songs[j], songs[j + 1] = songs[j + 1], songs[j]
                swapped = True

        if not swapped:  # nothing moved the list is sorted
            break

    return songs, comparisons


# ---------- Sorting (fast): Merge Sort ----------
def merge_sort(songs, key):
    """Returns a NEW sorted list. Uses <= so equal items keep their order (stable)."""
    counter = [0]  # a list, so inner calls can change it
    return _merge_sort(songs, key, counter), counter[0]


def _merge_sort(songs, key, counter):
    if len(songs) <= 1:
        return songs
    
    mid = len(songs) // 2
    left = _merge_sort(songs[:mid], key, counter)
    right = _merge_sort(songs[mid:], key, counter)

    merged = []
    i = j = 0

    while i < len(left) and j < len(right):
        counter[0] += 1

        if left[i][key] <= right[j][key]:
            merged.append(left[i])
            i += 1

        else:
            merged.append(right[j])
            j += 1

    while i < len(left):  # one side ran out: copy the rest
        merged.append(left[i])
        i += 1

    while j < len(right):
        merged.append(right[j])
        j += 1

    return merged


# ---------- Testing ----------
def is_ascending(songs, key):
    for i in range(len(songs) - 1):
        if songs[i][key] > songs[i + 1][key]:
            return False
        
    return True


if __name__ == "__main__":
    from data_gen import generate_songs

    print("Sorting (key = song_id)")
    for size in (1000, 10000, 30000):
        for order in ("random", "sorted", "reverse"):
            base = generate_songs(size, order)

            (out, comps), us = timed(merge_sort, base[:], "song_id")
            print(
                f"{size:>6} {order:<8} merge   comps={comps:>9,}  {us/1000:>9.1f} ms  ok={is_ascending(out, 'song_id')}"
            )

            # bubble sort is slow, so only run the big sizes on sorted input here
            if size == 1000 or order == "sorted":
                (out, comps), us = timed(bubble_sort, base[:], "song_id")
                print(
                    f"{size:>6} {order:<8} bubble  comps={comps:>9,}  {us/1000:>9.1f} ms  ok={is_ascending(out, 'song_id')}"
                )

    print("\nSearching 30,000 songs")
    data = generate_songs(30000, "sorted")

    for target in ("SNG-000001", "SNG-015000", "SNG-030000", "sng-999999"):
        (p1, c1), _ = timed(linear_search, data, "song_id", target)
        (p2, c2), _ = timed(binary_search, data, "song_id", target)
        print(
            f"{target}: linear pos={p1:>6} comps={c1:>6}   binary pos={p2:>6} comps={c2:>3}"
        )
