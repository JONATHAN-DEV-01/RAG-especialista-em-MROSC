"""
src/llm_provider.py
===================
Fábrica de LLM (get_llm) — suporta Ollama, Groq e Gemini.

Padrão: Ollama local (nenhuma chave necessária).
Alternativas gratuitas via API: Groq, Google Gemini.

Uso:
  from src.llm_provider import get_llm

  llm = get_llm()                    # usa LLM_PROVIDER do .env (padrão: ollama)
  llm = get_llm(provider="groq")     # força Groq
  llm = get_llm(provider="gemini")   # força Gemini
"""

import os
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()

# Tipo dos provedores suportados
Provider = Literal["ollama", "groq", "gemini"]


def get_llm(provider: Optional[Provider] = None):
    """
    Fábrica de LLM. Retorna uma instância configurada do provedor solicitado.

    Args:
        provider: "ollama" | "groq" | "gemini"
                  Se None, lê LLM_PROVIDER do .env (padrão: "ollama").

    Returns:
        Instância de LLM compatível com LangChain (Runnable).

    Raises:
        ValueError: Se o provedor for desconhecido ou a chave de API não estiver configurada.
        ImportError: Se o pacote do provedor não estiver instalado.
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        return _get_ollama()
    elif provider == "groq":
        return _get_groq()
    elif provider == "gemini":
        return _get_gemini()
    else:
        raise ValueError(
            f"Provedor desconhecido: '{provider}'. "
            f"Opções válidas: 'ollama', 'groq', 'gemini'."
        )


# ---------------------------------------------------------------------------
# Provedores individuais
# ---------------------------------------------------------------------------

def _get_ollama():
    """
    Retorna LLM Ollama local.
    Requisitos:
      - Ollama instalado: https://ollama.com
      - Serviço rodando:  ollama serve
      - Modelo baixado:   ollama pull <modelo>
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError(
            "Pacote langchain-ollama não instalado. "
            "Execute: pip install langchain-ollama"
        )

    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    print(f"   🦙 LLM: Ollama local | modelo: {model} | URL: {base_url}")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0.1,       # baixa temperatura para respostas jurídicas precisas
        num_predict=2048,      # máximo de tokens na resposta
    )


def _get_groq():
    """
    Retorna LLM Groq (free tier).
    Requisito: GROQ_API_KEY configurada no .env
    """
    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError(
            "Pacote langchain-groq não instalado. "
            "Execute: pip install langchain-groq"
        )

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key.startswith("SUBSTITUA"):
        raise ValueError(
            "GROQ_API_KEY não configurada. "
            "Defina-a no arquivo .env ou use o provedor 'ollama' (padrão)."
        )

    model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    print(f"   ⚡ LLM: Groq | modelo: {model}")

    return ChatGroq(
        groq_api_key=api_key,
        model_name=model,
        temperature=0.1,
        max_tokens=2048,
    )


def _get_gemini():
    """
    Retorna LLM Google Gemini (free tier via Google AI Studio).
    Requisito: GOOGLE_API_KEY configurada no .env
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "Pacote langchain-google-genai não instalado. "
            "Execute: pip install langchain-google-genai"
        )

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key.startswith("SUBSTITUA"):
        raise ValueError(
            "GOOGLE_API_KEY não configurada. "
            "Defina-a no arquivo .env ou use o provedor 'ollama' (padrão)."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    print(f"   ✨ LLM: Google Gemini | modelo: {model}")

    return ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model=model,
        temperature=0.1,
        max_output_tokens=2048,
    )
