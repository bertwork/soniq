import threading
import time

from flask import Flask, jsonify, render_template, request

from algorithms import binary_search, bubble_sort, linear_search, merge_sort, timed
from data_gen import generate_songs

app = Flask(__name__)

SIZES = (1000, 10000, 30000)
ORDERS = ("random", "sorted", "reverse")
SORT_ALGOS = {"bubble": bubble_sort, "merge": merge_sort}
SORT_KEYS = ("song_id", "title", "artist", "album", "genre", "year", "duration")
SEARCH_ALGOS = {"linear": linear_search, "binary": binary_search}
SEARCH_KEYS = ("song_id", "title")
BENCH_ALGOS = ("linear", "binary", "bubble", "merge")
MAX_ROWS_SENT = 200  # the browser only draws this many rows
SEARCH_REPEATS = 100  # one search is tiny, so the benchmark repeats and averages

state = {"songs": generate_songs(25, "random"), "sorted_by": None}
jobs = {}  # job_id -> job dictionary
lock = threading.Lock()
running = False  # only ONE job may run at a time (keeps the timings honest)
next_job_id = 1


# ---------- helpers ----------

def bad(message, code=400):
    return jsonify({"error": message}), code


def get_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def valid_list(values, allowed):
    return (
        isinstance(values, list)
        and len(values) > 0
        and all(v in allowed for v in values)
    )


def snapshot():
    songs = state["songs"]

    return {
        "count": len(songs),
        "sorted_by": state["sorted_by"],
        "songs": songs[:MAX_ROWS_SENT],
    }


def start_job(worker, initial, *args):
    """Start a background job. Returns the job id, or None if one is already running."""
    global running, next_job_id

    with lock:
        if running:
            return None

        running = True
        job_id = next_job_id
        next_job_id += 1
        job = {"status": "running", "stop": False}
        job.update(initial)
        jobs[job_id] = job

    def run():
        global running

        try:
            worker(job, *args)
            if job["status"] == "running":
                job["status"] = "done"

        except Exception as error:  # report it instead of dying silently
            job["status"] = "error"
            job["error"] = str(error)

        finally:
            with lock:
                running = False

    threading.Thread(target=run, daemon=True).start()
    return job_id


BUSY = "Another job is running. Try again when it finishes."


# ---------- pages and routes ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/songs")
def songs():
    return jsonify(snapshot())


@app.route("/generate", methods=["POST"])
def generate():
    data = get_body()
    if data is None:
        return bad("JSON body required")

    if data.get("size") not in SIZES:
        return bad("size must be 1000, 10000, or 30000")

    if data.get("order") not in ORDERS:
        return bad("order must be random, sorted, or reverse")

    if running:
        return bad(BUSY, 409)

    state["songs"] = generate_songs(data["size"], data["order"])
    state["sorted_by"] = "song_id" if data["order"] == "sorted" else None

    return jsonify(snapshot())


@app.route("/search", methods=["POST"])
def search():
    data = get_body()

    if data is None:
        return bad("JSON body required")

    if data.get("algorithm") not in SEARCH_ALGOS:
        return bad("algorithm must be linear or binary")

    if data.get("by") not in SEARCH_KEYS:
        return bad("by must be song_id or title")

    text = data.get("text")

    if not isinstance(text, str) or text.strip() == "":
        return bad("text is required")

    if running:
        return bad(BUSY, 409)

    func = SEARCH_ALGOS[data["algorithm"]]
    (index, comparisons), us = timed(func, state["songs"], data["by"], text.strip())
    result = {
        "index": index,
        "comparisons": comparisons,
        "time_us": us,
        "sorted_by": state["sorted_by"],
        "count": len(state["songs"]),
    }
    if index >= 0:
        result["song"] = state["songs"][index]
    return jsonify(result)


# ---------- sort (background job) ----------
def sort_worker(job, algorithm, key):
    songs = state["songs"][:]  # the job works on its OWN copy

    (result, comparisons), us = timed(SORT_ALGOS[algorithm], songs, key)

    state["songs"] = result
    state["sorted_by"] = key
    job["result"] = {
        "algorithm": algorithm,
        "key": key,
        "count": len(result),
        "comparisons": comparisons,
        "time_us": us,
    }


@app.route("/sort", methods=["POST"])
def sort_route():
    data = get_body()

    if data is None:
        return bad("JSON body required")

    if data.get("algorithm") not in SORT_ALGOS:
        return bad("algorithm must be bubble or merge")

    if data.get("key") not in SORT_KEYS:
        return bad("key must be one of: " + ", ".join(SORT_KEYS))

    job_id = start_job(sort_worker, {}, data["algorithm"], data["key"])

    if job_id is None:
        return bad(BUSY, 409)

    return jsonify({"job_id": job_id}), 202


# ---------- benchmark (background job) ----------
def run_row(row, data):
    """Run one benchmark row. The benchmark always uses song_id as the key."""
    algo = row["algorithm"]

    if algo in SEARCH_ALGOS:
        target = f"SNG-{row['size']:06d}"  # the biggest ID, same target for every order
        status = "Done"

        if algo == "binary" and row["order"] != "sorted":
            data = merge_sort(data[:], "song_id")[
                0
            ]  # not timed: binary search needs sorted data

            status = "Done (sorted first)"

        func = SEARCH_ALGOS[algo]
        _, comparisons = func(data, "song_id", target)

        start = time.perf_counter()

        for _ in range(SEARCH_REPEATS):
            func(data, "song_id", target)

        row["time_us"] = (time.perf_counter() - start) * 1_000_000 / SEARCH_REPEATS
        row["comparisons"] = comparisons
        
        return status

    (_, comparisons), us = timed(SORT_ALGOS[algo], data[:], "song_id")
    row["comparisons"] = comparisons
    row["time_us"] = us

    return "Done"


def benchmark_worker(job):
    rows = job["rows"]
    cached_key, cached_data = None, None
    finished = 0

    for row in rows:
        if job["stop"]:
            row["status"] = "Stopped"
            job["status"] = "stopped"
            continue

        row["status"] = "Running"
        key = (row["size"], row["order"])

        if key != cached_key:
            cached_key, cached_data = key, generate_songs(row["size"], row["order"])

        row["status"] = run_row(row, cached_data)
        finished += 1
        job["progress"] = round(100 * finished / len(rows))


@app.route("/benchmark", methods=["POST"])
def benchmark_route():
    data = get_body()

    if data is None:
        return bad("JSON body required")
    
    if not valid_list(data.get("sizes"), SIZES):
        return bad("sizes must be a list from 1000, 10000, 30000")
    
    if not valid_list(data.get("orders"), ORDERS):
        return bad("orders must be a list from random, sorted, reverse")
    
    if not valid_list(data.get("algos"), BENCH_ALGOS):
        return bad("algos must be a list from linear, binary, bubble, merge")
    

    # small sizes first, so quick results show up early
    rows = [
        {
            "algorithm": a,
            "size": s,
            "order": o,
            "comparisons": None,
            "time_us": None,
            "status": "Queued",
        }
        for s in data["sizes"]
        for o in data["orders"]
        for a in data["algos"]
    ]

    job_id = start_job(benchmark_worker, {"rows": rows, "progress": 0})

    if job_id is None:
        return bad(BUSY, 409)
    
    return jsonify({"job_id": job_id}), 202


# ---------- job status ----------
@app.route("/status/<int:job_id>")
def status(job_id):
    job = jobs.get(job_id)

    if job is None:
        return bad("job not found", 404)
    
    return jsonify(job)


@app.route("/stop/<int:job_id>", methods=["POST"])
def stop(job_id):
    job = jobs.get(job_id)

    if job is None:
        return bad("job not found", 404)
    job["stop"] = True  # a benchmark stops after the row it is on

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
