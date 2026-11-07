from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

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
            ChatMessage.objects.create(
                trip=trip, sender=request.user, text=form.cleaned_data['text']
            )
            return redirect('trip_chat', trip_id=trip.id)
    else:
        form = ChatForm()

    latest = (
        ChatMessage.objects.filter(trip=trip)
        .select_related('sender__profile')
        .order_by('-created_at')[:100]
    )
    chat_messages = list(latest)[::-1]

    return render(request, 'chat/trip_chat.html', {
        'trip': trip,
        'chat_messages': chat_messages,
        'form': form,
    })