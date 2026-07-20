"""
KelsAI Database Manager
Handles SQLite database initialization and all CRUD operations.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "kelsai.db")


def get_connection():
    """Returns a database connection with row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all database tables and indexes."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Profile ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT, email TEXT, phone TEXT, location TEXT,
            linkedin TEXT, github TEXT, summary TEXT, skills TEXT,
            experience TEXT, education TEXT, projects TEXT,
            certifications TEXT, resume_path TEXT, updated_at TEXT
        )
    """)

    # ── Jobs ──────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            job_type TEXT,
            salary TEXT,
            description TEXT,
            url TEXT UNIQUE,
            source TEXT,
            match_score REAL DEFAULT 0,
            match_summary TEXT,
            status TEXT DEFAULT 'new',
            applied_at TEXT,
            notes TEXT,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for fast filtering
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score  ON jobs(match_score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")

    # ── Search Preferences ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_preferences (
            id INTEGER PRIMARY KEY,
            keywords TEXT, locations TEXT, job_types TEXT,
            min_salary INTEGER DEFAULT 0, experience_level TEXT,
            remote_preference TEXT, updated_at TEXT
        )
    """)

    # ── Q&A Store ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE, answer TEXT,
            category TEXT, updated_at TEXT
        )
    """)

    # ── Cover Letters ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cover_letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            job_title TEXT,
            company TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)

    # ── Job History / CRM Timeline ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_history_job ON job_history(job_id)")

    # ── Search Cache (24-hr TTL) ───────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            results TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Scheduler Settings ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_settings (
            id INTEGER PRIMARY KEY,
            auto_hunt_enabled INTEGER DEFAULT 0,
            hunt_hour INTEGER DEFAULT 8,
            digest_enabled INTEGER DEFAULT 0,
            digest_email TEXT,
            digest_hour INTEGER DEFAULT 9,
            smtp_host TEXT,
            smtp_port INTEGER DEFAULT 587,
            smtp_user TEXT,
            smtp_pass TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    return True


# ─── Profile ──────────────────────────────────────────────────────────────────

def save_profile(data: dict):
    conn = get_connection()
    data["updated_at"] = datetime.now().isoformat()
    existing = conn.execute("SELECT id FROM profile WHERE id=1").fetchone()
    if existing:
        conn.execute("""
            UPDATE profile SET name=:name, email=:email, phone=:phone, location=:location,
            linkedin=:linkedin, github=:github, summary=:summary, skills=:skills,
            experience=:experience, education=:education, projects=:projects,
            certifications=:certifications, resume_path=:resume_path, updated_at=:updated_at
            WHERE id=1
        """, data)
    else:
        conn.execute("""
            INSERT INTO profile (id, name, email, phone, location, linkedin, github, summary,
            skills, experience, education, projects, certifications, resume_path, updated_at)
            VALUES (1, :name, :email, :phone, :location, :linkedin, :github, :summary,
            :skills, :experience, :education, :projects, :certifications, :resume_path, :updated_at)
        """, data)
    conn.commit()
    conn.close()


def get_profile() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Jobs ─────────────────────────────────────────────────────────────────────

def save_job(job: dict) -> bool:
    """Insert a job, ignoring duplicates by URL."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs (title, company, location, job_type, salary,
            description, url, source, discovered_at)
            VALUES (:title, :company, :location, :job_type, :salary,
            :description, :url, :source, :discovered_at)
        """, job)
        conn.commit()
        inserted = conn.total_changes > 0
        if inserted:
            job_id = conn.execute("SELECT id FROM jobs WHERE url=?", (job["url"],)).fetchone()
            if job_id:
                conn.execute(
                    "INSERT INTO job_history (job_id, event_type, note) VALUES (?,?,?)",
                    (job_id[0], "discovered", f"Found on {job.get('source','?')}")
                )
                conn.commit()
        return inserted
    except Exception:
        return False
    finally:
        conn.close()


def update_job_score(job_id: int, score: float, summary: str):
    conn = get_connection()
    conn.execute("UPDATE jobs SET match_score=?, match_summary=? WHERE id=?", (score, summary, job_id))
    conn.commit()
    conn.close()


def update_job_status(job_id: int, status: str, notes: str = ""):
    conn = get_connection()
    applied_at = datetime.now().isoformat() if status == "applied" else None
    conn.execute(
        "UPDATE jobs SET status=?, notes=?, applied_at=? WHERE id=?",
        (status, notes, applied_at, job_id)
    )
    # Log the status change to history
    conn.execute(
        "INSERT INTO job_history (job_id, event_type, note) VALUES (?,?,?)",
        (job_id, f"status:{status}", notes or f"Status changed to {status}")
    )
    conn.commit()
    conn.close()


def get_all_jobs(min_score: float = 0, status_filter: str = "all") -> list:
    conn = get_connection()
    query = "SELECT * FROM jobs WHERE match_score >= ?"
    params = [min_score]
    if status_filter != "all":
        query += " AND status=?"
        params.append(status_filter)
    query += " ORDER BY match_score DESC, discovered_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job_by_id(job_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_job_stats() -> dict:
    conn = get_connection()
    stats = {}
    for key in ["total", "new", "saved", "applied", "interview", "rejected", "offered"]:
        if key == "total":
            stats[key] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        else:
            stats[key] = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE status=?", (key,)).fetchone()[0]
    # Source breakdown
    rows = conn.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source").fetchall()
    stats["by_source"] = {r["source"]: r["cnt"] for r in rows}
    # Score buckets
    stats["high_match"]   = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score>=85").fetchone()[0]
    stats["medium_match"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score>=70 AND match_score<85").fetchone()[0]
    stats["low_match"]    = conn.execute("SELECT COUNT(*) FROM jobs WHERE match_score>0 AND match_score<70").fetchone()[0]
    conn.close()
    return stats


# ─── Job History / CRM Timeline ───────────────────────────────────────────────

def log_job_event(job_id: int, event_type: str, note: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO job_history (job_id, event_type, note, created_at) VALUES (?,?,?,?)",
        (job_id, event_type, note, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_job_history(job_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM job_history WHERE job_id=? ORDER BY created_at ASC", (job_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Cover Letters ────────────────────────────────────────────────────────────

def save_cover_letter(job_id: int, job_title: str, company: str, content: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO cover_letters (job_id, job_title, company, content, created_at)
        VALUES (?,?,?,?,?)
    """, (job_id, job_title, company, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_cover_letters(job_id: int = None) -> list:
    conn = get_connection()
    if job_id:
        rows = conn.execute("SELECT * FROM cover_letters WHERE job_id=? ORDER BY created_at DESC", (job_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cover_letters ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Preferences ──────────────────────────────────────────────────────────────

def save_preferences(data: dict):
    conn = get_connection()
    data["updated_at"] = datetime.now().isoformat()
    # Ensure required keys exist
    for k in ["keywords","locations","job_types","min_salary","experience_level","remote_preference"]:
        data.setdefault(k, "" if k != "min_salary" else 0)
    existing = conn.execute("SELECT id FROM search_preferences WHERE id=1").fetchone()
    if existing:
        conn.execute("""
            UPDATE search_preferences SET keywords=:keywords, locations=:locations,
            job_types=:job_types, min_salary=:min_salary, experience_level=:experience_level,
            remote_preference=:remote_preference, updated_at=:updated_at WHERE id=1
        """, data)
    else:
        conn.execute("""
            INSERT INTO search_preferences (id, keywords, locations, job_types, min_salary,
            experience_level, remote_preference, updated_at)
            VALUES (1, :keywords, :locations, :job_types, :min_salary, :experience_level,
            :remote_preference, :updated_at)
        """, data)
    conn.commit()
    conn.close()


def get_preferences() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM search_preferences WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Search Cache ─────────────────────────────────────────────────────────────

def get_cached_search(cache_key: str, ttl_hours: int = 24) -> list | None:
    """Return cached results if within TTL, else None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT results, created_at FROM search_cache WHERE cache_key=?", (cache_key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    from datetime import datetime, timedelta
    created = datetime.fromisoformat(row["created_at"])
    if datetime.now() - created > timedelta(hours=ttl_hours):
        return None  # Expired
    return json.loads(row["results"])


def save_search_cache(cache_key: str, results: list):
    conn = get_connection()
    conn.execute("""
        INSERT INTO search_cache (cache_key, results, created_at)
        VALUES (?,?,?)
        ON CONFLICT(cache_key) DO UPDATE SET results=excluded.results, created_at=excluded.created_at
    """, (cache_key, json.dumps(results), datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ─── Scheduler Settings ───────────────────────────────────────────────────────

def save_scheduler_settings(data: dict):
    conn = get_connection()
    data["updated_at"] = datetime.now().isoformat()
    existing = conn.execute("SELECT id FROM scheduler_settings WHERE id=1").fetchone()
    if existing:
        conn.execute("""
            UPDATE scheduler_settings SET
            auto_hunt_enabled=:auto_hunt_enabled, hunt_hour=:hunt_hour,
            digest_enabled=:digest_enabled, digest_email=:digest_email,
            digest_hour=:digest_hour, smtp_host=:smtp_host, smtp_port=:smtp_port,
            smtp_user=:smtp_user, smtp_pass=:smtp_pass, updated_at=:updated_at
            WHERE id=1
        """, data)
    else:
        conn.execute("""
            INSERT INTO scheduler_settings
            (id, auto_hunt_enabled, hunt_hour, digest_enabled, digest_email, digest_hour,
             smtp_host, smtp_port, smtp_user, smtp_pass, updated_at)
            VALUES (1, :auto_hunt_enabled, :hunt_hour, :digest_enabled, :digest_email,
            :digest_hour, :smtp_host, :smtp_port, :smtp_user, :smtp_pass, :updated_at)
        """, data)
    conn.commit()
    conn.close()


def get_scheduler_settings() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM scheduler_settings WHERE id=1").fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Q&A ──────────────────────────────────────────────────────────────────────

def save_qa(question: str, answer: str, category: str = "general"):
    conn = get_connection()
    conn.execute("""
        INSERT INTO qa_store (question, answer, category, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(question) DO UPDATE SET answer=excluded.answer, updated_at=excluded.updated_at
    """, (question, answer, category, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_qa() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM qa_store ORDER BY category, question").fetchall()
    conn.close()
    return [dict(r) for r in rows]
