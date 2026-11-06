from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import Profile
from .forms import TripForm
from .models import Trip, TripMember


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
    count = members.count()
    per_person = trip.budget / count if count > 0 else trip.budget
    return render(request, 'trips/trip_detail.html', {
        'trip': trip,
        'members': members,
        'per_person': per_person,
    })
