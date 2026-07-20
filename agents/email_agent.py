"""
KelsAI Email Agent
Sends daily job digest emails via SMTP (works with Gmail App Passwords).
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_job_digest(
    to_email: str,
    jobs: list,
    profile: dict,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_pass: str = "",
) -> tuple[bool, str]:
    """
    Send a daily job digest email with top matching jobs.
    Returns (success: bool, message: str)
    """
    if not to_email or not smtp_user or not smtp_pass:
        return False, "Missing email credentials"

    top_jobs = sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)[:8]
    if not top_jobs:
        return False, "No jobs to send"

    candidate_name = profile.get("name", "Candidate").split()[0]
    today = datetime.now().strftime("%B %d, %Y")

    # Build HTML body
    job_rows = ""
    for job in top_jobs:
        score = job.get("match_score", 0)
        color = "#22c55e" if score >= 85 else "#f59e0b" if score >= 70 else "#ef4444"
        job_rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;">
            <div style="font-weight:700;color:#f1f5f9;font-size:14px;">{job.get('title','')}</div>
            <div style="color:#94a3b8;font-size:12px;margin-top:2px;">🏢 {job.get('company','')} &nbsp;|&nbsp; 📍 {job.get('location','')}</div>
            {f'<div style="color:#a5b4fc;font-size:12px;margin-top:4px;">{job["match_summary"][:120]}...</div>' if job.get('match_summary') else ''}
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;white-space:nowrap;vertical-align:top;">
            <span style="background:{color}22;color:{color};border:1px solid {color}44;border-radius:99px;padding:3px 10px;font-size:12px;font-weight:700;">{score:.0f}%</span><br>
            <span style="color:#64748b;font-size:11px;">{job.get('source','')}</span>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #1e293b;vertical-align:top;">
            <a href="{job.get('url','#')}" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border-radius:6px;padding:5px 12px;text-decoration:none;font-size:12px;font-weight:600;">Apply →</a>
          </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#0a0e1a;font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;">
      <div style="max-width:640px;margin:0 auto;padding:40px 20px;">

        <!-- Header -->
        <div style="text-align:center;margin-bottom:32px;">
          <div style="font-size:28px;font-weight:900;background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:inline-block;">
            🎯 KelsAI
          </div>
          <div style="color:#64748b;font-size:13px;margin-top:6px;letter-spacing:0.1em;text-transform:uppercase;">Daily Job Digest</div>
        </div>

        <!-- Greeting -->
        <div style="background:linear-gradient(135deg,rgba(99,102,241,0.1),rgba(168,85,247,0.05));border:1px solid rgba(99,102,241,0.2);border-radius:16px;padding:24px;margin-bottom:24px;">
          <div style="color:#f1f5f9;font-size:18px;font-weight:700;">Good morning, {candidate_name}! ☀️</div>
          <div style="color:#94a3b8;font-size:14px;margin-top:6px;">
            Here are your top <strong style="color:#a5b4fc;">{len(top_jobs)} job matches</strong> for {today}.
          </div>
        </div>

        <!-- Jobs table -->
        <table style="width:100%;border-collapse:collapse;background:#111827;border:1px solid #1e293b;border-radius:12px;overflow:hidden;">
          <thead>
            <tr style="background:#0d1117;">
              <th style="text-align:left;padding:10px 16px;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Job</th>
              <th style="text-align:left;padding:10px 16px;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Match</th>
              <th style="text-align:left;padding:10px 16px;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Apply</th>
            </tr>
          </thead>
          <tbody>{job_rows}</tbody>
        </table>

        <!-- Footer -->
        <div style="text-align:center;margin-top:32px;color:#475569;font-size:12px;">
          Sent by KelsAI — Your AI Job Copilot<br>
          <span style="color:#374151;">{today}</span>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 KelsAI Daily Digest — {len(top_jobs)} new job matches ({today})"
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        return True, f"Digest sent to {to_email}"
    except Exception as e:
        return False, f"SMTP error: {e}"
