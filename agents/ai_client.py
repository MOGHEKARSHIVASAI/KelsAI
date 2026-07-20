"""
KelsAI AI Client
Unified interface for Gemini API and OpenRouter.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class GeminiClient:
    """Wrapper around Google Gemini API."""

    def __init__(self, api_key: str = None):
        import google.generativeai as genai
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY not set.")
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def generate_content(self, prompt: str) -> object:
        return self.model.generate_content(prompt)


class OpenRouterClient:
    """Wrapper around OpenRouter API (OpenAI-compatible)."""

    def __init__(self, api_key: str = None, model: str = "google/gemini-2.5-flash"):
        import httpx
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set.")
        self.model = model
        self.http = httpx.Client(timeout=60.0)

    def generate_content(self, prompt: str) -> object:
        resp = self.http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]

        class _Response:
            def __init__(self, t):
                self.text = t
        return _Response(text)


def get_ai_client(provider: str = None, api_key: str = None):
    """
    Factory function to get the appropriate AI client.
    provider: 'gemini' or 'openrouter'
    """
    provider = provider or os.getenv("AI_PROVIDER", "gemini")
    if provider == "openrouter":
        return OpenRouterClient(api_key=api_key)
    return GeminiClient(api_key=api_key)
