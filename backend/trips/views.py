import logging
from django.db import transaction

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from accounts.models import Profile
from ai.services import generate_itinerary, ItineraryError
from itinerary.models import Stop
from .forms import TripForm, InviteForm
from .models import Trip, TripMember, Invitation

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
def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user)).select_related('owner').distinct(),
        id=trip_id
    )
    members = list(trip.members.select_related('user'))
    member_count = len(members)
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
        'is_owner': trip.owner_id == request.user.id,
        'invite_form': InviteForm(trip=trip),
        'pending_invites': trip.invitations.filter(status='pending').select_related('invited_by'),
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


@login_required
@require_POST
def invite_member(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, members__user=request.user)
    form = InviteForm(request.POST, trip=trip)
    if not form.is_valid():
        for error in form.errors.get('email', []):
            messages.error(request, error)
        return redirect('trip_detail', trip_id=trip.id)

    invitation = Invitation.objects.create(
        trip=trip,
        email=form.cleaned_data['email'],
        invited_by=request.user,
    )
    link = request.build_absolute_uri(reverse('invitation', args=[invitation.token]))
    try:
        send_mail(
            subject=f'{request.user.username} invited you to a trip on TravelMate AI',
            message=(
                f'Hi!\n\n'
                f'{request.user.username} invited you to join a trip to {trip.destination} '
                f'on TravelMate AI.\n\n'
                f'Open this link to accept or reject the invitation:\n{link}\n\n'
                f"If you didn't expect this, you can ignore this email.\n"
            ),
            from_email=None,
            recipient_list=[invitation.email],
        )
    except Exception:
        logger.exception('Could not send invitation email')
        invitation.delete()
        messages.error(request, 'Could not send the invitation email. Please try again.')
        return redirect('trip_detail', trip_id=trip.id)

    messages.success(request, f'Invitation sent to {invitation.email}.')
    return redirect('trip_detail', trip_id=trip.id)

def invitation_detail(request, token):
    invitation = get_object_or_404(
        Invitation.objects.select_related('trip', 'invited_by'),
        token=token,
    )
    context = {'invitation': invitation, 'trip': invitation.trip}

    if invitation.status != 'pending':
        context['state'] = 'closed'
    elif not request.user.is_authenticated:
        context['state'] = 'anonymous'
    elif (request.user.email or '').strip().lower() != (invitation.email or '').strip().lower():
        context['state'] = 'wrong_account'
    else:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not profile.is_complete():
            messages.error(request, 'Complete your profile to join this trip.')
            return redirect(f"{reverse('edit_profile')}?{urlencode({'next': request.path})}")
        context['state'] = 'ready'
    return render(request, 'trips/invitation.html', context)


@login_required
@require_POST
def respond_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token, status='pending')

    if (request.user.email or '').strip().lower() != (invitation.email or '').strip().lower():
        messages.error(request, 'This invitation was sent to a different email address.')
        return redirect('invitation', token=token)

    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_complete():
        return redirect('invitation', token=token)

    action = request.POST.get('action')
    if action == 'accept':
        TripMember.objects.get_or_create(
            trip=invitation.trip, user=request.user, defaults={'role': 'member'}
        )
        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save()
        messages.success(request, f'You joined the trip to {invitation.trip.destination}.')
        return redirect('trip_detail', trip_id=invitation.trip.id)

    if action == 'reject':
        invitation.status = 'rejected'
        invitation.responded_at = timezone.now()
        invitation.save()
        messages.info(request, 'You rejected the invitation.')
        return redirect('home')

    return redirect('invitation', token=token)

@login_required
def my_trips(request):
    memberships = (
        TripMember.objects.filter(user=request.user)
        .select_related('trip', 'trip__owner')
        .order_by('-trip__created_at')
    )
    return render(request, 'trips/my_trips.html', {'memberships': memberships})


trip_list = my_trips


@login_required
@require_POST
def leave_trip(request, trip_id):
    membership = get_object_or_404(TripMember, trip_id=trip_id, user=request.user)
    trip = membership.trip
    destination = trip.destination
    message = f'You left the trip to {destination}.'

    with transaction.atomic():
        if membership.role == 'owner':
            successor = trip.members.exclude(user=request.user).order_by('joined_at').first()
            if successor is None:
                trip.delete()
                messages.info(
                    request,
                    f'You left, and the trip to {destination} was deleted because nobody else was in it.',
                )
                return redirect('my_trips')
            successor.role = 'owner'
            successor.save()
            trip.owner = successor.user
            trip.save()
            message = f'You left the trip to {destination}. {successor.user.username} is now the owner.'
        membership.delete()

    messages.info(request, message)
    return redirect('my_trips')


@login_required
@require_POST
def remove_member(request, trip_id, user_id):
    trip = get_object_or_404(Trip, id=trip_id, owner=request.user)
    membership = get_object_or_404(TripMember, trip=trip, user_id=user_id)
    if membership.user_id == request.user.id:
        messages.error(request, 'Use "Leave trip" to leave your own trip.')
    else:
        username = membership.user.username
        membership.delete()
        messages.success(request, f'{username} was removed from the trip.')
    return redirect('trip_detail', trip_id=trip.id)