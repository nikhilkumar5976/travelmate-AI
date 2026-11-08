from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from trips.models import Trip
from .forms import ChatForm
from .models import ChatMessage


@login_required
def trip_chat(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user)).distinct(),
        id=trip_id
    )

    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            message = ChatMessage.objects.create(
                trip=trip, sender=request.user, text=form.cleaned_data['text']
            )
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json'
            if is_ajax:
                profile = getattr(request.user, 'profile', None)
                photo = profile.photo.url if profile and profile.photo else ''
                return JsonResponse({
                    'id': message.id,
                    'sender_id': request.user.id,
                    'sender': request.user.username,
                    'photo': photo,
                    'text': message.text,
                    'time': timezone.localtime(message.created_at).strftime('%d %b, %H:%M'),
                })
            return redirect('trip_chat', trip_id=trip.id)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'error': 'Invalid message content.'}, status=400)
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
def chat_messages_api(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user)).distinct(),
        id=trip_id
    )
    after_id = request.GET.get('after')
    query = ChatMessage.objects.filter(trip=trip).select_related('sender', 'sender__profile')
    if after_id and str(after_id).isdigit():
        query = query.filter(id__gt=int(after_id)).order_by('created_at')[:50]
        messages_iter = query
    else:
        query = query.order_by('-created_at')[:50]
        messages_iter = list(query)[::-1]

    messages_list = []
    for msg in messages_iter:
        profile = getattr(msg.sender, 'profile', None)
        photo = profile.photo.url if profile and profile.photo else ''
        messages_list.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender': msg.sender.username,
            'photo': photo,
            'text': msg.text,
            'time': timezone.localtime(msg.created_at).strftime('%d %b, %H:%M'),
        })
    return JsonResponse({'messages': messages_list})
