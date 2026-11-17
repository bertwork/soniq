import random

_ADJECTIVES = [
    "Midnight",
    "Golden",
    "Electric",
    "Silent",
    "Crystal",
    "Neon",
    "Velvet",
    "Cosmic",
    "Frozen",
    "Burning",
    "Fading",
    "Radiant",
    "Hollow",
    "Distant",
    "Silver",
    "Endless",
    "Broken",
    "Wild",
]
_NOUNS = [
    "Echo",
    "Skyline",
    "River",
    "Dream",
    "Horizon",
    "Pulse",
    "Shadow",
    "Fire",
    "Rain",
    "Star",
    "Ocean",
    "Highway",
    "Lullaby",
    "Paradise",
    "Kingdom",
    "Mirage",
    "Signal",
    "Heart",
]
_ARTISTS = [
    "Aurora Waves",
    "Neon Fox",
    "The Velvet Hours",
    "Crystal Static",
    "Midnight Arcade",
    "Echo Valley",
    "Silver Lining",
    "Burning Sky",
    "Hollow Moon",
    "Cosmic Drift",
    "Paper Lanterns",
    "Iron Feather",
    "Glass Harbor",
    "Fading Signals",
    "Wild Ember",
    "Ocean Cartography",
]
_ALBUMS = [
    "First Light",
    "After Hours",
    "The Long Way Home",
    "Static Dreams",
    "Northern Lines",
    "Blue Season",
    "Fractured Sky",
    "Analog Heart",
    "Slow Motion",
    "Ghost Notes",
    "Wide Awake",
    "Polaroid",
]
_GENRES = [
    "Pop",
    "Rock",
    "Jazz",
    "Hip-Hop",
    "Electronic",
    "Classical",
    "R&B",
    "Country",
    "Indie",
    "Metal",
]


def _norm(v):
    """Case-insensitive normalize — must match search.py / sort.py."""
    if isinstance(v, str):
        return v.lower()
    return v


def _pre_merge(a, b, key):
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        if _norm(getattr(a[i], key)) <= _norm(getattr(b[j], key)):
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    while i < len(a):
        out.append(a[i])
        i += 1
    while j < len(b):
        out.append(b[j])
        j += 1
    return out


def _pre_sort(seq, key):
    if len(seq) <= 1:
        return list(seq)
    mid = len(seq) // 2
    return _pre_merge(_pre_sort(seq[:mid], key), _pre_sort(seq[mid:], key), key)


def _reverse(seq):
    out = []
    i = len(seq) - 1
    while i >= 0:
        out.append(seq[i])
        i -= 1
    return out


# ── Public API ────────────────────────────────────────────────────────


def generate_songs(count: int, seed: int | None = None, order: str = "random") -> list:
    """
    Generate `count` songs with unique `song_id` values.

    order:
        "random"        — shuffled (default, for interactive use)
        "sorted_id"     — ascending by song_id
        "sorted_title"  — ascending by title
        "reverse_id"    — descending by song_id  (benchmark)
        "reverse_title" — descending by title    (benchmark)
    """
    if seed is not None:
        random.seed(seed)

    from src.models.song import Song

    songs = []
    for i in range(count):
        sid = f"SNG-{i + 1:06d}"  # sequential → uniqueness guaranteed
        title = f"{random.choice(_ADJECTIVES)} {random.choice(_NOUNS)}"
        songs.append(
            Song(
                song_id=sid,
                title=title,
                artist=random.choice(_ARTISTS),
                album=random.choice(_ALBUMS),
                genre=random.choice(_GENRES),
                year=random.randint(1960, 2025),
                duration=random.randint(90, 480),
            )
        )

    if order == "random":
        random.shuffle(songs)
    elif order == "sorted_id":
        pass  # already ascending
    elif order == "sorted_title":
        songs = _pre_sort(songs, "title")
    elif order == "reverse_id":
        songs = _reverse(songs)
    elif order == "reverse_title":
        songs = _reverse(_pre_sort(songs, "title"))
    else:
        raise ValueError(f"Unknown order: {order!r}")

    return songs
