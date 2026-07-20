"""
KelsAI Database Manager (PostgreSQL Version)
Handles PostgreSQL database initialization and all CRUD operations.
Supports per-user isolated data via _active_user.
"""

import os
import json
from datetime import datetime
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# ── Per-user state management ───────────────────────────────────────────────
_active_user: str = "default"

def set_active_user(username: str):
    """Set the active user for all DB operations in this thread/session."""
    global _active_user
    _active_user = username.lower().replace(" ", "_")

def get_active_user() -> str:
    return _active_user

def get_connection():
    """Returns a PostgreSQL database connection with dictionary cursor."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn


def init_db():
    """Initialize all database tables and indexes in PostgreSQL."""
    conn = get_connection()
    with conn.cursor() as cur:
        # ── Profile ───────────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                name TEXT, email TEXT, phone TEXT, location TEXT,
                linkedin TEXT, github TEXT, summary TEXT, skills TEXT,
                experience TEXT, education TEXT, projects TEXT,
                certifications TEXT, resume_path TEXT, updated_at TIMESTAMP
            )
        """)

        # ── Jobs ──────────────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                job_type TEXT,
                salary TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                match_score REAL DEFAULT 0,
                match_summary TEXT,
                status TEXT DEFAULT 'new',
                applied_at TIMESTAMP,
                notes TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (username, url)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_username ON jobs(username)")

        # ── Search Preferences ────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_preferences (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                keywords TEXT, locations TEXT, job_types TEXT,
                min_salary INTEGER DEFAULT 0, experience_level TEXT,
                remote_preference TEXT, updated_at TIMESTAMP
            )
        """)

        # ── Q&A Store ─────────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS qa_store (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                question TEXT, 
                answer TEXT,
                category TEXT, 
                updated_at TIMESTAMP,
                UNIQUE (username, question)
            )
        """)

        # ── Cover Letters ─────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cover_letters (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                job_id INTEGER,
                job_title TEXT,
                company TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)

        # ── Job History / CRM Timeline ────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_history (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                job_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_job ON job_history(job_id)")

        # ── Search Cache (24-hr TTL) ───────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, cache_key)
            )
        """)

        # ── Scheduler Settings ────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_settings (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                auto_hunt_enabled INTEGER DEFAULT 0,
                hunt_hour INTEGER DEFAULT 8,
                digest_enabled INTEGER DEFAULT 0,
                digest_email TEXT,
                digest_hour INTEGER DEFAULT 9,
                smtp_host TEXT,
                smtp_port INTEGER DEFAULT 587,
                smtp_user TEXT,
                smtp_pass TEXT,
                updated_at TIMESTAMP
            )
        """)
        
        # ── User API Keys ─────────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_api_keys (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                gemini_key TEXT DEFAULT '',
                openrouter_key TEXT DEFAULT '',
                rapidapi_key TEXT DEFAULT '',
                adzuna_app_id TEXT DEFAULT '',
                adzuna_app_key TEXT DEFAULT '',
                updated_at TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()
    return True


# ─── Profile ──────────────────────────────────────────────────────────────────

def save_profile(data: dict):
    conn = get_connection()
    username = get_active_user()
    data["updated_at"] = datetime.now()
    data["username"] = username
    
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM profile WHERE username=%(username)s", {"username": username})
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE profile SET name=%(name)s, email=%(email)s, phone=%(phone)s, location=%(location)s,
                linkedin=%(linkedin)s, github=%(github)s, summary=%(summary)s, skills=%(skills)s,
                experience=%(experience)s, education=%(education)s, projects=%(projects)s,
                certifications=%(certifications)s, resume_path=%(resume_path)s, updated_at=%(updated_at)s
                WHERE username=%(username)s
            """, data)
        else:
            cur.execute("""
                INSERT INTO profile (username, name, email, phone, location, linkedin, github, summary,
                skills, experience, education, projects, certifications, resume_path, updated_at)
                VALUES (%(username)s, %(name)s, %(email)s, %(phone)s, %(location)s, %(linkedin)s, %(github)s, %(summary)s,
                %(skills)s, %(experience)s, %(education)s, %(projects)s, %(certifications)s, %(resume_path)s, %(updated_at)s)
            """, data)
    conn.commit()
    conn.close()


def get_profile() -> dict:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM profile WHERE username=%s", (username,))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Jobs ─────────────────────────────────────────────────────────────────────

def save_job(job: dict) -> bool:
    """Insert a job, ignoring duplicates by URL and username."""
    conn = get_connection()
    username = get_active_user()
    job["username"] = username
    job["discovered_at"] = job.get("discovered_at") or datetime.now()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO jobs (username, title, company, location, job_type, salary,
                description, url, source, discovered_at)
                VALUES (%(username)s, %(title)s, %(company)s, %(location)s, %(job_type)s, %(salary)s,
                %(description)s, %(url)s, %(source)s, %(discovered_at)s)
                ON CONFLICT (username, url) DO NOTHING RETURNING id
            """, job)
            row = cur.fetchone()
            inserted = bool(row)
            if inserted:
                job_id = row["id"]
                cur.execute(
                    "INSERT INTO job_history (username, job_id, event_type, note) VALUES (%s,%s,%s,%s)",
                    (username, job_id, "discovered", f"Found on {job.get('source','?')}")
                )
        conn.commit()
        return inserted
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()


def update_job_score(job_id: int, score: float, summary: str):
    conn = get_connection()
    username = get_active_user()
    with conn.cursor() as cur:
        cur.execute("UPDATE jobs SET match_score=%s, match_summary=%s WHERE id=%s AND username=%s", (score, summary, job_id, username))
    conn.commit()
    conn.close()


def update_job_status(job_id: int, status: str, notes: str = ""):
    conn = get_connection()
    username = get_active_user()
    applied_at = datetime.now() if status == "applied" else None
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status=%s, notes=%s, applied_at=%s WHERE id=%s AND username=%s",
            (status, notes, applied_at, job_id, username)
        )
        cur.execute(
            "INSERT INTO job_history (username, job_id, event_type, note) VALUES (%s,%s,%s,%s)",
            (username, job_id, f"status:{status}", notes or f"Status changed to {status}")
        )
    conn.commit()
    conn.close()


def get_all_jobs(min_score: float = 0, status_filter: str = "all") -> list:
    conn = get_connection()
    username = get_active_user()
    query = "SELECT * FROM jobs WHERE username = %s AND match_score >= %s"
    params = [username, min_score]
    if status_filter != "all":
        query += " AND status=%s"
        params.append(status_filter)
    query += " ORDER BY match_score DESC, discovered_at DESC"
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
    conn.close()
    
    # Format datetime objects back to ISO string if needed by Streamlit
    for r in rows:
        if isinstance(r.get('discovered_at'), datetime):
            r['discovered_at'] = r['discovered_at'].isoformat()
        if isinstance(r.get('applied_at'), datetime):
            r['applied_at'] = r['applied_at'].isoformat()
    return [dict(r) for r in rows]


def get_job_by_id(job_id: int) -> dict:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM jobs WHERE id=%s AND username=%s", (job_id, username))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_job_stats() -> dict:
    conn = get_connection()
    username = get_active_user()
    stats = {}
    with conn.cursor() as cur:
        for key in ["total", "new", "saved", "applied", "interview", "rejected", "offered"]:
            if key == "total":
                cur.execute("SELECT COUNT(*) FROM jobs WHERE username=%s", (username,))
                stats[key] = cur.fetchone()[0]
            else:
                cur.execute("SELECT COUNT(*) FROM jobs WHERE status=%s AND username=%s", (key, username))
                stats[key] = cur.fetchone()[0]
        # Source breakdown
        cur.execute("SELECT source, COUNT(*) as cnt FROM jobs WHERE username=%s GROUP BY source", (username,))
        rows = cur.fetchall()
        stats["by_source"] = {r[0]: r[1] for r in rows}
        # Score buckets
        cur.execute("SELECT COUNT(*) FROM jobs WHERE match_score>=85 AND username=%s", (username,))
        stats["high_match"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM jobs WHERE match_score>=70 AND match_score<85 AND username=%s", (username,))
        stats["medium_match"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM jobs WHERE match_score>0 AND match_score<70 AND username=%s", (username,))
        stats["low_match"] = cur.fetchone()[0]
    conn.close()
    return stats


# ─── Job History / CRM Timeline ───────────────────────────────────────────────

def log_job_event(job_id: int, event_type: str, note: str = ""):
    conn = get_connection()
    username = get_active_user()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO job_history (username, job_id, event_type, note, created_at) VALUES (%s,%s,%s,%s,%s)",
            (username, job_id, event_type, note, datetime.now())
        )
    conn.commit()
    conn.close()


def get_job_history(job_id: int) -> list:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM job_history WHERE job_id=%s AND username=%s ORDER BY created_at ASC", (job_id, username)
        )
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Cover Letters ────────────────────────────────────────────────────────────

def save_cover_letter(job_id: int, job_title: str, company: str, content: str):
    conn = get_connection()
    username = get_active_user()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cover_letters (username, job_id, job_title, company, content, created_at)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (username, job_id, job_title, company, content, datetime.now()))
    conn.commit()
    conn.close()


def get_cover_letters(job_id: int = None) -> list:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if job_id:
            cur.execute("SELECT * FROM cover_letters WHERE job_id=%s AND username=%s ORDER BY created_at DESC", (job_id, username))
        else:
            cur.execute("SELECT * FROM cover_letters WHERE username=%s ORDER BY created_at DESC", (username,))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Preferences ──────────────────────────────────────────────────────────────

def save_preferences(data: dict):
    conn = get_connection()
    username = get_active_user()
    data["updated_at"] = datetime.now()
    data["username"] = username
    # Ensure required keys exist
    for k in ["keywords","locations","job_types","min_salary","experience_level","remote_preference"]:
        data.setdefault(k, "" if k != "min_salary" else 0)
    
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM search_preferences WHERE username=%(username)s", {"username": username})
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE search_preferences SET keywords=%(keywords)s, locations=%(locations)s,
                job_types=%(job_types)s, min_salary=%(min_salary)s, experience_level=%(experience_level)s,
                remote_preference=%(remote_preference)s, updated_at=%(updated_at)s WHERE username=%(username)s
            """, data)
        else:
            cur.execute("""
                INSERT INTO search_preferences (username, keywords, locations, job_types, min_salary,
                experience_level, remote_preference, updated_at)
                VALUES (%(username)s, %(keywords)s, %(locations)s, %(job_types)s, %(min_salary)s, %(experience_level)s,
                %(remote_preference)s, %(updated_at)s)
            """, data)
    conn.commit()
    conn.close()


def get_preferences() -> dict:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM search_preferences WHERE username=%s", (username,))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Search Cache ─────────────────────────────────────────────────────────────

def get_cached_search(cache_key: str, ttl_hours: int = 24) -> list | None:
    """Return cached results if within TTL, else None."""
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT results, created_at FROM search_cache WHERE cache_key=%s AND username=%s", (cache_key, username)
        )
        row = cur.fetchone()
    conn.close()
    if not row:
        return None
    from datetime import datetime, timedelta
    created = row["created_at"]
    if datetime.now() - created > timedelta(hours=ttl_hours):
        return None  # Expired
    return json.loads(row["results"])


def save_search_cache(cache_key: str, results: list):
    conn = get_connection()
    username = get_active_user()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO search_cache (username, cache_key, results, created_at)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (username, cache_key) DO UPDATE SET results=EXCLUDED.results, created_at=EXCLUDED.created_at
        """, (username, cache_key, json.dumps(results), datetime.now()))
    conn.commit()
    conn.close()


# ─── Scheduler Settings ───────────────────────────────────────────────────────

def save_scheduler_settings(data: dict):
    conn = get_connection()
    username = get_active_user()
    data["updated_at"] = datetime.now()
    data["username"] = username
    
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM scheduler_settings WHERE username=%(username)s", {"username": username})
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE scheduler_settings SET
                auto_hunt_enabled=%(auto_hunt_enabled)s, hunt_hour=%(hunt_hour)s,
                digest_enabled=%(digest_enabled)s, digest_email=%(digest_email)s,
                digest_hour=%(digest_hour)s, smtp_host=%(smtp_host)s, smtp_port=%(smtp_port)s,
                smtp_user=%(smtp_user)s, smtp_pass=%(smtp_pass)s, updated_at=%(updated_at)s
                WHERE username=%(username)s
            """, data)
        else:
            cur.execute("""
                INSERT INTO scheduler_settings
                (username, auto_hunt_enabled, hunt_hour, digest_enabled, digest_email, digest_hour,
                 smtp_host, smtp_port, smtp_user, smtp_pass, updated_at)
                VALUES (%(username)s, %(auto_hunt_enabled)s, %(hunt_hour)s, %(digest_enabled)s, %(digest_email)s,
                %(digest_hour)s, %(smtp_host)s, %(smtp_port)s, %(smtp_user)s, %(smtp_pass)s, %(updated_at)s)
            """, data)
    conn.commit()
    conn.close()


def get_scheduler_settings() -> dict:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM scheduler_settings WHERE username=%s", (username,))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


# ─── Q&A ──────────────────────────────────────────────────────────────────────

def save_qa(question: str, answer: str, category: str = "general"):
    conn = get_connection()
    username = get_active_user()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO qa_store (username, question, answer, category, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username, question) DO UPDATE SET answer=EXCLUDED.answer, updated_at=EXCLUDED.updated_at
        """, (username, question, answer, category, datetime.now()))
    conn.commit()
    conn.close()


def get_all_qa() -> list:
    conn = get_connection()
    username = get_active_user()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM qa_store WHERE username=%s ORDER BY category, question", (username,))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── User API Keys ─────────────────────────────────────────────────────────

def save_user_api_keys(gemini_key: str = "", openrouter_key: str = "",
                       rapidapi_key: str = "",
                       adzuna_app_id: str = "", adzuna_app_key: str = ""):
    """Store the user's API keys in Postgres."""
    conn = get_connection()
    username = get_active_user()
    
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM user_api_keys WHERE username=%s", (username,))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE user_api_keys
                SET gemini_key=%s, openrouter_key=%s, rapidapi_key=%s,
                    adzuna_app_id=%s, adzuna_app_key=%s, updated_at=%s
                WHERE username=%s
            """, (gemini_key, openrouter_key, rapidapi_key,
                   adzuna_app_id, adzuna_app_key, datetime.now(), username))
        else:
            cur.execute("""
                INSERT INTO user_api_keys
                (username, gemini_key, openrouter_key, rapidapi_key, adzuna_app_id, adzuna_app_key, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (username, gemini_key, openrouter_key, rapidapi_key,
                   adzuna_app_id, adzuna_app_key, datetime.now()))
    conn.commit()
    conn.close()


def get_user_api_keys() -> dict:
    """Retrieve the user's stored API keys."""
    try:
        conn = get_connection()
        username = get_active_user()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM user_api_keys WHERE username=%s", (username,))
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as e:
        print(f"Error fetching API keys: {e}")
        return {}
