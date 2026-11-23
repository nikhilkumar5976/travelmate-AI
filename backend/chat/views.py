import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from trips.models import Trip
from .forms import ChatForm
from .models import ChatMessage

logger = logging.getLogger(__name__)


def is_ajax_request(request):
    """
    Check if the request is an AJAX or API call expecting JSON.
    """
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '').lower()
        or request.GET.get('format') == 'json'
    )


def get_user_photo_url(user):
    """
    Safely retrieve user photo URL without throwing on missing storage paths.
    """
    try:
        profile = getattr(user, 'profile', None)
        if profile and profile.photo:
            return profile.photo.url
    except Exception:
        pass
    return ''


@login_required
def trip_chat(request, trip_id):
    is_ajax = is_ajax_request(request)
    trip = Trip.objects.filter(
        Q(owner=request.user) | Q(members__user=request.user)
    ).distinct().filter(id=trip_id).first()

    if not trip:
        existing = Trip.objects.filter(id=trip_id).first()
        if is_ajax:
            if existing:
                return JsonResponse({'error': 'You must be a member of this trip to access group chat.'}, status=403)
            return JsonResponse({'error': 'This trip was not found or has expired on the server.'}, status=404)

        if existing:
            messages.error(request, 'You must be a member of this trip to access the group chat.')
        else:
            messages.error(request, 'This trip was not found or has expired on the server.')
        return redirect('my_trips')

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['text'].strip()
            message = ChatMessage.objects.create(
                trip=trip, sender=request.user, text=text
            )
            if is_ajax:
                return JsonResponse({
                    'id': message.id,
                    'sender_id': request.user.id,
                    'sender': request.user.username,
                    'photo': get_user_photo_url(request.user),
                    'text': message.text,
                    'time': timezone.localtime(message.created_at).strftime('%d %b, %H:%M'),
                })
            return redirect('trip_chat', trip_id=trip.id)

        if is_ajax:
            return JsonResponse({'error': 'Please enter a valid message.'}, status=400)
    else:
        form = ChatForm()

    latest = (
        ChatMessage.objects.filter(trip=trip)
        .select_related('sender', 'sender__profile')
        .order_by('-created_at')[:100]
    )
    chat_messages = list(latest)[::-1]

    return render(request, 'chat/trip_chat.html', {
        'trip': trip,
        'chat_messages': chat_messages,
        'form': form,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def chat_messages_api(request, trip_id):
    """
    Dedicated JSON API for fetching and posting chat messages.
    Handles GET for incremental polling and POST for async message delivery.
    """
    trip = Trip.objects.filter(
        Q(owner=request.user) | Q(members__user=request.user)
    ).distinct().filter(id=trip_id).first()

    if not trip:
        existing = Trip.objects.filter(id=trip_id).first()
        if existing:
            return JsonResponse({'error': 'You must be a member of this trip.', 'messages': []}, status=403)
        return JsonResponse({'error': 'Trip not found or access denied.', 'messages': []}, status=404)

    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if not text:
            # Also check JSON body if posted as application/json
            try:
                import json
                body = json.loads(request.body.decode('utf-8'))
                text = (body.get('text') or '').strip()
            except Exception:
                pass

        if not text:
            return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

        message = ChatMessage.objects.create(
            trip=trip, sender=request.user, text=text
        )
        return JsonResponse({
            'id': message.id,
            'sender_id': request.user.id,
            'sender': request.user.username,
            'photo': get_user_photo_url(request.user),
            'text': message.text,
            'time': timezone.localtime(message.created_at).strftime('%d %b, %H:%M'),
        })

    # GET request: incremental polling
    after_id = request.GET.get('after')
    query = ChatMessage.objects.filter(trip=trip).select_related('sender', 'sender__profile')

    if after_id and str(after_id).isdigit() and int(after_id) > 0:
        messages_iter = query.filter(id__gt=int(after_id)).order_by('id')[:50]
    else:
        query = query.order_by('-id')[:50]
        messages_iter = list(query)[::-1]

    messages_list = []
    for msg in messages_iter:
        messages_list.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender': msg.sender.username,
            'photo': get_user_photo_url(msg.sender),
            'text': msg.text,
            'time': timezone.localtime(msg.created_at).strftime('%d %b, %H:%M'),
        })

    return JsonResponse({'messages': messages_list})
