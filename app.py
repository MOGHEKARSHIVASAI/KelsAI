"""
KelsAI — AI Job Matcher & Copilot
Complete redesign: professional, clean, modern Streamlit UI
"""

import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KelsAI — AI Job Copilot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database.db_manager import (
    init_db, save_profile, get_profile, save_job, update_job_score,
    update_job_status, get_all_jobs, get_job_stats, save_preferences,
    get_preferences, save_qa, get_all_qa,
    log_job_event, get_job_history, get_scheduler_settings, save_scheduler_settings,
    save_cover_letter, get_cover_letters
)
from agents.profile_agent import process_resume
from agents.search_agent import search_all_sources, ALL_SOURCES
from agents.matcher_agent import match_jobs_batch
from agents.cover_letter_agent import generate_cover_letter, tailor_resume_summary
from agents.skill_gap_agent import analyze_skill_gap
from agents.scheduler import schedule_daily_hunt, schedule_digest_email

init_db()

# Start background scheduler if enabled
_sched_settings = get_scheduler_settings()
if _sched_settings.get("auto_hunt_enabled"):
    schedule_daily_hunt(hour=_sched_settings.get("hunt_hour", 8))
if _sched_settings.get("digest_enabled"):
    schedule_digest_email(
        hour=_sched_settings.get("digest_hour", 9),
        email=_sched_settings.get("digest_email", ""),
        smtp_settings=_sched_settings
    )

# ─── Google Fonts + CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid rgba(99,102,241,0.15) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* ── Hide default Streamlit decoration ── */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
.stDeployButton { display: none !important; }

/* ── Main content padding ── */
.main .block-container {
    padding: 2rem 3rem 2rem 3rem !important;
    max-width: 1400px !important;
}

/* ── Radio nav styling ── */
div[data-testid="stRadio"] > label { display: none !important; }
div[data-testid="stRadio"] > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
div[data-testid="stRadio"] > div > label {
    border-radius: 8px !important;
    padding: 0.5rem 0.8rem !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: rgba(99,102,241,0.12) !important;
}

/* ── Expander ── */
.stExpander {
    border: 1px solid rgba(75,85,99,0.3) !important;
    border-radius: 12px !important;
    background: rgba(17,24,39,0.5) !important;
    margin-bottom: 0.6rem !important;
}
.stExpander > summary {
    padding: 0.8rem 1rem !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.4) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99,102,241,0.5) !important;
}

/* ── Link button ── */
.stLinkButton > a {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border-radius: 10px !important;
    border: 1px solid rgba(75,85,99,0.4) !important;
    background: rgba(17,24,39,0.8) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Multiselect ── */
.stMultiSelect > div > div {
    border-radius: 10px !important;
    border: 1px solid rgba(75,85,99,0.4) !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
    border-radius: 999px !important;
}

/* ── Status ── */
div[data-testid="stStatusWidget"] {
    border-radius: 12px !important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #6366f1 !important;
}
div[data-baseweb="underline"][aria-selected="true"] {
    background-color: #6366f1 !important;
}

/* ── Custom components ── */
.kels-logo {
    text-align: center;
    padding: 1rem 0 0.5rem 0;
}
.kels-logo h1 {
    font-size: 1.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.03em;
    margin: 0;
}
.kels-logo p {
    font-size: 0.7rem;
    color: rgba(156,163,175,0.6);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin: 0.3rem 0 0 0;
}

.page-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(75,85,99,0.2);
}
.page-header h2 {
    font-size: 1.6rem;
    font-weight: 800;
    color: #f1f5f9;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
}
.page-header p {
    font-size: 0.88rem;
    color: rgba(148,163,184,0.8);
    margin: 0;
}

.stat-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(168,85,247,0.04) 100%);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 14px;
    padding: 1.1rem 1rem;
    text-align: center;
}
.stat-card .val {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}
.stat-card .lbl {
    font-size: 0.72rem;
    font-weight: 600;
    color: rgba(148,163,184,0.7);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.3rem;
}

.job-card {
    background: rgba(17,24,39,0.7);
    border: 1px solid rgba(55,65,81,0.5);
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 0.8rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s ease;
}
.job-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #6366f1, #a855f7);
}
.job-card:hover { border-color: rgba(99,102,241,0.4); }
.job-card .jc-title {
    font-size: 0.97rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 0.2rem 0;
}
.job-card .jc-company {
    font-size: 0.83rem;
    color: rgba(148,163,184,0.85);
    margin: 0 0 0.5rem 0;
}
.job-card .jc-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.5rem;
}

.chip {
    display: inline-flex;
    align-items: center;
    padding: 0.15rem 0.6rem;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.4;
}
.chip-source { background: rgba(99,102,241,0.12); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.25); }
.chip-loc    { background: rgba(16,185,129,0.10); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.2); }
.chip-type   { background: rgba(245,158,11,0.10); color: #fcd34d; border: 1px solid rgba(245,158,11,0.2); }

.score-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.65rem;
    border-radius: 99px;
    font-size: 0.82rem;
    font-weight: 700;
}
.score-hi { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.score-md { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.score-lo { background: rgba(239,68,68,0.15);  color: #f87171; border: 1px solid rgba(239,68,68,0.3); }

.status-pill {
    display: inline-flex; align-items: center;
    padding: 0.15rem 0.6rem; border-radius: 99px;
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
}
.sp-new      { background:rgba(99,102,241,0.12); color:#818cf8; border:1px solid rgba(99,102,241,0.25); }
.sp-saved    { background:rgba(14,165,233,0.12); color:#38bdf8; border:1px solid rgba(14,165,233,0.25); }
.sp-applied  { background:rgba(16,185,129,0.12); color:#34d399; border:1px solid rgba(16,185,129,0.25); }
.sp-interview{ background:rgba(245,158,11,0.12); color:#fbbf24; border:1px solid rgba(245,158,11,0.25); }
.sp-rejected { background:rgba(239,68,68,0.12);  color:#f87171; border:1px solid rgba(239,68,68,0.25); }
.sp-offered  { background:rgba(167,139,250,0.12);color:#c084fc; border:1px solid rgba(167,139,250,0.25);}

.ai-summary {
    background: rgba(99,102,241,0.06);
    border-left: 3px solid rgba(99,102,241,0.4);
    border-radius: 0 8px 8px 0;
    padding: 0.65rem 0.9rem;
    font-size: 0.83rem;
    color: rgba(203,213,225,0.85);
    line-height: 1.6;
    margin-top: 0.6rem;
}

.section-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(148,163,184,0.6);
    margin: 1.2rem 0 0.6rem 0;
}

.ai-status-on  { background:rgba(16,185,129,0.1); color:#34d399; border:1px solid rgba(16,185,129,0.25);
                  border-radius:8px; padding:0.5rem 0.8rem; font-size:0.8rem; font-weight:600; text-align:center; }
.ai-status-off { background:rgba(239,68,68,0.1); color:#f87171; border:1px solid rgba(239,68,68,0.25);
                  border-radius:8px; padding:0.5rem 0.8rem; font-size:0.8rem; font-weight:600; text-align:center; }

.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    color: rgba(148,163,184,0.5);
    font-size: 0.9rem;
}
.empty-state .icon { font-size: 3rem; margin-bottom: 0.8rem; }
.empty-state .msg  { font-weight: 600; color: rgba(148,163,184,0.7); margin-bottom: 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────────────
for k, v in [("ai_client", None), ("embedding_model", None), ("ai_ready", False)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="kels-logo">
        <h1>🎯 KelsAI</h1>
        <p>Your AI Job Copilot</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "Navigation",
        ["🏠  Dashboard", "📄  My Profile", "⚙️  Preferences",
         "🔍  Job Hunt", "📋  Applications", "📊  Analytics", 
         "📝  Cover Letters", "🎯  Skill Gap", "💬  Q&A Prep", "⏰  Scheduler"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown('<p class="section-label">AI Connection</p>', unsafe_allow_html=True)

    provider = st.selectbox("Provider", ["Gemini", "OpenRouter"], label_visibility="collapsed")
    api_key = st.text_input(
        "API Key",
        value=os.getenv("GEMINI_API_KEY" if provider == "Gemini" else "OPENROUTER_API_KEY", ""),
        type="password",
        placeholder="Enter your API key...",
        label_visibility="collapsed"
    )

    if st.button("⚡ Connect AI", use_container_width=True, type="primary"):
        with st.spinner("Connecting..."):
            try:
                from agents.ai_client import get_ai_client
                st.session_state.ai_client = get_ai_client(provider=provider.lower(), api_key=api_key)
                st.session_state.ai_client.generate_content("Say OK.")
                if st.session_state.embedding_model is None:
                    with st.spinner("Loading embeddings..."):
                        from sentence_transformers import SentenceTransformer
                        st.session_state.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                st.session_state.ai_ready = True
                st.success("Connected!")
            except Exception as e:
                st.error(f"Failed: {e}")

    if st.session_state.ai_ready:
        st.markdown('<div class="ai-status-on">✅ AI Ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-status-off">⚪ Not Connected</div>', unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def score_class(s):
    return "score-hi" if s >= 85 else "score-md" if s >= 70 else "score-lo"

def status_class(s):
    return f"sp-{s}" if s in ("new","saved","applied","interview","rejected","offered") else "sp-new"

def render_job_card(job, show_summary=True):
    score = job.get("match_score", 0)
    sc = score_class(score)
    status = job.get("status", "new")
    st.markdown(f"""
    <div class="job-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;">
            <div style="flex:1;min-width:0;">
                <div class="jc-title">{job.get('title','')}</div>
                <div class="jc-company">🏢 {job.get('company','Unknown')}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem;flex-shrink:0;">
                <span class="score-badge {sc}">{score:.0f}%</span>
                <span class="status-pill {status_class(status)}">{status}</span>
            </div>
        </div>
        <div class="jc-meta">
            <span class="chip chip-source">📌 {job.get('source','')}</span>
            <span class="chip chip-loc">📍 {job.get('location','')}</span>
            {'<span class="chip chip-type">⏰ ' + job.get('job_type','') + '</span>' if job.get('job_type') else ''}
        </div>
        {f'<div class="ai-summary">💡 {job["match_summary"]}</div>' if show_summary and job.get("match_summary") else ''}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Dashboard":
    st.markdown('<div class="page-header"><h2>🏠 Dashboard</h2><p>Your job search overview at a glance</p></div>', unsafe_allow_html=True)

    stats = get_job_stats()
    profile = get_profile()
    prefs = get_preferences()

    # Stats row
    stat_items = [
        ("Total Found", stats["total"]),
        ("New", stats["new"]),
        ("Saved", stats["saved"]),
        ("Applied", stats["applied"]),
        ("Interview", stats["interview"]),
        ("Rejected", stats["rejected"]),
        ("Offered", stats["offered"]),
    ]
    cols = st.columns(7)
    for col, (lbl, val) in zip(cols, stat_items):
        col.markdown(f'<div class="stat-card"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown('<p class="section-label">🔥 Top Matching Jobs</p>', unsafe_allow_html=True)
        top_jobs = get_all_jobs(min_score=70)[:5]
        if top_jobs:
            for job in top_jobs:
                render_job_card(job, show_summary=False)
        else:
            st.markdown('<div class="empty-state"><div class="icon">🔍</div><div class="msg">No high-match jobs yet</div>Run a Job Hunt to discover matches!</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<p class="section-label">👤 Your Profile</p>', unsafe_allow_html=True)
        if profile:
            st.markdown(f"""
            <div class="job-card">
                <div class="jc-title">{profile.get('name','—')}</div>
                <div class="jc-company">✉️ {profile.get('email','—')}</div>
                <div class="jc-meta">
                    <span class="chip chip-loc">📍 {profile.get('location','—')}</span>
                </div>
                <div style="font-size:0.8rem;color:rgba(148,163,184,0.75);line-height:1.5;">
                    <b>Skills:</b> {(profile.get('skills','') or '—')[:120]}{'...' if len(profile.get('skills',''))>120 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No profile found. Upload your resume in **My Profile**.")

        st.markdown('<p class="section-label">🔍 Search Settings</p>', unsafe_allow_html=True)
        if prefs:
            st.markdown(f"""
            <div class="job-card">
                <div style="font-size:0.84rem;color:rgba(203,213,225,0.85);line-height:1.8;">
                    <b>Keywords:</b> {prefs.get('keywords','—')}<br>
                    <b>Location:</b> {prefs.get('locations','—')}<br>
                    <b>Remote:</b> {prefs.get('remote_preference','—')}<br>
                    <b>Level:</b> {prefs.get('experience_level','—')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No preferences set. Go to **Preferences**.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📄  My Profile":
    st.markdown('<div class="page-header"><h2>📄 My Profile</h2><p>Upload your resume and let AI build your profile automatically</p></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📤  Upload Resume (AI)", "✏️  Edit Manually"])

    with tab1:
        col1, col2 = st.columns([3, 2], gap="large")
        with col1:
            uploaded = st.file_uploader("Drop your PDF resume here", type=["pdf"], key="resume_uploader")
            if uploaded:
                resume_dir = os.path.join(os.path.dirname(__file__), "data")
                os.makedirs(resume_dir, exist_ok=True)
                resume_path = os.path.join(resume_dir, "base_resume.pdf")
                with open(resume_path, "wb") as f:
                    f.write(uploaded.getvalue())
                st.success(f"✅ **{uploaded.name}** uploaded successfully")

                if st.button("🤖 Parse with Gemini AI", use_container_width=True, type="primary", key="parse_btn"):
                    if not st.session_state.ai_ready:
                        st.error("Please connect AI first (sidebar).")
                    else:
                        with st.spinner("AI is reading your resume..."):
                            try:
                                from agents.profile_agent import process_resume
                                profile = process_resume(resume_path, st.session_state.ai_client)
                                save_profile(profile)
                                st.success("✅ Resume parsed and saved!")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Error: {e}")

        with col2:
            profile = get_profile()
            if profile:
                st.markdown(f"""
                <div class="job-card">
                    <div class="jc-title">{profile.get('name','—')}</div>
                    <div class="jc-company">✉️ {profile.get('email','—')}</div>
                    <div class="jc-meta">
                        <span class="chip chip-loc">📍 {profile.get('location','—')}</span>
                    </div>
                    <div style="font-size:0.82rem;color:rgba(148,163,184,0.8);margin-top:0.5rem;">
                        <b>Skills:</b> {(profile.get('skills','') or '—')[:200]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Upload your resume to see a preview here.")

    with tab2:
        profile = get_profile()
        with st.form("profile_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Full Name", value=profile.get("name",""), placeholder="e.g. Shivasai Moghekar")
                email = st.text_input("Email", value=profile.get("email",""))
                phone = st.text_input("Phone", value=profile.get("phone",""))
                location = st.text_input("Location", value=profile.get("location",""), placeholder="e.g. Hyderabad, India")
            with c2:
                linkedin = st.text_input("LinkedIn URL", value=profile.get("linkedin",""))
                github = st.text_input("GitHub URL", value=profile.get("github",""))
                certifications = st.text_input("Certifications", value=profile.get("certifications",""))

            summary = st.text_area("Professional Summary", value=profile.get("summary",""), height=90)
            skills = st.text_area("Skills (comma-separated)", value=profile.get("skills",""), height=70,
                                  help="e.g. Python, Flask, React, GCP, Machine Learning, Docker, PostgreSQL")
            c3, c4 = st.columns(2)
            with c3:
                experience = st.text_area("Experience", value=profile.get("experience","[]"), height=100)
                projects = st.text_area("Projects", value=profile.get("projects","[]"), height=80)
            with c4:
                education = st.text_area("Education", value=profile.get("education","[]"), height=100)

            if st.form_submit_button("💾 Save Profile", use_container_width=True, type="primary"):
                save_profile({"name":name,"email":email,"phone":phone,"location":location,
                              "linkedin":linkedin,"github":github,"summary":summary,"skills":skills,
                              "experience":experience,"education":education,"projects":projects,
                              "certifications":certifications,"resume_path":profile.get("resume_path","")})
                st.success("✅ Profile saved!")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️  Preferences":
    st.markdown('<div class="page-header"><h2>⚙️ Job Search Preferences</h2><p>Configure exactly what kind of jobs KelsAI should hunt for you</p></div>', unsafe_allow_html=True)
    prefs = get_preferences()

    with st.form("prefs_form"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            keywords = st.text_input(
                "Job Keywords *",
                value=prefs.get("keywords",""),
                placeholder="e.g. Python Developer, Backend Engineer, ML Engineer",
                help="Comma-separated. These are used to search job boards AND filter results."
            )
            locations = st.text_input(
                "Preferred Locations",
                value=prefs.get("locations",""),
                placeholder="e.g. Hyderabad, Bangalore, Remote"
            )
            remote_pref = st.selectbox(
                "Remote Preference",
                ["Remote", "Hybrid", "On-site", "Any"],
                index=["Remote","Hybrid","On-site","Any"].index(prefs.get("remote_preference","Remote"))
                if prefs.get("remote_preference") in ["Remote","Hybrid","On-site","Any"] else 0
            )
        with c2:
            experience_level = st.selectbox(
                "Experience Level",
                ["Entry-level", "Mid-level", "Senior", "Lead", "Manager"],
                index=["Entry-level","Mid-level","Senior","Lead","Manager"].index(
                    prefs.get("experience_level","Mid-level"))
                if prefs.get("experience_level") in ["Entry-level","Mid-level","Senior","Lead","Manager"] else 1
            )
            job_types = st.multiselect(
                "Job Types",
                ["Full-time","Part-time","Contract","Internship","Freelance"],
                default=[t.strip() for t in prefs.get("job_types","Full-time").split(",") if t.strip()]
            )
            min_salary = st.number_input("Min. Salary (₹ LPA / $k/yr)", value=int(prefs.get("min_salary",0)), min_value=0, step=1)

        st.info("💡 **Tip:** Be specific with keywords. Instead of just 'Python', use 'Python Developer' or 'Python Backend Engineer' to get more relevant job matches.")

        if st.form_submit_button("💾 Save Preferences", use_container_width=True, type="primary"):
            save_preferences({"keywords":keywords,"locations":locations,"job_types":", ".join(job_types),
                              "min_salary":min_salary,"experience_level":experience_level,"remote_preference":remote_pref})
            st.success("✅ Preferences saved!")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: JOB HUNT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍  Job Hunt":
    st.markdown('<div class="page-header"><h2>🔍 Job Hunt</h2><p>Search, score and discover jobs matched to your profile</p></div>', unsafe_allow_html=True)

    profile = get_profile()
    prefs = get_preferences()

    # ── Status row ─────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1, 1], gap="medium")
    with c1:
        min_score = st.slider("Minimum Match Score to Show", 0, 100, 70, key="hunt_min_score",
                              help="Jobs below this score won't be shown in results")
    with c2:
        st.metric("Profile", "✅ Ready" if profile else "❌ Missing")
    with c3:
        st.metric("AI Engine", "✅ Ready" if st.session_state.ai_ready else "❌ Disconnected")

    # ── Keywords quick-set ─────────────────────────────────────────────────────
    saved_keywords = (prefs.get("keywords", "") if prefs else "").strip()
    st.markdown('<p class="section-label">🔑 Job Keywords</p>', unsafe_allow_html=True)
    quick_keywords = st.text_input(
        "Keywords",
        value=saved_keywords,
        placeholder="e.g. Python Developer, Backend Engineer, Full Stack Developer",
        key="quick_keywords",
        help="Comma-separated. Used to search AND filter jobs. More specific = better results.",
        label_visibility="collapsed",
    )
    if quick_keywords.strip() and quick_keywords.strip() != saved_keywords:
        updated_prefs = prefs.copy() if prefs else {}
        updated_prefs["keywords"] = quick_keywords.strip()
        save_preferences(updated_prefs)
        prefs = updated_prefs
        st.caption("✅ Keywords saved")

    # ── Source selector ────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">🌐 Select Job Sources</p>', unsafe_allow_html=True)
    source_info = {
        "LinkedIn":       "🔵 LinkedIn — India-targeted search",
        "Remotive":       "🟢 Remotive — Remote tech jobs",
        "Arbeitnow":      "🟡 Arbeitnow — European & global roles",
        "Himalayas":      "🟣 Himalayas — Remote-first companies",
        "WeWorkRemotely": "🔴 We Work Remotely — Developer board",
    }
    selected_sources = st.multiselect(
        "Sources",
        options=ALL_SOURCES,
        default=ALL_SOURCES,
        format_func=lambda s: source_info.get(s, s),
        key="hunt_sources",
        label_visibility="collapsed",
    )
    if not selected_sources:
        st.warning("⚠️ Select at least one source.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Start button ───────────────────────────────────────────────────────────
    hunt_ready = bool(selected_sources)
    if st.button("🚀 Start Job Hunt", use_container_width=True, type="primary",
                 key="start_hunt_btn", disabled=not hunt_ready):

        # Validation checks
        keywords_to_use = (prefs.get("keywords", "") if prefs else "").strip()
        if not profile:
            st.error("❌ Complete your profile first — go to **📄 My Profile**.")
        elif not keywords_to_use:
            st.error("❌ Please type your job keywords in the field above, then click **Start Job Hunt** again.")
        elif not st.session_state.ai_ready:
            st.error("❌ Connect your AI first — enter your API key in the sidebar and click **⚡ Connect AI**.")
        else:
            with st.status("🔍 Hunting for jobs...", expanded=True) as hunt_status:
                log_box = st.empty()
                log_lines = []

                def ui_log(msg):
                    log_lines.append(msg)
                    log_box.markdown("\n\n".join(log_lines[-10:]))

                jobs = search_all_sources(prefs, log_fn=ui_log, enabled_sources=selected_sources)
                st.write(f"✅ **{len(jobs)}** unique listings collected")

                new_count = sum(1 for job in jobs if save_job(job))
                st.write(f"💾 **{new_count}** new jobs saved to database")

                st.write("🤖 Scoring jobs against your profile...")
                prog = st.progress(0)
                prog_text = st.empty()

                scored = match_jobs_batch(
                    profile=profile, jobs=jobs,
                    embedding_model=st.session_state.embedding_model,
                    ai_client=st.session_state.ai_client,
                    min_score=min_score,
                    progress_callback=lambda p, m: (prog.progress(p), prog_text.text(m))
                )

                for job in scored:
                    for db_job in get_all_jobs():
                        if db_job["url"] == job.get("url"):
                            update_job_score(db_job["id"], job["match_score"], job.get("match_summary", ""))
                            break

                above = [j for j in scored if j["match_score"] >= min_score]
                hunt_status.update(label=f"✅ Done! Found {len(above)} strong matches.", state="complete")

            st.success(f"🎉 Found **{len(above)}** jobs above {min_score}% match. Go to **📋 Applications** to review!")
            st.balloons()


    # ── Recent results ────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">📋 Recent Results</p>', unsafe_allow_html=True)
    recent_jobs = get_all_jobs(min_score=0)[:30]
    if recent_jobs:
        # Source breakdown
        from collections import Counter
        src_counts = Counter(j.get("source","?") for j in recent_jobs)
        src_cols = st.columns(len(src_counts))
        for col, (src, cnt) in zip(src_cols, src_counts.items()):
            col.metric(src, cnt)
        st.markdown("<br>", unsafe_allow_html=True)
        for job in recent_jobs:
            render_job_card(job)
    else:
        st.markdown('<div class="empty-state"><div class="icon">🔍</div><div class="msg">No jobs found yet</div>Click Start Job Hunt to begin!</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: APPLICATIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋  Applications":
    st.markdown('<div class="page-header"><h2>📋 Application Tracker</h2><p>Track every job from discovery to offer</p></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([2, 1, 1, 2], gap="small")
    with c1:
        status_filter = st.selectbox(
            "Status", ["all","new","saved","applied","interview","rejected","offered"],
            format_func=lambda s: {"all":"All Statuses","new":"🆕 New","saved":"💾 Saved",
                                    "applied":"📤 Applied","interview":"📅 Interview",
                                    "rejected":"❌ Rejected","offered":"🎉 Offered"}.get(s, s),
            key="app_status_filter", label_visibility="collapsed"
        )
    with c2:
        min_score_filter = st.slider("Min %", 0, 100, 0, key="app_min_score", label_visibility="collapsed")
    with c3:
        source_filter = st.multiselect("Source", ALL_SOURCES, placeholder="All sources",
                                        key="app_source_filter", label_visibility="collapsed")
    with c4:
        search_q = st.text_input("Search jobs...", placeholder="🔎 Filter by title or company...",
                                  key="app_search", label_visibility="collapsed")

    jobs = get_all_jobs(min_score=min_score_filter, status_filter=status_filter)
    if source_filter:
        jobs = [j for j in jobs if j.get("source") in source_filter]
    if search_q:
        q = search_q.lower()
        jobs = [j for j in jobs if q in j.get("title","").lower() or q in j.get("company","").lower()]

    st.caption(f"**{len(jobs)}** jobs matching filters")
    st.divider()

    if not jobs:
        st.markdown('<div class="empty-state"><div class="icon">📋</div><div class="msg">No jobs here yet</div>Run a Job Hunt to populate this list.</div>', unsafe_allow_html=True)
    else:
        for job in jobs:
            score = job.get("match_score", 0)
            sc = score_class(score)
            status = job.get("status","new")
            icon = "🟢" if score>=85 else "🟡" if score>=70 else "🔴"

            with st.expander(f"{icon} **{job['title']}** — {job.get('company','Unknown')}  |  {score:.0f}% match"):
                cl, cr = st.columns([3, 1], gap="large")
                with cl:
                    st.markdown(f"""
                    <div class="jc-meta">
                        <span class="chip chip-source">📌 {job.get('source','')}</span>
                        <span class="chip chip-loc">📍 {job.get('location','')}</span>
                        <span class="chip chip-type">⏰ {job.get('job_type','')}</span>
                        <span class="status-pill {status_class(status)}">{status}</span>
                    </div>
                    {f'<div class="ai-summary">💡 {job["match_summary"]}</div>' if job.get("match_summary") else ''}
                    """, unsafe_allow_html=True)

                    tabs = st.tabs(["📝 Description", "⏱️ History / CRM", "⚙️ Actions"])
                    with tabs[0]:
                        st.text(job.get("description","No description available.")[:3000])
                    with tabs[1]:
                        hist = get_job_history(job["id"])
                        if not hist:
                            st.caption("No history logged yet.")
                        else:
                            for h in hist:
                                ts = datetime.fromisoformat(h["created_at"]).strftime("%b %d, %H:%M")
                                st.markdown(f"**{ts}** — `{h['event_type']}`: {h['note']}")
                    with tabs[2]:
                        if job.get("url"):
                            st.link_button("🔗 Open & Apply", job["url"], use_container_width=True)

                        new_status = st.selectbox(
                            "Status", ["new","saved","applied","interview","rejected","offered"],
                            index=["new","saved","applied","interview","rejected","offered"].index(status),
                            key=f"st_{job['id']}", label_visibility="collapsed"
                        )
                        notes = st.text_input("Notes", value=job.get("notes","") or "",
                                              key=f"notes_{job['id']}", placeholder="Add notes...",
                                              label_visibility="collapsed")
                        
                        col_a, col_b = st.columns(2)
                        if col_a.button("💾 Update", key=f"upd_{job['id']}", use_container_width=True):
                            update_job_status(job["id"], new_status, notes)
                            st.success("Updated!")
                            st.rerun()
                        if new_status == "interview" and col_b.button("🔔 Set Reminder", key=f"rem_{job['id']}", use_container_width=True):
                            from agents.notifications import notify
                            notify("Interview Reminder Set", f"Reminder set for {job['company']}")
                            log_job_event(job["id"], "reminder", "User requested reminder")
                            st.success("macOS Reminder Sent!")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Q&A PREP
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💬  Q&A Prep":
    st.markdown('<div class="page-header"><h2>💬 Application Q&A Prep</h2><p>Generate AI-powered answers to common job application questions</p></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🤖  Generate Answer", "📚  My Answer Bank"])

    with tab1:
        profile = get_profile()
        c1, c2 = st.columns([3, 1], gap="large")
        with c1:
            question = st.text_area("Application Question", height=100,
                                     placeholder="e.g. Why should we hire you?\ne.g. Describe your experience with Python.\ne.g. What is your expected salary?")
        with c2:
            category = st.selectbox("Category", ["General","Behavioral","Technical","Salary","Personal"])
            st.markdown("<br>", unsafe_allow_html=True)
            gen_btn = st.button("✨ Generate", use_container_width=True, type="primary", key="gen_qa")

        if gen_btn:
            if not question.strip():
                st.error("Please enter a question.")
            elif not st.session_state.ai_ready:
                st.error("Connect AI first.")
            else:
                with st.spinner("Generating your personalized answer..."):
                    prompt = f"""You are an expert career counselor. Help this job applicant answer an application question.

Candidate Profile:
- Name: {profile.get('name','the applicant')}
- Skills: {profile.get('skills','Python, React, Cloud')}
- Summary: {profile.get('summary','')}
- Experience: {profile.get('experience','')}

Question: {question}

Write a professional, confident, 3-5 sentence answer in first person. Make it specific to the candidate's profile. Do not use bullet points."""
                    try:
                        resp = st.session_state.ai_client.generate_content(prompt)
                        answer = resp.text.strip()
                        st.markdown('<p class="section-label">✅ Generated Answer</p>', unsafe_allow_html=True)
                        st.markdown(f'<div class="ai-summary" style="font-size:0.9rem;">{answer}</div>', unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("💾 Save to Answer Bank", key="save_qa_btn"):
                            save_qa(question, answer, category.lower())
                            st.success("✅ Saved!")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab2:
        qa_list = get_all_qa()
        if not qa_list:
            st.markdown('<div class="empty-state"><div class="icon">💬</div><div class="msg">No saved answers yet</div>Generate some answers above to build your bank!</div>', unsafe_allow_html=True)
        else:
            for qa in qa_list:
                with st.expander(f"❓ {qa['question'][:80]}{'...' if len(qa['question'])>80 else ''}"):
                    st.caption(f"Category: `{qa.get('category','general')}`")
                    st.markdown(f'<div class="ai-summary">{qa["answer"]}</div>', unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"del_{qa['id']}"):
                        from database.db_manager import get_connection
                        c = get_connection()
                        c.execute("DELETE FROM qa_store WHERE id=?", (qa['id'],))
                        c.commit(); c.close()
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊  Analytics":
    st.markdown('<div class="page-header"><h2>📊 Analytics Dashboard</h2><p>Insights on your job search performance</p></div>', unsafe_allow_html=True)
    
    stats = get_job_stats()
    if stats["total"] == 0:
        st.info("No data available yet. Run a job hunt to get started.")
    else:
        import plotly.graph_objects as go
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="section-label">Funnel</p>', unsafe_allow_html=True)
            funnel_fig = go.Figure(go.Funnel(
                y=["Found", "Saved", "Applied", "Interview", "Offered"],
                x=[stats["total"], stats["saved"], stats["applied"], stats["interview"], stats["offered"]],
                marker={"color": ["#3b82f6", "#8b5cf6", "#f59e0b", "#06b6d4", "#22c55e"]}
            ))
            funnel_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f1f5f9"))
            st.plotly_chart(funnel_fig, use_container_width=True)
            
        with c2:
            st.markdown('<p class="section-label">Source Performance</p>', unsafe_allow_html=True)
            sources = list(stats["by_source"].keys())
            counts = list(stats["by_source"].values())
            pie_fig = go.Figure(go.Pie(labels=sources, values=counts, hole=0.4, marker=dict(colors=["#3b82f6", "#22c55e", "#eab308", "#a855f7", "#ef4444"])))
            pie_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#f1f5f9"))
            st.plotly_chart(pie_fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: COVER LETTERS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📝  Cover Letters":
    st.markdown('<div class="page-header"><h2>📝 Cover Letters</h2><p>AI-generated tailored cover letters</p></div>', unsafe_allow_html=True)
    
    jobs = get_all_jobs(status_filter="saved") + get_all_jobs(status_filter="applied")
    if not jobs:
        st.info("Save or apply to some jobs first to generate cover letters for them.")
    else:
        st.markdown('<p class="section-label">Generate New</p>', unsafe_allow_html=True)
        sel_job = st.selectbox("Select a Job", jobs, format_func=lambda j: f"{j['company']} - {j['title']}")
        
        if st.button("✨ Generate Cover Letter", type="primary", disabled=not st.session_state.ai_ready):
            with st.spinner("Generating highly tailored cover letter..."):
                cl = generate_cover_letter(get_profile(), sel_job, st.session_state.ai_client)
                save_cover_letter(sel_job["id"], sel_job["title"], sel_job["company"], cl)
                st.success("Cover letter generated!")
                st.rerun()
                
    st.divider()
    st.markdown('<p class="section-label">Saved Letters</p>', unsafe_allow_html=True)
    cls = get_cover_letters()
    if not cls:
        st.caption("No cover letters generated yet.")
    else:
        for cl in cls:
            with st.expander(f"📄 {cl['company']} - {cl['job_title']} ({datetime.fromisoformat(cl['created_at']).strftime('%b %d')})"):
                st.markdown(f'<div style="white-space:pre-wrap;background:#1e293b;padding:15px;border-radius:8px;font-size:0.9rem;">{cl["content"]}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SKILL GAP
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🎯  Skill Gap":
    st.markdown('<div class="page-header"><h2>🎯 Skill Gap Analyzer</h2><p>Identify missing skills and get learning resources</p></div>', unsafe_allow_html=True)
    
    jobs = get_all_jobs(min_score=70)
    if not jobs:
        st.info("Run a job hunt first to find jobs to analyze.")
    else:
        sel_job = st.selectbox("Select a highly-matched Job", jobs, format_func=lambda j: f"{j['company']} - {j['title']} ({j['match_score']:.0f}%)")
        if st.button("🔍 Analyze Gap", type="primary", disabled=not st.session_state.ai_ready):
            with st.spinner("Analyzing JD against your profile..."):
                res = analyze_skill_gap(get_profile(), sel_job, st.session_state.ai_client)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Overall Readiness", f"{res.get('overall_readiness', 0)}%")
                    st.success(f"**Matching Skills:** {', '.join(res.get('matching_skills', []))}")
                with c2:
                    st.info(f"**Summary:** {res.get('summary', '')}")
                    
                st.markdown("### Missing Skills & Resources")
                for missing in res.get("missing_skills", []):
                    st.error(f"❌ {missing}")
                    links = res.get("resources", {}).get(missing)
                    if links:
                        st.markdown(f"- 📖 [Documentation]({links['docs']})  |  🎥 [Video Tutorial]({links['video']})")
                    else:
                        st.caption("Search YouTube for tutorials on this topic.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⏰  Scheduler":
    st.markdown('<div class="page-header"><h2>⏰ Automation Scheduler</h2><p>Run job hunts and get email digests automatically</p></div>', unsafe_allow_html=True)
    
    settings = get_scheduler_settings()
    
    with st.form("scheduler_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🤖 Auto Hunt")
            st.caption("Runs Job Hunt automatically every day.")
            auto_hunt = st.checkbox("Enable Auto Hunt", value=bool(settings.get("auto_hunt_enabled")))
            hunt_hour = st.slider("Hour (24h)", 0, 23, int(settings.get("hunt_hour", 8)))
            
        with c2:
            st.markdown("### 📧 Daily Email Digest")
            st.caption("Sends the top matches of the day to your email. (Requires Gmail App Password)")
            digest_en = st.checkbox("Enable Digest", value=bool(settings.get("digest_enabled")))
            digest_hour = st.slider("Send at Hour (24h)", 0, 23, int(settings.get("digest_hour", 9)))
            digest_email = st.text_input("To Email", value=settings.get("digest_email", ""))
            
            with st.expander("SMTP Settings (Gmail)"):
                smtp_user = st.text_input("Gmail Address", value=settings.get("smtp_user", ""))
                smtp_pass = st.text_input("App Password", value=settings.get("smtp_pass", ""), type="password")
                
        if st.form_submit_button("💾 Save Settings", type="primary"):
            save_scheduler_settings({
                "auto_hunt_enabled": 1 if auto_hunt else 0,
                "hunt_hour": hunt_hour,
                "digest_enabled": 1 if digest_en else 0,
                "digest_email": digest_email,
                "digest_hour": digest_hour,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": smtp_user,
                "smtp_pass": smtp_pass
            })
            
            # Update scheduler immediately
            if auto_hunt:
                schedule_daily_hunt(hour=hunt_hour)
            else:
                from agents.scheduler import cancel_job
                cancel_job("daily_hunt")
                
            if digest_en:
                schedule_digest_email(hour=digest_hour, email=digest_email, smtp_settings=get_scheduler_settings())
            else:
                from agents.scheduler import cancel_job
                cancel_job("daily_digest")
                
            st.success("Settings saved and scheduler updated!")
