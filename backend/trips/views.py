import logging
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from accounts.models import Profile
from ai.services import generate_itinerary, ItineraryError
from itinerary.models import Stop
from .emails import send_invitation_email
from .forms import TripForm, InviteForm
from .models import Trip, TripMember, Invitation

logger = logging.getLogger(__name__)


@login_required
def create_trip(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_complete():
        messages.error(request, 'Complete your profile before creating a trip.')
        return redirect('edit_profile')

    if not profile.email_verified:
        messages.error(
            request,
            'Verify your email first. Check your inbox or use the Resend button on your home page.'
        )
        return redirect('home')

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
def edit_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, owner=request.user)

    if request.method == 'POST':
        old_destination = trip.destination
        old_num_days = trip.num_days
        old_interests = set(trip.interests or [])

        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            trip = form.save()
            messages.success(request, 'Trip updated.')

            if trip.days.exists():
                new_interests = set(trip.interests or [])
                if (
                    old_destination != trip.destination
                    or old_num_days != trip.num_days
                    or old_interests != new_interests
                ):
                    messages.info(request, 'Your trip details changed. Regenerate the itinerary to match.')

            return redirect('trip_detail', trip_id=trip.id)
    else:
        form = TripForm(instance=trip)

    return render(request, 'trips/edit_trip.html', {'trip': trip, 'form': form})


@login_required
def delete_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, owner=request.user)

    if request.method == 'POST':
        destination = trip.destination
        trip.delete()
        messages.success(request, f'The trip to {destination} was deleted.')
        return redirect('my_trips')

    return render(request, 'trips/delete_trip.html', {'trip': trip})


@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user)).select_related('owner').distinct(),
        id=trip_id
    )
    members = list(trip.members.select_related('user', 'user__profile'))
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


GENERATIONS_PER_HOUR = 5


@login_required
@require_POST
def generate_itinerary_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, owner=request.user)

    key = f'itinerary-count:{request.user.id}'
    cache.add(key, 0, timeout=3600)
    if cache.incr(key) > GENERATIONS_PER_HOUR:
        messages.error(
            request,
            'You have generated several itineraries recently. Please try again in a while.',
        )
        return redirect('trip_detail', trip_id=trip.id)

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


INVITES_PER_HOUR = 20


@login_required
@require_POST
def invite_member(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, members__user=request.user)
    form = InviteForm(request.POST, trip=trip)
    if not form.is_valid():
        for error in form.errors.get('email', []):
            messages.error(request, error)
        return redirect('trip_detail', trip_id=trip.id)

    key = f'invite-count:{request.user.id}'
    cache.add(key, 0, timeout=3600)
    if cache.incr(key) > INVITES_PER_HOUR:
        messages.error(request, 'You have sent too many invitations. Please try again later.')
        return redirect('trip_detail', trip_id=trip.id)

    invitation = Invitation.objects.create(
        trip=trip,
        email=form.cleaned_data['email'],
        invited_by=request.user,
    )

    try:
        send_invitation_email(invitation, request=request)
    except Exception:
        logger.exception('Could not send invitation email')
        invitation.delete()
        messages.error(request, 'Could not send the invitation email. Please try again.')
        return redirect('trip_detail', trip_id=trip.id)

    messages.success(request, f'Invitation sent to {invitation.email}.')
    return redirect('trip_detail', trip_id=trip.id)


@login_required
@require_POST
def cancel_invitation(request, trip_id, invitation_id):
    trip = get_object_or_404(Trip, id=trip_id, members__user=request.user)
    invitation = get_object_or_404(Invitation, id=invitation_id, trip=trip, status='pending')

    if request.user != trip.owner and request.user != invitation.invited_by:
        raise Http404

    email = invitation.email
    invitation.delete()
    messages.success(request, f'Invitation to {email} was cancelled.')
    return redirect('trip_detail', trip_id=trip.id)

def accept_invitation(request, token):
    invitation = get_object_or_404(
        Invitation.objects.select_related('trip', 'invited_by'),
        token=token,
    )

    if invitation.status == 'accepted':
        messages.info(request, 'This invitation has already been accepted.')
        return render(request, 'trips/invitation_response.html', {
            'state': 'accepted',
            'invitation': invitation,
            'trip': invitation.trip,
            'message': f'This invitation was already accepted. You are part of the trip to {invitation.trip.destination}.',
        })

    if invitation.status == 'rejected':
        messages.info(request, 'This invitation was previously declined.')
        return render(request, 'trips/invitation_response.html', {
            'state': 'rejected',
            'invitation': invitation,
            'trip': invitation.trip,
            'message': 'This invitation was previously rejected.',
        })

    if not request.user.is_authenticated:
        messages.info(request, f'Please log in or sign up with {invitation.email} to accept this invitation.')
        return redirect(f"{reverse('login')}?{urlencode({'next': request.get_full_path()})}")

    if (request.user.email or '').strip().lower() != (invitation.email or '').strip().lower():
        messages.error(
            request,
            f'This invitation was sent to {invitation.email}, but you are logged in as {request.user.email or request.user.username}.'
        )
        return render(request, 'trips/invitation_response.html', {
            'state': 'wrong_account',
            'invitation': invitation,
            'trip': invitation.trip,
        })

    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.is_complete():
        messages.warning(request, 'Please complete your profile to join this trip.')
        return redirect(f"{reverse('edit_profile')}?{urlencode({'next': request.get_full_path()})}")

    with transaction.atomic():
        TripMember.objects.get_or_create(
            trip=invitation.trip, user=request.user, defaults={'role': 'member'}
        )
        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

    messages.success(request, f'You successfully joined the trip to {invitation.trip.destination}!')
    return render(request, 'trips/invitation_response.html', {
        'state': 'accepted',
        'invitation': invitation,
        'trip': invitation.trip,
        'message': f'You successfully accepted the invitation! Welcome to the trip to {invitation.trip.destination}.',
    })


def reject_invitation(request, token):
    invitation = get_object_or_404(
        Invitation.objects.select_related('trip', 'invited_by'),
        token=token,
    )

    if invitation.status == 'accepted':
        messages.info(request, 'This invitation was already accepted.')
        return render(request, 'trips/invitation_response.html', {
            'state': 'accepted',
            'invitation': invitation,
            'trip': invitation.trip,
            'message': 'This invitation was already accepted and cannot be declined.',
        })

    if invitation.status == 'rejected':
        return render(request, 'trips/invitation_response.html', {
            'state': 'rejected',
            'invitation': invitation,
            'trip': invitation.trip,
            'message': 'This invitation has already been declined.',
        })

    with transaction.atomic():
        invitation.status = 'rejected'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

    messages.info(request, f'You have declined the invitation to join the trip to {invitation.trip.destination}.')
    return render(request, 'trips/invitation_response.html', {
        'state': 'rejected',
        'invitation': invitation,
        'trip': invitation.trip,
        'message': f'You have safely declined the invitation to join the trip to {invitation.trip.destination}.',
    })

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
        if not profile.email_verified:
            messages.error(
                request,
                'Verify your email first. Check your inbox or use the Resend button on your home page. After verifying, open your invitation link again.'
            )
            return redirect('home')
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
    if not profile.email_verified:
        messages.error(
            request,
            'Verify your email first. Check your inbox or use the Resend button on your home page.'
        )
        return redirect('home')

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
        .prefetch_related('trip__members')
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