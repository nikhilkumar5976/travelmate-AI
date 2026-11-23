import logging
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Fallback models in the Gemini family if primary is rate-limited or unavailable
FALLBACK_MODELS = [
    'gemini-3.5-flash-lite',
    'gemini-3.5-flash',
    'gemini-3.1-flash-lite',
    'gemini-3.7-flash',
    'gemini-3.6-flash',
]


def call_llm(prompt, json_output=False):
    api_key = (
        getattr(settings, 'LLM_API_KEY', '')
        or getattr(settings, 'GEMINI_API_KEY', '')
        or getattr(settings, 'GOOGLE_API_KEY', '')
    )
    if not api_key:
        raise ValueError("No Gemini API key configured. Please set LLM_API_KEY or GEMINI_API_KEY in environment variables.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=15.0,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    config = types.GenerateContentConfig(
        response_mime_type='application/json' if json_output else None,
    )

    primary_model = getattr(settings, 'LLM_MODEL', 'gemini-3.8-flash') or 'gemini-3.8-flash'
    models_to_try = [primary_model]
    for model_name in FALLBACK_MODELS:
        if model_name not in models_to_try:
            models_to_try.append(model_name)

    last_error = None
    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text
        except Exception as error:
            logger.warning(
                "Model %s failed (%s). Attempting next available model...",
                model,
                error,
            )
            last_error = error
            continue

    if last_error:
        raise last_error
