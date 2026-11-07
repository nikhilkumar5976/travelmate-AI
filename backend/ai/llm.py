from django.conf import settings
from google import genai


def call_llm(prompt):
    client = genai.Client(api_key=settings.LLM_API_KEY)
    response = client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
    )
    return response.text