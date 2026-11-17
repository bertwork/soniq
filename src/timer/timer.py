import time

class Timer:
    """Context manager:  with Timer() as t:  ...  ->  t.elapsed_us"""

    def __init__(self):
        self.start = 0.0
        self.end = 0.0
        self.elapsed_us = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
        self.elapsed_us = (self.end - self.start) * 1_000_000.0
        return False


def format_elapsed(us: float) -> str:
    """
    Human-friendly duration from a microsecond value.

        500       → "500.00 µs"
        12_345    → "12.35 ms"
        1_234_567 → "1.235 s"
        76_997_000 → "1m 16.997s"     ← the phone-stopwatch match
        185_234_000 → "3m 5.234s"
    """
    if us < 1_000:
        return f"{us:.2f} µs"
    if us < 1_000_000:
        return f"{us / 1_000:.2f} ms"

    seconds = us / 1_000_000.0
    if seconds < 60:
        return f"{seconds:.3f} s"

    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}m {remainder:.3f}s"