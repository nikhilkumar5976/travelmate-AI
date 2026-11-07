import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.models import Profile
from ai.services import generate_itinerary, ItineraryError
from itinerary.models import Stop
from .forms import TripForm
from .models import Trip, TripMember

logger = logging.getLogger(__name__)


@login_required
def create_trip(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_complete():
        messages.error(request, 'Complete your profile before creating a trip.')
        return redirect('edit_profile')

    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.owner = request.user
            trip.save()
            TripMember.objects.create(trip=trip, user=request.user, role='owner')
            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = TripForm()
    return render(request, 'trips/create_trip.html', {'form': form})


@login_required
def trip_list(request):
    trips = Trip.objects.filter(
        Q(owner=request.user) | Q(members__user=request.user)
    ).distinct().order_by('-created_at')
    return render(request, 'trips/trip_list.html', {'trips': trips})


@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user)).distinct(),
        id=trip_id
    )
    members = trip.members.select_related('user')
    member_count = members.count()
    days = trip.days.prefetch_related('stops')

    cost_per_person = Stop.objects.filter(day__trip=trip).aggregate(
        total=Sum('estimated_cost_per_person')
    )['total'] or 0

    return render(request, 'trips/trip_detail.html', {
        'trip': trip,
        'members': members,
        'days': days,
        'budget_per_person': trip.budget / member_count if member_count > 0 else trip.budget,
        'cost_per_person': cost_per_person,
        'group_cost': cost_per_person * member_count,
        'is_owner': trip.owner == request.user,
    })


@login_required
@require_POST
def generate_itinerary_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, owner=request.user)
    try:
        generate_itinerary(trip)
        messages.success(request, 'Your itinerary is ready.')
    except ItineraryError as error:
        logger.warning('Unusable AI reply: %s', error)
        messages.error(request, 'The AI gave an unusable answer. Please try again.')
    except Exception:
        logger.exception('Itinerary generation failed')
        messages.error(request, 'Could not reach the AI service. Please try again.')
    return redirect('trip_detail', trip_id=trip.id)
