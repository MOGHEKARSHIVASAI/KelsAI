"""
KelsAI Profile Agent
Parses a user's PDF resume and extracts structured information using AI.
"""

import json
import os
import re
import fitz  # PyMuPDF
from datetime import datetime


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}")
    return text.strip()


def parse_resume_with_ai(text: str, ai_client) -> dict:
    """
    Use the AI client to extract structured data from resume text.
    Returns a dictionary with profile fields.
    """
    prompt = f"""
You are a resume parser. Extract the following information from the resume text below and return ONLY a valid JSON object with these exact keys:
- name (string)
- email (string)
- phone (string)
- location (string)
- linkedin (string, URL or empty)
- github (string, URL or empty)
- summary (string, professional summary or objective)
- skills (string, comma-separated list of all technical and soft skills)
- experience (string, JSON array of jobs with keys: title, company, duration, description)
- education (string, JSON array with keys: degree, institution, year)
- projects (string, JSON array with keys: name, description, tech_stack)
- certifications (string, comma-separated list of certifications)

Return ONLY the JSON object with no markdown fences, no explanation.

RESUME TEXT:
{text}
"""
    try:
        response = ai_client.generate_content(prompt)
        raw = response.text.strip()
        # Remove markdown fences if present
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
        return json.loads(raw.strip())
    except Exception as e:
        # Fallback: return basic extraction
        return _basic_extraction(text)


def _basic_extraction(text: str) -> dict:
    """Fallback basic regex-based extraction if AI fails."""
    email = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phone = re.findall(r"[\+]?[\d\s\-\(\)]{10,15}", text)
    linkedin = re.findall(r"linkedin\.com/in/[\w\-]+", text)
    github = re.findall(r"github\.com/[\w\-]+", text)

    return {
        "name": "",
        "email": email[0] if email else "",
        "phone": phone[0].strip() if phone else "",
        "location": "",
        "linkedin": f"https://{linkedin[0]}" if linkedin else "",
        "github": f"https://{github[0]}" if github else "",
        "summary": "",
        "skills": "",
        "experience": "[]",
        "education": "[]",
        "projects": "[]",
        "certifications": "",
    }


def process_resume(pdf_path: str, ai_client) -> dict:
    """Full pipeline: extract text → parse with AI → return profile dict."""
    text = extract_text_from_pdf(pdf_path)
    profile = parse_resume_with_ai(text, ai_client)
    profile["resume_path"] = pdf_path

    # Ensure experience/education/projects are stored as JSON strings
    for key in ["experience", "education", "projects"]:
        if isinstance(profile.get(key), (list, dict)):
            profile[key] = json.dumps(profile[key])
        elif not profile.get(key):
            profile[key] = "[]"

    return profile
