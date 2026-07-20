"""
KelsAI Skill Gap Analyzer
Identifies missing skills between a candidate's profile and a job description,
and suggests free learning resources for each gap.
"""

RESOURCE_MAP = {
    # Languages
    "python":      ("https://docs.python.org/3/tutorial/", "https://www.youtube.com/watch?v=_uQrJ0TkZlc"),
    "java":        ("https://dev.java/learn/", "https://www.youtube.com/watch?v=eIrMbAQSU34"),
    "javascript":  ("https://javascript.info/", "https://www.youtube.com/watch?v=PkZNo7MFNFg"),
    "typescript":  ("https://www.typescriptlang.org/docs/", "https://www.youtube.com/watch?v=30LWjhZzg50"),
    "go":          ("https://go.dev/learn/", "https://www.youtube.com/watch?v=yyUHQIec83I"),
    "rust":        ("https://doc.rust-lang.org/book/", "https://www.youtube.com/watch?v=T_KrYLW4jw8"),
    "c++":         ("https://cppreference.com/", "https://www.youtube.com/watch?v=vLnPwxZdW4Y"),
    "kotlin":      ("https://kotlinlang.org/docs/", "https://www.youtube.com/watch?v=F9UC9DY-vIU"),
    # Frameworks
    "react":       ("https://react.dev/learn", "https://www.youtube.com/watch?v=SqcY0GlETPk"),
    "angular":     ("https://angular.io/tutorial", "https://www.youtube.com/watch?v=3dHNOWTI7H8"),
    "vue":         ("https://vuejs.org/guide/", "https://www.youtube.com/watch?v=VeNfHj6MhgA"),
    "django":      ("https://docs.djangoproject.com/en/stable/intro/tutorial01/", "https://www.youtube.com/watch?v=PtQiiknWUcI"),
    "flask":       ("https://flask.palletsprojects.com/tutorial/", "https://www.youtube.com/watch?v=Z1RJmh_OqeA"),
    "fastapi":     ("https://fastapi.tiangolo.com/tutorial/", "https://www.youtube.com/watch?v=0sOvCWFmrtA"),
    "spring":      ("https://spring.io/guides", "https://www.youtube.com/watch?v=vtPkZShrvXQ"),
    "node":        ("https://nodejs.org/en/learn/", "https://www.youtube.com/watch?v=32M1al-Y6Ag"),
    # Cloud & DevOps
    "aws":         ("https://aws.amazon.com/training/", "https://www.youtube.com/watch?v=ulprqHHWlng"),
    "gcp":         ("https://cloud.google.com/learn/training", "https://www.youtube.com/watch?v=IeMYQ-qJeK4"),
    "azure":       ("https://learn.microsoft.com/azure/", "https://www.youtube.com/watch?v=NKEFWyqJ5XA"),
    "docker":      ("https://docs.docker.com/get-started/", "https://www.youtube.com/watch?v=3c-iBn73dDE"),
    "kubernetes":  ("https://kubernetes.io/docs/tutorials/", "https://www.youtube.com/watch?v=X48VuDVv0do"),
    "terraform":   ("https://developer.hashicorp.com/terraform/tutorials", "https://www.youtube.com/watch?v=SLB_c_ayRMo"),
    "ci/cd":       ("https://docs.github.com/actions", "https://www.youtube.com/watch?v=mFFXuXjVgkU"),
    # Data & ML
    "machine learning": ("https://www.coursera.org/learn/machine-learning", "https://www.youtube.com/watch?v=NWONeJKn6kc"),
    "deep learning":    ("https://www.deeplearning.ai/", "https://www.youtube.com/watch?v=aircAruvnKk"),
    "tensorflow":  ("https://www.tensorflow.org/tutorials", "https://www.youtube.com/watch?v=tPYj3fFJGjk"),
    "pytorch":     ("https://pytorch.org/tutorials/", "https://www.youtube.com/watch?v=IC0_FRiX-sw"),
    "sql":         ("https://www.sqlitetutorial.net/", "https://www.youtube.com/watch?v=HXV3zeQKqGY"),
    "postgresql":  ("https://www.postgresql.org/docs/current/tutorial.html", "https://www.youtube.com/watch?v=qw--VYLpxG4"),
    "mongodb":     ("https://learn.mongodb.com/", "https://www.youtube.com/watch?v=Www6cTUymCY"),
    "redis":       ("https://redis.io/docs/", "https://www.youtube.com/watch?v=jgpVdJB2sKQ"),
    # System Design
    "microservices": ("https://microservices.io/patterns/", "https://www.youtube.com/watch?v=rv4LlmLmVWk"),
    "system design": ("https://github.com/donnemartin/system-design-primer", "https://www.youtube.com/watch?v=FSR1s2b-l_I"),
    "kafka":         ("https://kafka.apache.org/documentation/", "https://www.youtube.com/watch?v=Ch5VhJzaoaI"),
    "graphql":       ("https://graphql.org/learn/", "https://www.youtube.com/watch?v=ed8SzALpx1Q"),
    "rest api":      ("https://restfulapi.net/", "https://www.youtube.com/watch?v=SLwpqD8n3d0"),
}


def analyze_skill_gap(profile: dict, job: dict, ai_client) -> dict:
    """
    Analyze the skill gap between candidate profile and job description.
    Returns: { missing_skills, matching_skills, suggestions, overall_readiness }
    """
    try:
        candidate_skills = profile.get("skills", "")
        job_title = job.get("title", "")
        job_desc = job.get("description", "")[:1500]

        prompt = f"""You are a technical recruiter analyzing a skill gap.

Candidate's Skills: {candidate_skills}
Candidate's Experience: {str(profile.get('experience', ''))[:500]}

Job Title: {job_title}
Job Description: {job_desc}

Analyze the gap and respond with ONLY a valid JSON object in this exact format:
{{
  "matching_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "nice_to_have": ["skill5"],
  "overall_readiness": 75,
  "summary": "Brief 2-sentence assessment"
}}

Rules:
- matching_skills: skills the candidate HAS that the job needs
- missing_skills: skills the job REQUIRES that the candidate is MISSING
- nice_to_have: mentioned in JD but not required
- overall_readiness: percentage (0-100) of how ready the candidate is
- Return ONLY the JSON, no markdown, no explanation
"""
        response = ai_client.generate_content(prompt)
        text = response.text.strip()
        # Clean markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        import json
        data = json.loads(text)

        # Attach learning resources for missing skills
        resources = {}
        for skill in data.get("missing_skills", []):
            skill_lower = skill.lower()
            for key, (docs, video) in RESOURCE_MAP.items():
                if key in skill_lower or skill_lower in key:
                    resources[skill] = {"docs": docs, "video": video}
                    break

        data["resources"] = resources
        return data

    except Exception as e:
        return {
            "matching_skills": [],
            "missing_skills": [],
            "nice_to_have": [],
            "overall_readiness": 0,
            "summary": f"Analysis failed: {e}",
            "resources": {}
        }
