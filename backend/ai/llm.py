from django.conf import settings
from google import genai
from google.genai import types


def call_llm(prompt, json_output=False):
    client = genai.Client(api_key=settings.LLM_API_KEY)
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level='low'),
        response_mime_type='application/json' if json_output else None,
    )
    response = client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
        config=config,
    )
    return response.text
