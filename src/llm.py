"""Shared Gemini chat model setup."""

from config import GEMINI_API_KEY, GEMINI_MODEL

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def gemini_openai_client():
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to enable Google AI Studio")
    from openai import OpenAI
    return OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)


def gemini_chat_model(temperature: float = 0, model: str | None = None):
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to enable Gemini")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model or GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        temperature=temperature,
        max_retries=2,
    )
