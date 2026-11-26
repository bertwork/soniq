import random

WORDS_A = [
    "Midnight",
    "Golden",
    "Electric",
    "Fading",
    "Neon",
    "Silent",
    "Wild",
    "Frozen",
    "Velvet",
    "Hollow",
    "Cosmic",
    "Crystal",
]
WORDS_B = [
    "Dream",
    "Fire",
    "Shadow",
    "Mirage",
    "Signal",
    "Echo",
    "Horizon",
    "River",
    "Heart",
    "Star",
    "Highway",
    "Rain",
]
ARTISTS = [
    "Hollow Moon",
    "The Velvet Hours",
    "Burning Sky",
    "Aurora Waves",
    "Crystal Static",
    "Paper Lanterns",
    "Echo Valley",
    "Iron Feather",
]
ALBUMS = [
    "Wide Awake",
    "After Hours",
    "Slow Motion",
    "Static Dreams",
    "Ghost Notes",
    "Polaroid",
    "Fractured Sky",
    "First Light",
]
GENRES = [
    "Classical",
    "Country",
    "Metal",
    "Electronic",
    "Jazz",
    "Hip-Hop",
    "Rock",
    "R&B",
    "Indie",
]


def make_song(n):
    """One song. The ID comes from the counter n, so it is always unique."""
    return {
        "song_id": f"SNG-{n:06d}",  # SNG-000001, SNG-000002, ...
        "title": random.choice(WORDS_A) + " " + random.choice(WORDS_B),
        "artist": random.choice(ARTISTS),
        "album": random.choice(ALBUMS),
        "genre": random.choice(GENRES),
        "year": random.randint(1960, 2024),
        "duration": random.randint(90, 480),  # seconds; the UI shows m:ss
    }


def generate_songs(count, order="random"):
    """order: 'random', 'sorted', or 'reverse' (by song_id)."""
    songs = [make_song(n) for n in range(1, count + 1)]  # already sorted by ID

    if order == "reverse":
        songs = songs[::-1]

    elif order == "random":
        random.shuffle(songs)

    # 'sorted' needs nothing: the list is already in ID order
    return songs


# ---------- Testing ----------
def is_ascending(songs, key):
    for i in range(len(songs) - 1):
        if songs[i][key] > songs[i + 1][key]:
            return False
        
    return True


if __name__ == "__main__":
    for size in (1000, 10000, 30000):
        for order in ("random", "sorted", "reverse"):
            data = generate_songs(size, order)
            unique = len({s["song_id"] for s in data}) == size
            asc = is_ascending(data, "song_id")
            print(
                f"{size:>6} {order:<8} unique IDs: {unique}  ascending: {asc}  first: {data[0]['song_id']}"
            )