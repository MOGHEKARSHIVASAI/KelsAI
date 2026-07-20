"""
KelsAI Scheduler
APScheduler-based background job runner for daily hunt and digest email.
Runs as a daemon thread — start it once at app startup.
"""

import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def _get_scheduler() -> BackgroundScheduler:
    global _scheduler
    with _lock:
        if _scheduler is None or not _scheduler.running:
            _scheduler = BackgroundScheduler(daemon=True)
            _scheduler.start()
    return _scheduler


def schedule_daily_hunt(hour: int = 8, preferences: dict = None, ai_client=None, embedding_model=None):
    """Schedule a daily automated Job Hunt at the given hour (24h)."""
    sched = _get_scheduler()

    # Remove existing job if any
    try:
        sched.remove_job("daily_hunt")
    except Exception:
        pass

    def _run_hunt():
        try:
            from agents.search_agent import search_all_sources
            from agents.matcher_agent import match_jobs_batch
            from database.db_manager import get_profile, get_preferences, save_job, update_job_score, get_all_jobs
            from agents.notifications import notify_hunt_complete

            prefs = preferences or get_preferences()
            profile = get_profile()
            if not prefs or not profile:
                return

            jobs = search_all_sources(prefs)
            for job in jobs:
                save_job(job)

            if ai_client and embedding_model:
                scored = match_jobs_batch(profile, jobs, embedding_model, ai_client, min_score=70)
                for job in scored:
                    for db_job in get_all_jobs():
                        if db_job["url"] == job.get("url"):
                            update_job_score(db_job["id"], job["match_score"], job.get("match_summary", ""))
                            break
                above = [j for j in scored if j["match_score"] >= 70]
                notify_hunt_complete(len(above), len(jobs))
            else:
                notify_hunt_complete(0, len(jobs))

            print(f"[Scheduler] Daily hunt complete at {datetime.now().isoformat()}")
        except Exception as e:
            print(f"[Scheduler] Hunt error: {e}")

    sched.add_job(
        _run_hunt,
        trigger=CronTrigger(hour=hour, minute=0),
        id="daily_hunt",
        replace_existing=True,
        name=f"Daily Job Hunt at {hour:02d}:00"
    )
    print(f"[Scheduler] Daily hunt scheduled at {hour:02d}:00 every day")


def schedule_digest_email(hour: int = 9, email: str = "", smtp_settings: dict = None):
    """Schedule a daily email digest at the given hour."""
    sched = _get_scheduler()
    try:
        sched.remove_job("daily_digest")
    except Exception:
        pass

    def _send_digest():
        try:
            from database.db_manager import get_all_jobs, get_profile
            from agents.email_agent import send_job_digest
            from agents.notifications import notify_digest_sent

            profile = get_profile()
            jobs = get_all_jobs(min_score=70, status_filter="new")
            if not jobs:
                return

            settings = smtp_settings or {}
            success, msg = send_job_digest(
                to_email=email,
                jobs=jobs,
                profile=profile,
                smtp_host=settings.get("smtp_host", "smtp.gmail.com"),
                smtp_port=settings.get("smtp_port", 587),
                smtp_user=settings.get("smtp_user", ""),
                smtp_pass=settings.get("smtp_pass", ""),
            )
            if success:
                notify_digest_sent(email)
            print(f"[Scheduler] Digest: {msg}")
        except Exception as e:
            print(f"[Scheduler] Digest error: {e}")

    sched.add_job(
        _send_digest,
        trigger=CronTrigger(hour=hour, minute=0),
        id="daily_digest",
        replace_existing=True,
        name=f"Daily Email Digest at {hour:02d}:00"
    )
    print(f"[Scheduler] Daily digest scheduled at {hour:02d}:00 every day")


def cancel_job(job_id: str):
    """Cancel a scheduled job by ID."""
    try:
        _get_scheduler().remove_job(job_id)
        return True
    except Exception:
        return False


def get_jobs_status() -> list:
    """Return list of all scheduled jobs."""
    try:
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
            }
            for job in _get_scheduler().get_jobs()
        ]
    except Exception:
        return []
