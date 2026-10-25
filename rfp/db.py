import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import Criterion, active_criteria

SEED = [
    (1, "Technical Capability", "Architecture, integrations, scalability and technical fit", 30, 10, 1),
    (2, "Implementation Plan", "Timeline, milestones, staffing, acceptance criteria and risk plan", 20, 10, 1),
    (3, "Commercial Value", "Pricing clarity, three-year total cost, assumptions and exclusions", 20, 10, 1),
    (4, "Security & Compliance", "Controls, privacy, certifications and auditability; distinguish claims from evidence", 20, 10, 1),
    (5, "Support & Experience", "Support coverage, SLA, comparable projects and references", 10, 10, 1),
]


@contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(path):
    with connect(path) as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS evaluation_criteria (
          criterion_id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
          weight REAL NOT NULL CHECK(weight >= 0), max_score REAL NOT NULL CHECK(max_score > 0),
          is_active INTEGER NOT NULL CHECK(is_active IN (0,1)));
        CREATE TABLE IF NOT EXISTS rfp_runs (
          rfp_run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, run_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS supplier_results (
          rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id), supplier_name TEXT NOT NULL,
          submission_date TEXT NOT NULL, experience_rating REAL NOT NULL, absolute_score REAL NOT NULL,
          ppi REAL NOT NULL, final_rank INTEGER NOT NULL, result_json TEXT NOT NULL,
          PRIMARY KEY(rfp_run_id, supplier_name));
        ''')
        if conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0] == 0:
            conn.executemany("INSERT INTO evaluation_criteria VALUES (?,?,?,?,?,?)", SEED)


def load_criteria(path, only_active=True):
    with connect(path) as conn:
        rows = conn.execute("SELECT * FROM evaluation_criteria ORDER BY criterion_id").fetchall()
    criteria = [Criterion(**dict(r)) for r in rows]
    return active_criteria(criteria) if only_active else criteria


def save_criteria(path, rows):
    criteria = [Criterion(**row) for row in rows]
    active_criteria(criteria)
    with connect(path) as conn:
        conn.execute("DELETE FROM evaluation_criteria")
        conn.executemany("INSERT INTO evaluation_criteria VALUES (?,?,?,?,?,?)", [
            (c.criterion_id, c.name.strip(), c.description.strip(), c.weight, c.max_score, int(c.is_active))
            for c in criteria])


def save_run(path, run):
    payload = json.dumps(run, allow_nan=False)
    with connect(path) as conn:
        conn.execute("INSERT INTO rfp_runs VALUES (?,?,?,?) ON CONFLICT(rfp_run_id) DO UPDATE SET status=excluded.status, run_json=excluded.run_json",
                     (run["rfp_run_id"], run["created_at"], run["status"], payload))
        conn.execute("DELETE FROM supplier_results WHERE rfp_run_id=?", (run["rfp_run_id"],))
        conn.executemany("INSERT INTO supplier_results VALUES (?,?,?,?,?,?,?,?)", [
            (run["rfp_run_id"], s["supplier_name"], s["submission_date"], s["experience_rating"],
             s["absolute_score"], s["ppi"], s["final_rank"], json.dumps(s, allow_nan=False))
            for s in run.get("suppliers", [])])


def list_runs(path):
    with connect(path) as conn:
        return [dict(r) for r in conn.execute("SELECT rfp_run_id,created_at,status FROM rfp_runs ORDER BY created_at DESC")]


def get_run(path, run_id):
    with connect(path) as conn:
        row = conn.execute("SELECT run_json FROM rfp_runs WHERE rfp_run_id=?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None
