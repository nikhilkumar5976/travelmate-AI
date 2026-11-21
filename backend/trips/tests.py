import json
import shutil
import tempfile
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from itinerary.models import Day, Stop
from trips.emails import send_invitation_email
from trips.forms import TripForm
from trips.models import Trip, TripMember, Invitation

TINY_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
    b'\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
    b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
)


def create_test_image(name='test.gif'):
    return SimpleUploadedFile(name, TINY_GIF, content_type='image/gif')


class TripsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.override_media = override_settings(MEDIA_ROOT=cls.temp_dir.name)
        cls.override_media.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.override_media.disable()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.owner = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        self.owner_profile = Profile.objects.create(
            user=self.owner, phone='1234567890', photo=create_test_image('alice.gif'), email_verified=True
        )

        self.member = User.objects.create_user(
            username='bob', email='bob@example.com', password='password123'
        )
        self.member_profile = Profile.objects.create(
            user=self.member, phone='0987654321', photo=create_test_image('bob.gif'), email_verified=True
        )

        self.stranger = User.objects.create_user(
            username='charlie', email='charlie@example.com', password='password123'
        )
        self.stranger_profile = Profile.objects.create(
            user=self.stranger, phone='1112223333', photo=create_test_image('charlie.gif'), email_verified=True
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
        self.owner_member = TripMember.objects.create(trip=self.trip, user=self.owner, role='owner')
        self.member_member = TripMember.objects.create(trip=self.trip, user=self.member, role='member')

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

    # ---------------------------------------------------------
    # 1. Logged-out user visiting trip page
    # ---------------------------------------------------------
    def test_rule_1_logged_out_user_redirected_to_login(self):
        """1. A logged-out user visiting a trip page is redirected to the login page."""
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    # ---------------------------------------------------------
    # 2. Incomplete profile cannot create trip
    # ---------------------------------------------------------
    def test_rule_2_incomplete_profile_cannot_create_trip(self):
        """2. A user with an incomplete profile (no photo or phone) cannot create a trip and is redirected to edit_profile."""
        user_no_photo = User.objects.create_user(
            username='nophoto', email='nophoto@example.com', password='password123'
        )
        Profile.objects.create(user=user_no_photo, phone='1234567890', photo='', email_verified=True)
        self.client.force_login(user_no_photo)

        response_get = self.client.get(reverse('create_trip'))
        self.assertRedirects(response_get, reverse('edit_profile'))

        response_post = self.client.post(reverse('create_trip'), {
            'destination': 'Paris', 'num_days': 3, 'budget': 1000, 'interests': ['food']
        })
        self.assertRedirects(response_post, reverse('edit_profile'))
        self.assertFalse(Trip.objects.filter(destination='Paris').exists())

        user_no_phone = User.objects.create_user(
            username='nophone', email='nophone@example.com', password='password123'
        )
        Profile.objects.create(user=user_no_phone, phone='', photo=create_test_image('nophone.gif'), email_verified=True)
        self.client.force_login(user_no_phone)

        response_get2 = self.client.get(reverse('create_trip'))
        self.assertRedirects(response_get2, reverse('edit_profile'))

        response_post2 = self.client.post(reverse('create_trip'), {
            'destination': 'Berlin', 'num_days': 3, 'budget': 1000, 'interests': ['food']
        })
        self.assertRedirects(response_post2, reverse('edit_profile'))
        self.assertFalse(Trip.objects.filter(destination='Berlin').exists())

    # ---------------------------------------------------------
    # 3. Unverified email cannot create trip
    # ---------------------------------------------------------
    def test_rule_3_unverified_email_cannot_create_trip(self):
        """3. A user whose email is not verified cannot create a trip (only if the email_verified field exists on Profile)."""
        if hasattr(Profile, 'email_verified'):
            unverified_user = User.objects.create_user(
                username='unverified', email='unverified@example.com', password='password123'
            )
            Profile.objects.create(
                user=unverified_user, phone='1234567890', photo=create_test_image('unverified.gif'), email_verified=False
            )
            self.client.force_login(unverified_user)

            response_get = self.client.get(reverse('create_trip'))
            self.assertRedirects(response_get, reverse('home'))

            response_post = self.client.post(reverse('create_trip'), {
                'destination': 'Rome', 'num_days': 3, 'budget': 1000, 'interests': ['food']
            })
            self.assertRedirects(response_post, reverse('home'))
            self.assertFalse(Trip.objects.filter(destination='Rome').exists())

    # ---------------------------------------------------------
    # 4. Only owner can edit, delete, generate, remove member
    # ---------------------------------------------------------
    def test_rule_4_only_owner_can_edit_trip(self):
        """4a. Only the trip owner can edit a trip. Normal member gets 404."""
        self.client.force_login(self.member)
        response_get = self.client.get(reverse('edit_trip', args=[self.trip.id]))
        self.assertEqual(response_get.status_code, 404)

        response_post = self.client.post(reverse('edit_trip', args=[self.trip.id]), {
            'destination': 'Osaka', 'num_days': 4, 'budget': 2000, 'interests': ['food']
        })
        self.assertEqual(response_post.status_code, 404)

        self.client.force_login(self.owner)
        owner_get = self.client.get(reverse('edit_trip', args=[self.trip.id]))
        self.assertEqual(owner_get.status_code, 200)

        owner_post = self.client.post(reverse('edit_trip', args=[self.trip.id]), {
            'destination': 'Osaka', 'num_days': 4, 'budget': 2000, 'interests': ['food']
        })
        self.assertRedirects(owner_post, reverse('trip_detail', args=[self.trip.id]))
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.destination, 'Osaka')

    def test_rule_4_only_owner_can_delete_trip(self):
        """4b. Only the trip owner can delete a trip. Normal member gets 404."""
        self.client.force_login(self.member)
        response_get = self.client.get(reverse('delete_trip', args=[self.trip.id]))
        self.assertEqual(response_get.status_code, 404)

        response_post = self.client.post(reverse('delete_trip', args=[self.trip.id]))
        self.assertEqual(response_post.status_code, 404)
        self.assertTrue(Trip.objects.filter(id=self.trip.id).exists())

        self.client.force_login(self.owner)
        owner_get = self.client.get(reverse('delete_trip', args=[self.trip.id]))
        self.assertEqual(owner_get.status_code, 200)

        owner_post = self.client.post(reverse('delete_trip', args=[self.trip.id]))
        self.assertRedirects(owner_post, reverse('my_trips'))
        self.assertFalse(Trip.objects.filter(id=self.trip.id).exists())

    @patch('ai.services.call_llm')
    def test_rule_4_only_owner_can_generate_itinerary(self, mock_llm):
        """4c. Only the trip owner can generate an itinerary. Normal member gets 404."""
        mock_llm.return_value = json.dumps({
            "summary": "AI summary",
            "days": [
                {
                    "day_number": i,
                    "title": f"Day {i}",
                    "stops": [
                        {
                            "name": f"Place {i}",
                            "description": "Desc",
                            "time_of_day": "morning",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 20,
                        }
                    ],
                }
                for i in range(1, self.trip.num_days + 1)
            ],
            "budget_warning": "",
        })
        self.client.force_login(self.member)
        response = self.client.post(reverse('generate_itinerary', args=[self.trip.id]))
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.owner)
        owner_response = self.client.post(reverse('generate_itinerary', args=[self.trip.id]))
        self.assertRedirects(owner_response, reverse('trip_detail', args=[self.trip.id]))

    def test_rule_4_only_owner_can_remove_member(self):
        """4d. Only the trip owner can remove a member. Normal member gets 404."""
        extra_user = User.objects.create_user(
            username='david', email='david@example.com', password='password123'
        )
        Profile.objects.create(
            user=extra_user, phone='5555555555', photo=create_test_image('david.gif'), email_verified=True
        )
        TripMember.objects.create(trip=self.trip, user=extra_user, role='member')

        # Normal member gets 404
        self.client.force_login(self.member)
        response = self.client.post(reverse('remove_member', args=[self.trip.id, extra_user.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(TripMember.objects.filter(trip=self.trip, user=extra_user).exists())

        # Owner can remove member
        self.client.force_login(self.owner)
        owner_response = self.client.post(reverse('remove_member', args=[self.trip.id, extra_user.id]))
        self.assertRedirects(owner_response, reverse('trip_detail', args=[self.trip.id]))
        self.assertFalse(TripMember.objects.filter(trip=self.trip, user=extra_user).exists())

    # ---------------------------------------------------------
    # 5. Non-member gets 404 on trip page and chat page
    # ---------------------------------------------------------
    def test_rule_5_non_member_gets_404_on_trip_page_and_chat_page(self):
        """5. A user who is not a member of a trip gets a 404 on the trip page and on the chat page."""
        self.client.force_login(self.stranger)
        trip_response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(trip_response.status_code, 404)

        chat_response = self.client.get(reverse('trip_chat', args=[self.trip.id]))
        self.assertEqual(chat_response.status_code, 404)

    # ---------------------------------------------------------
    # 6. Trip form rejects invalid inputs
    # ---------------------------------------------------------
    def test_rule_6_trip_form_rejections(self):
        """6. The trip form rejects: empty fields, 0 days, 16 days, budget 0, and no interests."""
        # Empty fields
        form_empty = TripForm(data={})
        self.assertFalse(form_empty.is_valid())
        self.assertIn('destination', form_empty.errors)
        self.assertIn('num_days', form_empty.errors)
        self.assertIn('budget', form_empty.errors)
        self.assertIn('interests', form_empty.errors)

        # 0 days
        form_0_days = TripForm(data={
            'destination': 'Kyoto', 'num_days': 0, 'budget': 1000, 'interests': ['food']
        })
        self.assertFalse(form_0_days.is_valid())
        self.assertIn('num_days', form_0_days.errors)

        # 16 days (max is 15)
        form_16_days = TripForm(data={
            'destination': 'Kyoto', 'num_days': 16, 'budget': 1000, 'interests': ['food']
        })
        self.assertFalse(form_16_days.is_valid())
        self.assertIn('num_days', form_16_days.errors)

        # budget 0
        form_0_budget = TripForm(data={
            'destination': 'Kyoto', 'num_days': 3, 'budget': 0, 'interests': ['food']
        })
        self.assertFalse(form_0_budget.is_valid())
        self.assertIn('budget', form_0_budget.errors)

        # no interests
        form_no_interests = TripForm(data={
            'destination': 'Kyoto', 'num_days': 3, 'budget': 1000, 'interests': []
        })
        self.assertFalse(form_no_interests.is_valid())
        self.assertIn('interests', form_no_interests.errors)

    # ---------------------------------------------------------
    # 7. Invitation only accepted by matching email
    # ---------------------------------------------------------
    def test_rule_7_invitation_only_accepted_by_matching_email(self):
        """7. An invitation can only be accepted by a user whose email matches the invitation email."""
        invite = Invitation.objects.create(
            trip=self.trip,
            email='guest@example.com',
            invited_by=self.owner,
        )

        # Non-matching user tries to accept
        wrong_user = User.objects.create_user(
            username='wronguser', email='wrong@example.com', password='password123'
        )
        Profile.objects.create(
            user=wrong_user, phone='1234567890', photo=create_test_image('wrong.gif'), email_verified=True
        )
        self.client.force_login(wrong_user)

        response_wrong = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response_wrong.status_code, 200)
        self.assertEqual(response_wrong.context['state'], 'wrong_account')
        self.assertFalse(TripMember.objects.filter(trip=self.trip, user=wrong_user).exists())

        # Matching user accepts
        right_user = User.objects.create_user(
            username='rightuser', email='guest@example.com', password='password123'
        )
        Profile.objects.create(
            user=right_user, phone='0987654321', photo=create_test_image('right.gif'), email_verified=True
        )
        self.client.force_login(right_user)

        response_right = self.client.get(reverse('accept_invitation', args=[invite.token]))
        self.assertEqual(response_right.status_code, 200)
        self.assertEqual(response_right.context['state'], 'accepted')
        self.assertTrue(TripMember.objects.filter(trip=self.trip, user=right_user).exists())
        invite.refresh_from_db()
        self.assertEqual(invite.status, 'accepted')

    # ---------------------------------------------------------
    # 8. Owner leaves succession & last member leaves deletes trip
    # ---------------------------------------------------------
    def test_rule_8_owner_leaves_succession_and_last_member_leaves_deletes_trip(self):
        """8. When owner leaves with other members, first-joined member becomes owner. When last leaves, trip is deleted."""
        member2 = User.objects.create_user(
            username='member2', email='m2@example.com', password='password123'
        )
        Profile.objects.create(
            user=member2, phone='4445556666', photo=create_test_image('m2.gif'), email_verified=True
        )
        member2_tm = TripMember.objects.create(trip=self.trip, user=member2, role='member')

        # Ensure explicit ordering of joined_at
        now = timezone.now()
        TripMember.objects.filter(id=self.owner_member.id).update(joined_at=now - timezone.timedelta(minutes=30))
        TripMember.objects.filter(id=self.member_member.id).update(joined_at=now - timezone.timedelta(minutes=20))
        TripMember.objects.filter(id=member2_tm.id).update(joined_at=now - timezone.timedelta(minutes=10))

        # Owner leaves
        self.client.force_login(self.owner)
        response_owner_leaves = self.client.post(reverse('leave_trip', args=[self.trip.id]))
        self.assertRedirects(response_owner_leaves, reverse('my_trips'))

        # self.member joined first, so self.member becomes the new owner
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.owner, self.member)
        self.member_member.refresh_from_db()
        self.assertEqual(self.member_member.role, 'owner')
        self.assertFalse(TripMember.objects.filter(trip=self.trip, user=self.owner).exists())

        # member2 leaves
        self.client.force_login(member2)
        response_member2_leaves = self.client.post(reverse('leave_trip', args=[self.trip.id]))
        self.assertRedirects(response_member2_leaves, reverse('my_trips'))
        self.assertEqual(self.trip.members.count(), 1)

        # Last member (self.member) leaves
        self.client.force_login(self.member)
        response_last_leaves = self.client.post(reverse('leave_trip', args=[self.trip.id]))
        self.assertRedirects(response_last_leaves, reverse('my_trips'))

        # Trip is deleted
        self.assertFalse(Trip.objects.filter(id=self.trip.id).exists())

    # ---------------------------------------------------------
    # 9. Budget per person equals total budget / members
    # ---------------------------------------------------------
    def test_rule_9_budget_per_person_equals_total_divided_by_members(self):
        """9. Budget per person on the trip page equals the total budget divided by the number of members."""
        self.client.force_login(self.owner)
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 200)

        # 2 members: owner and member
        expected_2 = self.trip.budget / 2
        self.assertEqual(response.context['budget_per_person'], expected_2)
        self.assertContains(response, f"₹{expected_2:.2f} / person")

        # Add a 3rd member
        user3 = User.objects.create_user(
            username='third', email='third@example.com', password='password123'
        )
        Profile.objects.create(
            user=user3, phone='3333333333', photo=create_test_image('third.gif'), email_verified=True
        )
        TripMember.objects.create(trip=self.trip, user=user3, role='member')

        response3 = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        expected_3 = self.trip.budget / 3
        self.assertEqual(response3.context['budget_per_person'], expected_3)
        self.assertContains(response3, f"₹{expected_3:.2f} / person")

    # ---------------------------------------------------------
    # Additional baseline trip tests
    # ---------------------------------------------------------
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
        self.assertContains(response, '₹1500.00 budget')

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
        self.assertContains(response, '₹1500.00')
        self.assertContains(response, 'Estimated cost per person: ₹10.00')

    def test_trip_detail_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('trip_detail', args=[self.trip.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'trips/trip_detail.html')
        self.assertNotContains(response, 'Regenerate itinerary')

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
