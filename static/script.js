const POLL_MS = 500;

const ALGO_NAMES = {
  linear: "Linear Search",
  binary: "Binary Search",
  bubble: "Bubble Sort",
  merge: "Merge Sort",
};

const ORDER_NAMES = {
  random: "Random",
  sorted: "Sorted",
  reverse: "Reverse-Sorted",
};

const KEY_NAMES = {
  song_id: "Song ID",
  title: "Title",
  artist: "Artist",
  album: "Album",
  genre: "Genre",
  year: "Year",
  duration: "Duration",
};

const el = (id) => document.getElementById(id);
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let songs = []; // the rows the server sent (at most 200)
let totalCount = 0; // how many songs the server really holds
let inBenchmark = false;
let benchJobId = null;
let benchRows = [];
let runTimerId = null;

// ---------- Flask API ----------
async function api(url, body) {
  const options =
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };

  let res;

  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new Error("Cannot reach the server. Is app.py running?");
  }

  const data = await res.json();
  if (!res.ok)
    throw new Error(data.error || "Request failed (" + res.status + ")");

  return data;
}

// asks GET /status/<id> until the job is no longer "running"
async function waitForJob(jobId, onUpdate) {
  for (;;) {
    const job = await api("/status/" + jobId);

    if (onUpdate) onUpdate(job);
    if (job.status !== "running") return job;
    await wait(POLL_MS);
  }
}

// ---------- Formatting and drawing ----------
function formatDuration(seconds) {
  return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
}

function formatTime(us) {
  if (us < 1000) return us.toFixed(1) + " \u00b5s";
  if (us < 1000000) return (us / 1000).toFixed(2) + " ms";
  return (us / 1000000).toFixed(3) + " s";
}

function loadSongs(data) {
  songs = data.songs;
  totalCount = data.count;
}

function renderTable(highlightIndex = -1) {
  const body = el("songBody");
  body.textContent = "";

  songs.forEach((s, i) => {
    const tr = document.createElement("tr");
    if (i === highlightIndex) tr.className = "match";

    for (const value of [
      s.song_id,
      s.title,
      s.artist,
      s.album,
      s.genre,
      s.year,
      formatDuration(s.duration),
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }

    body.appendChild(tr);
  });

  el("songCount").textContent =
    totalCount > songs.length
      ? "showing " +
        songs.length +
        " of " +
        totalCount.toLocaleString() +
        " songs"
      : totalCount + " songs";

  const hit = body.querySelector("tr.match");
  if (hit) hit.scrollIntoView({ block: "center" });
}

function setLastOp(title, detail, stats) {
  el("lastOpTitle").textContent = title;
  el("lastOpDetail").textContent = detail;

  const dl = el("lastOpStats");
  dl.textContent = "";

  const entries = stats ? Object.entries(stats) : [];
  dl.hidden = entries.length === 0;

  for (const [label, value] of entries) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");

    dt.textContent = label;
    dd.textContent = value;
    dl.append(dt, dd);
  }
}

function showSearchError(message) {
  el("searchError").textContent = message;
  el("searchError").hidden = message === "";
  el("searchText").classList.toggle("invalid", message !== "");
}

function setStatus(text) {
  el("statusBar").textContent = text;
}

function setBusy(busy) {
  for (const b of document.querySelectorAll("#songsView button"))
    b.disabled = busy;
}

// ---------- Running screen (live clock while a sort runs) ----------
function startRun(title, note) {
  el("tableWrap").hidden = true;
  el("runPanel").hidden = false;
  el("runTitle").textContent = title;
  el("runNote").textContent = note;
  el("runTimer").textContent = "0.000 s";

  const start = performance.now();

  runTimerId = setInterval(() => {
    el("runTimer").textContent =
      ((performance.now() - start) / 1000).toFixed(3) + " s";
  }, 50);

  setBusy(true);
}

function endRun() {
  clearInterval(runTimerId);
  runTimerId = null;

  el("runPanel").hidden = true;
  el("tableWrap").hidden = false;

  setBusy(false);
}

// ---------- Generate ----------
for (const btn of document.querySelectorAll(".size-btn")) {
  btn.addEventListener("click", async () => {
    const size = Number(btn.dataset.n);
    const order = el("order").value;

    setBusy(true);
    setStatus("Generating " + size.toLocaleString() + " songs...");

    try {
      loadSongs(await api("/generate", { size, order }));
      renderTable();

      for (const b of document.querySelectorAll(".size-btn"))
        b.classList.toggle("active", b === btn);

      setLastOp("Generate", "Made a new song list.", {
        Songs: size.toLocaleString(),
        Order: ORDER_NAMES[order],
      });

      setStatus("Generated " + size.toLocaleString() + " songs.");
    } catch (err) {
      setStatus(err.message);
    } finally {
      setBusy(false);
    }
  });
}

// ---------- Search ----------
el("searchBtn").addEventListener("click", async () => {
  const by = document.querySelector('input[name="searchBy"]:checked').value;
  const algorithm = document.querySelector(
    'input[name="searchAlgo"]:checked',
  ).value;
  const text = el("searchText").value.trim();

  if (text === "") {
    showSearchError("Type a Song ID or title first.");
    el("searchText").focus();

    return;
  }

  showSearchError("");
  setBusy(true);

  try {
    const r = await api("/search", { algorithm, by, text });
    const found = r.index >= 0;
    renderTable(found ? r.index : -1);

    let detail = found
      ? "Found " + r.song.song_id + ", " + r.song.title + "."
      : "Not found.";

    if (algorithm === "binary" && r.sorted_by !== by) {
      detail +=
        " The list is not sorted by this key, so Binary Search can give a wrong answer.";
    }

    setLastOp("Search", detail, {
      Algorithm: ALGO_NAMES[algorithm],
      Position: found ? (r.index + 1).toLocaleString() : "-",
      Comparisons: r.comparisons.toLocaleString(),
      Time: formatTime(r.time_us),
    });

    setStatus(
      found
        ? "Found at position " + (r.index + 1).toLocaleString() + "."
        : "Not found.",
    );
  } catch (err) {
    setStatus(err.message);
  } finally {
    setBusy(false);
  }
});

el("searchText").addEventListener("input", () => showSearchError(""));
el("searchText").addEventListener("keydown", (e) => {
  if (e.key === "Enter") el("searchBtn").click();
});

// ---------- Sort ----------
el("sortBtn").addEventListener("click", async () => {
  const algorithm = el("sortAlgo").value;
  const key = el("sortKey").value;
  const note =
    algorithm === "bubble"
      ? "Bubble Sort is O(n\u00b2). Please be patient."
      : "Merge Sort is O(n log n).";

  startRun(
    "Sorting " +
      totalCount.toLocaleString() +
      " songs with " +
      ALGO_NAMES[algorithm] +
      "...",
    note,
  );

  try {
    const { job_id } = await api("/sort", { algorithm, key });
    const job = await waitForJob(job_id);
    if (job.status !== "done") throw new Error(job.error || "Sort failed.");

    loadSongs(await api("/songs"));
    renderTable();
    setLastOp("Sort", "Sorted by " + KEY_NAMES[key] + ".", {
      Algorithm: ALGO_NAMES[algorithm],
      Songs: job.result.count.toLocaleString(),
      Comparisons: job.result.comparisons.toLocaleString(),
      Time: formatTime(job.result.time_us),
    });

    setStatus(
      "Sorted " +
        job.result.count.toLocaleString() +
        " songs in " +
        formatTime(job.result.time_us) +
        ".",
    );
  } catch (err) {
    setStatus(err.message);
  } finally {
    endRun();
  }
});

// ---------- Benchmark view ----------
function showView(bench) {
  inBenchmark = bench;
  el("songsView").hidden = bench;
  el("benchView").hidden = !bench;
  el("benchBtn").textContent = bench ? "Back to songs" : "Generate Report";
  setStatus(
    bench ? "Benchmark: choose a configuration and click Run." : "SONIQ ready.",
  );
}

el("benchBtn").addEventListener("click", () => showView(!inBenchmark));

function checkedValues(name) {
  return Array.from(
    document.querySelectorAll('input[name="' + name + '"]:checked'),
    (box) => box.value,
  );
}

function renderBench(job) {
  benchRows = job.rows;

  const body = el("benchBody");
  body.textContent = "";

  let done = 0;
  for (const row of job.rows) {
    if (row.status.startsWith("Done")) done++;
    const tr = document.createElement("tr");
    const cells = [
      ALGO_NAMES[row.algorithm],
      row.size.toLocaleString(),
      ORDER_NAMES[row.order],
      row.comparisons === null ? "-" : row.comparisons.toLocaleString(),
      row.time_us === null ? "-" : formatTime(row.time_us),
      row.status,
    ];

    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }

    body.appendChild(tr);
  }

  el("benchProgress").value = job.progress;
  el("benchExport").disabled = done === 0;

  return done;
}

el("benchRun").addEventListener("click", async () => {
  const sizes = checkedValues("bSize").map(Number);
  const orders = checkedValues("bOrder");
  const algos = checkedValues("bAlgo");

  if (sizes.length === 0 || orders.length === 0 || algos.length === 0) {
    el("benchStatus").textContent =
      "Pick at least one size, one order, and one algorithm.";
    return;
  }

  el("benchRun").disabled = true;
  el("benchStop").disabled = false;
  setBusy(true); // the server runs one job at a time
  try {
    const { job_id } = await api("/benchmark", { sizes, orders, algos });
    benchJobId = job_id;
    const job = await waitForJob(job_id, (j) => {
      const done = renderBench(j);

      el("benchStatus").textContent =
        "Running... " + done + " of " + j.rows.length + " done.";
    });
    const done = renderBench(job);

    el("benchStatus").textContent =
      job.status === "done"
        ? "Finished all " + job.rows.length + " runs."
        : job.status === "stopped"
          ? "Stopped. " + done + " of " + job.rows.length + " runs finished."
          : "Error: " + (job.error || "unknown");
  } catch (err) {
    el("benchStatus").textContent = err.message;
  } finally {
    benchJobId = null;
    el("benchRun").disabled = false;
    el("benchStop").disabled = true;
    setBusy(false);
  }
});

el("benchStop").addEventListener("click", async () => {
  if (benchJobId === null) return;
  el("benchStop").disabled = true;
  el("benchStatus").textContent = "Stopping after the current run finishes...";
  try {
    await api("/stop/" + benchJobId, {});
  } catch (err) {
    el("benchStatus").textContent = err.message;
  }
});

el("benchExport").addEventListener("click", () => {
  const lines = [
    ["Algorithm", "Rows", "Input Order", "Comparisons", "Time (us)", "Status"],
  ];

  for (const r of benchRows) {
    lines.push([
      ALGO_NAMES[r.algorithm],
      r.size,
      ORDER_NAMES[r.order],
      r.comparisons === null ? "" : r.comparisons,
      r.time_us === null ? "" : r.time_us.toFixed(1),
      r.status,
    ]);
  }
  const csv = lines
    .map((row) =>
      row.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(","),
    )
    .join("\n");

  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = "soniq_benchmark.csv";
  link.click();

  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
});

// ---------- Small interactions ----------
el("songBody").addEventListener("click", (e) => {
  const tr = e.target.closest("tr");
  if (!tr) return;

  const wasSelected = tr.classList.contains("selected");

  for (const row of el("songBody").querySelectorAll("tr.selected"))
    row.classList.remove("selected");

  if (!wasSelected) tr.classList.add("selected");
});

// ---------- Start ----------
(async () => {
  try {
    loadSongs(await api("/songs"));
    renderTable();
    setStatus("SONIQ ready. Loaded " + totalCount + " sample songs.");
  } catch (err) {
    setStatus(err.message);
  }
})();
