"""NeMo auto-loads this module from the rails config directory.

NeMo 0.10 only routes `engine: openai` to ChatOpenAI when the model name contains
"gpt-3.5"/"gpt-4"; other names fall back to the legacy /completions client, which
Google AI Studio's OpenAI-compatible endpoint does not serve (HTTP 404).
Registering a chat provider keeps calls on /chat/completions for Gemini.
"""
from langchain_openai.chat_models import ChatOpenAI
from nemoguardrails.llm.providers import register_llm_provider

register_llm_provider("openai_chat", ChatOpenAI)
