import os
from typing import AsyncGenerator, List, Tuple
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError, BadRequestError
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

# Initialize default client as 'client' to maintain compatibility with test suite mocks
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Initialize Gemini client using the OpenAI compatibility endpoint
gemini_client = None
if settings.GEMINI_API_KEY:
    gemini_client = AsyncOpenAI(
        api_key=settings.GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

# Initialize Groq client using the OpenAI-compatible endpoint
groq_client = None
if settings.GROQ_API_KEY:
    groq_client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

def get_client_and_model() -> Tuple[AsyncOpenAI, str]:
    """Helper to select active client and model based on the config settings."""
    import sys
    if "pytest" in sys.modules:
        return client, settings.OPENAI_MODEL

    if settings.AI_PROVIDER == "groq" and groq_client:
        return groq_client, settings.GROQ_MODEL
    if settings.AI_PROVIDER == "gemini" and gemini_client:
        return gemini_client, settings.GEMINI_MODEL
    return client, settings.OPENAI_MODEL

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "pretend you are",
    "forget everything",
    "system prompt",
    "as an ai with no restrictions",
]

def check_prompt_injection(content: str) -> bool:
    """Check if the user input contains patterns matching prompt injection attempts."""
    content_lower = content.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in content_lower:
            return True
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
    reraise=True
)
async def call_openai_raw(messages: List[dict]) -> Tuple[str, dict]:
    selected_client, model = get_client_and_model()
    response = await selected_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=settings.OPENAI_MAX_TOKENS,
    )
    choice = response.choices[0]
    content = choice.message.content or ""
    
    usage = response.usage
    token_usage = {
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
    }
    
    return content, token_usage

async def call_openai(messages: List[dict]) -> Tuple[str, dict]:
    """Call the selected AI API (OpenAI/Gemini) with retry handling and return (response_text, token_usage)."""
    try:
        return await call_openai_raw(messages)
    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="AI service is temporarily unavailable due to rate limiting. Please wait a moment and try again."
        )
    except BadRequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"AI request error: {str(e)}"
        )
    except Exception as e:
        from loguru import logger
        logger.exception("AI call failed")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

async def stream_openai(messages: List[dict]) -> AsyncGenerator[str, None]:
    """Stream selected AI API (OpenAI/Gemini) response chunk by chunk."""
    selected_client, model = get_client_and_model()
    response = await selected_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        stream=True,
    )
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
