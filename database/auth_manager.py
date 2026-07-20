"""
KelsAI Auth Manager
Handles user registration and login with bcrypt password hashing.
All credentials stored in a shared database/auth.db file.
"""

import sqlite3
import os
import re
from datetime import datetime

AUTH_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "auth.db")


def _get_auth_conn():
    os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Create the shared users table if it doesn't exist."""
    conn = _get_auth_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
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
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username.lower(), pw_hash, display)
        )
        conn.commit()
        conn.close()
        return True, f"Account created! Welcome, {display} 🎉"
    except sqlite3.IntegrityError:
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
        row = conn.execute(
            "SELECT id, username, password_hash, display_name FROM users WHERE username=?",
            (username,)
        ).fetchone()

        if not row:
            conn.close()
            return False, {"error": "Username not found."}

        if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
            # Update last_login
            conn.execute(
                "UPDATE users SET last_login=? WHERE username=?",
                (datetime.now().isoformat(), username)
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
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
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
        conn.execute(
            "UPDATE users SET password_hash=? WHERE username=?",
            (pw_hash, username.lower())
        )
        conn.commit()
        conn.close()
        return True, "Password updated successfully."
    except Exception as e:
        return False, f"Error: {e}"
