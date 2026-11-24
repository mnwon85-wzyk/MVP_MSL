import os
from typing import List

from dotenv import load_dotenv


load_dotenv()


# ============================================================
# PROVIDERS
# ============================================================

def available_providers() -> List[str]:
    providers = []

    if os.getenv("GEMINI_API_KEY"):
        providers.append("Gemini")

    if os.getenv("OPENAI_API_KEY"):
        providers.append("OpenAI")

    return providers


# ============================================================
# MAIN ROUTER
# ============================================================

def ask_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
) -> str:

    provider_normalized = (
        provider or ""
    ).strip().lower()

    if provider_normalized == "gemini":
        return ask_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    if provider_normalized == "openai":
        return ask_openai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    raise ValueError(
        f"Unsupported or unconfigured LLM provider: {provider}"
    )


# ============================================================
# GEMINI
# ============================================================

def ask_gemini(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Gemini server-side call.

    GEMINI_API_KEY is read only from the backend environment.
    """

    try:
        from google import genai

    except ImportError as exc:
        raise RuntimeError(
            "Google GenAI SDK is not installed. "
            "Run: pip install google-genai"
        ) from exc

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or ""
    ).strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    model = (
        os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )
        or "gemini-2.5-flash"
    ).strip()

    client = genai.Client(
        api_key=api_key
    )

    combined_prompt = f"""
SYSTEM INSTRUCTIONS
-------------------
{system_prompt.strip()}

USER REQUEST / SOURCE MATERIAL
------------------------------
{user_prompt.strip()}
""".strip()

    try:
        response = (
            client.models.generate_content(
                model=model,
                contents=combined_prompt,
            )
        )

    except Exception as exc:
        raise RuntimeError(
            "Gemini request failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return str(text).strip()


# ============================================================
# OPENAI
# ============================================================

def ask_openai(
    system_prompt: str,
    user_prompt: str,
) -> str:

    try:
        from openai import OpenAI

    except ImportError as exc:
        raise RuntimeError(
            "OpenAI SDK is not installed. "
            "Run: pip install openai"
        ) from exc

    api_key = (
        os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    client = OpenAI(
        api_key=api_key
    )

    model = (
        os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
        )
        or "gpt-5.6-luna"
    ).strip()

    try:
        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=user_prompt,
        )

    except Exception as exc:
        raise RuntimeError(
            "OpenAI request failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    text = getattr(
        response,
        "output_text",
        None,
    )

    if not text:
        raise RuntimeError(
            "OpenAI returned an empty response."
        )

    return str(text).strip()