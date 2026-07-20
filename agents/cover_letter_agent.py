"""
KelsAI Cover Letter Agent
Generates personalized cover letters and tailored resume summaries using AI.
"""


def generate_cover_letter(profile: dict, job: dict, ai_client) -> str:
    """
    Generate a professional, personalized cover letter for the given job.
    Returns the cover letter as a string.
    """
    try:
        prompt = f"""You are a professional career coach. Write a compelling, personalized cover letter for this candidate.

Candidate Profile:
- Name: {profile.get('name', 'Candidate')}
- Location: {profile.get('location', '')}
- Skills: {profile.get('skills', '')}
- Summary: {profile.get('summary', '')}
- Experience: {str(profile.get('experience', ''))[:600]}

Target Job:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Location: {job.get('location', '')}
- Description: {job.get('description', '')[:1200]}

Instructions:
1. Write exactly 3 paragraphs
2. Paragraph 1: Opening — why the candidate is excited about THIS company and role specifically
3. Paragraph 2: Key skills match — connect 3-4 specific skills/experiences to the job requirements
4. Paragraph 3: Closing — confident call to action
5. Keep it under 300 words total
6. Do NOT use generic phrases like "I am writing to express my interest"
7. Use the candidate's real name and skills
8. Sound confident, professional, and specific

Write only the letter body (no subject line, no "Dear Hiring Manager" header — just the 3 paragraphs).
"""
        response = ai_client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating cover letter: {e}"


def tailor_resume_summary(profile: dict, job: dict, ai_client) -> str:
    """
    Rewrite the candidate's resume summary to better match a specific job.
    Returns the tailored summary as a string.
    """
    try:
        prompt = f"""You are a resume expert. Rewrite this candidate's professional summary to better match the target job.

Current Summary:
{profile.get('summary', 'Experienced software developer.')}

Candidate Skills: {profile.get('skills', '')}

Target Job:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Key requirements from JD: {job.get('description', '')[:800]}

Rules:
1. Keep it to 2-3 sentences max
2. Naturally incorporate 3-4 keywords from the job description
3. Maintain the candidate's actual experience level — do NOT fabricate experience
4. Write in first person, professional tone
5. Return only the summary text, nothing else
"""
        response = ai_client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating tailored summary: {e}"
