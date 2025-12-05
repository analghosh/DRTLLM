# app/core/llm_factory.py
import os
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import httpx

def create_llm() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
        return ChatOllama(model=model,temperature=0.2,)

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        return ChatGoogleGenerativeAI(model=model,api_key=api_key,)

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        insecure_client = httpx.Client(verify=False, timeout=30.0)
        return ChatGroq(model=model,api_key=api_key,http_client=insecure_client,)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
