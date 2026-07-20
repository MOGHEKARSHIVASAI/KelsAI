"""
KelsAI Matcher Agent v2
- Embedding-first batch scoring pipeline
- Only calls Gemini on jobs above the embedding threshold (>55%)
- Fallback keyword scoring
"""

import json
import numpy as np


def _cosine_similarity(vec_a: list, vec_b: list) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _build_profile_text(profile: dict) -> str:
    parts = []
    if profile.get("summary"):
        parts.append(profile["summary"])
    if profile.get("skills"):
        parts.append(f"Skills: {profile['skills']}")
    if profile.get("experience"):
        try:
            exp = json.loads(profile["experience"]) if isinstance(profile["experience"], str) else profile["experience"]
            for job in exp:
                parts.append(f"{job.get('title', '')} at {job.get('company', '')}. {job.get('description', '')}")
        except Exception:
            parts.append(profile["experience"])
    return " ".join(parts)


def _keyword_match_score(profile: dict, job: dict) -> float:
    skills = [s.strip().lower() for s in profile.get("skills", "").split(",") if s.strip()]
    jd = job.get("description", "").lower()
    if not skills:
        return 0.0
    matched = sum(1 for skill in skills if skill in jd)
    return round((matched / len(skills)) * 100, 1)


def generate_match_summary(profile: dict, job: dict, score: float, ai_client) -> str:
    try:
        prompt = f"""You are a career advisor. Given this candidate's skills and the job description, write a 2-3 sentence summary explaining how well the candidate matches this job.
        
Candidate Skills: {profile.get("skills", "")}
Job Title: {job.get("title", "")}
Job Description (excerpt): {job.get("description", "")[:1000]}
Match Score: {score}%

Write a concise, encouraging summary. Be specific about matching skills. No bullet points, just 2-3 sentences."""
        response = ai_client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Match score: {score}%. Review job description for details. ({e})"


def match_jobs_batch(
    profile: dict,
    jobs: list,
    embedding_model,
    ai_client,
    min_score: float = 60,
    progress_callback=None
) -> list:
    """
    Score all jobs against profile.
    1. Batch encode all texts (fast, CPU only).
    2. Calculate cosine similarities.
    3. ONLY call Gemini for summaries on jobs that score >= min_score.
    """
    if not jobs:
        return []

    profile_text = _build_profile_text(profile)
    job_texts = [f"{j.get('title', '')} {j.get('description', '')}" for j in jobs]
    all_texts = [profile_text] + job_texts

    try:
        # Batch encode is significantly faster than one-by-one
        if progress_callback:
            progress_callback(0.1, "Generating semantic embeddings for all jobs...")
        
        embeddings = embedding_model.encode(all_texts)
        profile_emb = embeddings[0]
        job_embs = embeddings[1:]
        
        scores = []
        for j_emb in job_embs:
            sim = _cosine_similarity(profile_emb, j_emb)
            scores.append(round(sim * 100, 1))
            
    except Exception as e:
        print(f"[Matcher] Batch embedding failed, falling back to keyword match: {e}")
        scores = [_keyword_match_score(profile, j) for j in jobs]

    # Assign scores and generate summaries only for those above threshold
    scored_jobs = []
    total = len(jobs)
    
    for i, (job, score) in enumerate(zip(jobs, scores)):
        if progress_callback:
            progress_callback(0.1 + (0.9 * (i / total)), f"Scoring: {job.get('title', '')}")
            
        summary = ""
        # ⚡ Smart AI Scoring: Only hit the Gemini API if the embedding score passes the threshold
        if score >= min_score:
            summary = generate_match_summary(profile, job, score, ai_client)
            
        job["match_score"] = score
        job["match_summary"] = summary
        scored_jobs.append(job)

    if progress_callback:
        progress_callback(1.0, "Scoring complete!")

    return sorted(scored_jobs, key=lambda x: x["match_score"], reverse=True)
