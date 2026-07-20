"""
KelsAI Desktop Notifications
macOS desktop push notifications using osascript.
"""

import subprocess
import platform


def notify(title: str, message: str, subtitle: str = "KelsAI") -> bool:
    """
    Send a macOS desktop notification. Returns True on success.
    Falls back silently on non-macOS systems.
    """
    if platform.system() != "Darwin":
        print(f"[Notify] {title}: {message}")
        return False
    try:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Ping"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"[Notify] Failed: {e}")
        return False


def notify_hunt_complete(matched: int, total: int):
    notify(
        title="🎯 Job Hunt Complete!",
        message=f"Found {matched} strong matches out of {total} jobs scanned.",
    )


def notify_high_match(job_title: str, company: str, score: float):
    notify(
        title=f"⭐ {score:.0f}% Match Found!",
        message=f"{job_title} at {company}",
    )


def notify_digest_sent(to_email: str):
    notify(
        title="📧 Daily Digest Sent",
        message=f"Your morning job digest was sent to {to_email}",
    )
