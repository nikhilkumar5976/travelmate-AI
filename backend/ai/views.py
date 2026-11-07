import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .llm import call_llm
from .prompts import build_chatbot_prompt

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY = 10
HOURLY_LIMIT = 20


@require_POST
def chatbot_reply(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please log in to use the assistant.'}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    message = str(payload.get('message', '')).strip()
    if not message:
        return JsonResponse({'error': 'Please type a question.'}, status=400)
    if len(message) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {'error': f'Please keep your question under {MAX_MESSAGE_LENGTH} characters.'},
            status=400,
        )

    history = []
    raw_history = payload.get('history', [])
    if isinstance(raw_history, list):
        for item in raw_history[-MAX_HISTORY:]:
            if isinstance(item, dict) and item.get('role') in ('user', 'assistant'):
                history.append({'role': item['role'], 'text': str(item.get('text', ''))[:1000]})

    key = f'chatbot-count:{request.user.id}'
    cache.add(key, 0, timeout=3600)
    if cache.incr(key) > HOURLY_LIMIT:
        return JsonResponse(
            {'error': 'You have reached the hourly limit. Please try again later.'},
            status=429,
        )

    try:
        reply = call_llm(build_chatbot_prompt(history, message))
    except Exception:
        logger.exception('Chatbot call failed')
        return JsonResponse(
            {'error': 'The assistant is unavailable right now. Please try again.'},
            status=502,
        )

    return JsonResponse({'reply': reply.strip()})
