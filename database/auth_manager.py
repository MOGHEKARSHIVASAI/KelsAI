"""
KelsAI Auth Manager
Handles user registration and login with bcrypt password hashing.
All credentials stored in a shared database/auth.db file.
"""

import psycopg2
import psycopg2.extras
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _get_auth_conn():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn


def init_auth_db():
    """Create the shared users table if it doesn't exist."""
    conn = _get_auth_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()


def _sanitize_username(username: str) -> str:
    """Only allow alphanumeric + underscore, 3-20 chars."""
    return re.sub(r"[^a-zA-Z0-9_]", "", username.strip())[:20]


def register_user(username: str, password: str, display_name: str = "") -> tuple[bool, str]:
    """
    Register a new user.
    Returns (success: bool, message: str)
    """
    import bcrypt

    username = _sanitize_username(username)
    if len(username) < 3:
        return False, "Username must be at least 3 characters (letters, numbers, underscore only)."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    display = display_name.strip() or username

    try:
        conn = _get_auth_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (%s, %s, %s)",
                (username.lower(), pw_hash, display)
            )
        conn.commit()
        conn.close()
        return True, f"Account created! Welcome, {display} 🎉"
    except psycopg2.IntegrityError:
        return False, f"Username '{username}' is already taken. Try another."
    except Exception as e:
        return False, f"Registration error: {e}"


def login_user(username: str, password: str) -> tuple[bool, dict]:
    """
    Verify credentials.
    Returns (success: bool, user_dict or error_message)
    """
    import bcrypt

    username = _sanitize_username(username).lower()
    if not username:
        return False, {"error": "Invalid username."}

    try:
        conn = _get_auth_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, display_name FROM users WHERE username=%s",
                (username,)
            )
            row = cur.fetchone()

            if not row:
                conn.close()
                return False, {"error": "Username not found."}

            if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
                # Update last_login
                cur.execute(
                    "UPDATE users SET last_login=%s WHERE username=%s",
                    (datetime.now(), username)
                )
                conn.commit()
                conn.close()
                return True, {
                    "username": row["username"],
                    "display_name": row["display_name"] or row["username"],
                    "id": row["id"],
                }
            else:
                conn.close()
                return False, {"error": "Incorrect password."}
    except Exception as e:
        return False, {"error": f"Login error: {e}"}


def get_user_count() -> int:
    """Return total registered user count."""
    try:
        conn = _get_auth_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Allow user to change their password."""
    import bcrypt
    success, result = login_user(username, old_password)
    if not success:
        return False, "Current password is incorrect."
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."
    pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        conn = _get_auth_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash=%s WHERE username=%s",
                (pw_hash, username.lower())
            )
        conn.commit()
        conn.close()
        return True, "Password updated successfully."
    except Exception as e:
        return False, f"Error: {e}"
