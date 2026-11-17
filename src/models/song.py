from dataclasses import dataclass

@dataclass
class Song:
    """A single song.  `song_id` is the UNIQUE search key (like an SKU)."""

    song_id: str  # e.g. "SNG-000123"  — always unique
    title: str
    artist: str
    album: str
    genre: str
    year: int
    duration: int  # seconds

    def to_row(self) -> tuple:
        """Return a row tuple formatted for the Treeview."""
        minutes, seconds = divmod(self.duration, 60)
        return (
            self.song_id,
            self.title,
            self.artist,
            self.album,
            self.genre,
            self.year,
            f"{minutes}:{seconds:02d}",
        )