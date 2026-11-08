import uuid
from decimal import Decimal

from django.core import mail
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from itinerary.models import Day, Stop
from trips.emails import send_invitation_email
from trips.models import Trip, TripMember, Invitation


class TripsReadTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        self.owner_profile = Profile.objects.create(
            user=self.owner, phone='1234567890', photo='profile_photos/test.jpg'
        )

        self.member = User.objects.create_user(
            username='bob', email='bob@example.com', password='password123'
        )
        self.member_profile = Profile.objects.create(
            user=self.member, phone='0987654321', photo='profile_photos/bob.jpg'
        )

        self.stranger = User.objects.create_user(
            username='charlie', email='charlie@example.com', password='password123'
        )

        self.trip = Trip.objects.create(
            owner=self.owner,
            destination='Tokyo',
            num_days=3,
            budget=Decimal('1500.00'),
            interests=['food', 'sightseeing'],
            summary='3 days exploring Tokyo.',
            budget_warning='Tokyo can be pricey.',
        )
        TripMember.objects.create(trip=self.trip, user=self.owner, role='owner')
        TripMember.objects.create(trip=self.trip, user=self.member, role='member')

        self.day1 = Day.objects.create(trip=self.trip, day_number=1, title='Arrival & Shinjuku')
        Stop.objects.create(
            day=self.day1,
            name='Shinjuku Gyoen',
            description='National garden',
            time_of_day='morning',
            category='sightseeing',
            estimated_cost_per_person=Decimal('10.00'),
            order=1,
        )
        Stop.objects.create(
            day=self.day1,
            name='Ramen Street',
            description='Famous ramen shops',
            time_of_day='afternoon',
            category='food',
            estimated_cost_per_person=Decimal('15.00'),
            order=2,
        )

    def test_my_trips_unauthenticated(self):
        response = self.client.get(reverse('my_trips'))
        self.assertEqual(response.status_code, 302)

    def test_my_trips_authenticated(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('my_trips'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/my_trips.html')
        self.assertContains(response, 'Tokyo')
        self.assertContains(response, '3 days')

    def test_trip_detail_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/trip_detail.html')
        self.assertContains(response, 'Tokyo')
        self.assertContains(response, 'Shinjuku Gyoen')
        self.assertContains(response, 'Ramen Street')
        self.assertContains(response, 'Regenerate itinerary')
        self.assertContains(response, 'Food, sightseeing')

    def test_trip_detail_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/trip_detail.html')
        self.assertNotContains(response, 'Regenerate itinerary')

    def test_trip_detail_stranger_forbidden(self):
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 404)

    def test_invitation_model_uuid_token(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='newguest@example.com',
            invited_by=self.owner,
        )
        self.assertIsInstance(invite.token, uuid.UUID)
        self.assertEqual(invite.status, 'pending')

    def test_send_invitation_email(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='guest@example.com',
            invited_by=self.owner,
        )
        sent = send_invitation_email(invite)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        sent_mail = mail.outbox[0]
        self.assertIn('guest@example.com', sent_mail.to)
        self.assertIn(f'/trips/invitations/{invite.token}/accept/', sent_mail.body)
        self.assertIn(f'/trips/invitations/{invite.token}/reject/', sent_mail.body)

    def test_invitation_detail_anonymous(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='invited@example.com',
            invited_by=self.owner,
        )
        response = self.client.get(reverse('invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/invitation.html')
        self.assertEqual(response.context['state'], 'anonymous')

    def test_invitation_detail_wrong_account(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='invited@example.com',
            invited_by=self.owner,
        )
        self.client.force_login(self.stranger)  # charlie@example.com
        response = self.client.get(reverse('invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['state'], 'wrong_account')

    def test_invitation_detail_ready(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email=self.stranger.email,
            invited_by=self.owner,
        )
        Profile.objects.create(
            user=self.stranger, phone='1112223333', photo='profile_photos/c.jpg'
        )
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['state'], 'ready')

    def test_invitation_detail_closed(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='invited@example.com',
            invited_by=self.owner,
            status='accepted',
        )
        response = self.client.get(reverse('invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['state'], 'closed')

    def test_accept_invitation_unauthenticated(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='charlie@example.com',
            invited_by=self.owner,
        )
        response = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_accept_invitation_wrong_email(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='someoneelse@example.com',
            invited_by=self.owner,
        )
        self.client.force_login(self.stranger)  # charlie@example.com
        response = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/invitation_response.html')
        self.assertEqual(response.context['state'], 'wrong_account')

    def test_accept_invitation_success(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email=self.stranger.email,
            invited_by=self.owner,
        )
        Profile.objects.create(
            user=self.stranger, phone='1112223333', photo='profile_photos/c.jpg'
        )
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/invitation_response.html')
        self.assertEqual(response.context['state'], 'accepted')

        invite.refresh_from_db()
        self.assertEqual(invite.status, 'accepted')
        self.assertIsNotNone(invite.responded_at)
        self.assertTrue(TripMember.objects.filter(trip=self.trip, user=self.stranger).exists())

    def test_accept_invitation_already_accepted(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email=self.stranger.email,
            invited_by=self.owner,
            status='accepted',
        )
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['state'], 'accepted')

    def test_reject_invitation_success(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='guest@example.com',
            invited_by=self.owner,
        )
        response = self.client.get(reverse('reject_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/invitation_response.html')
        self.assertEqual(response.context['state'], 'rejected')

        invite.refresh_from_db()
        self.assertEqual(invite.status, 'rejected')
        self.assertIsNotNone(invite.responded_at)

    def test_reject_invitation_already_rejected(self):
        invite = Invitation.objects.create(
            trip=self.trip,
            email='guest@example.com',
            invited_by=self.owner,
            status='rejected',
        )
        response = self.client.get(reverse('reject_invitation', args=[invite.token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['state'], 'rejected')
