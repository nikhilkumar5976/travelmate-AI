from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from chat.models import ChatMessage
from trips.models import Trip, TripMember


class ChatReadTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        Profile.objects.create(user=self.user1, phone='1234567890')

        self.user2 = User.objects.create_user(
            username='bob', email='bob@example.com', password='password123'
        )
        Profile.objects.create(user=self.user2, phone='0987654321')

        self.stranger = User.objects.create_user(
            username='charlie', email='charlie@example.com', password='password123'
        )

        self.trip = Trip.objects.create(
            owner=self.user1,
            destination='Kyoto',
            num_days=2,
            budget=Decimal('800.00'),
            interests=['history'],
        )
        TripMember.objects.create(trip=self.trip, user=self.user1, role='owner')
        TripMember.objects.create(trip=self.trip, user=self.user2, role='member')

        self.msg = ChatMessage.objects.create(
            trip=self.trip, sender=self.user1, text='Looking forward to Kyoto!'
        )

    def test_trip_chat_unauthenticated(self):
        response = self.client.get(reverse('trip_chat', args=[self.trip.id]))
        self.assertEqual(response.status_code, 302)

    def test_trip_chat_member(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('trip_chat', args=[self.trip.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/trip_chat.html')
        self.assertContains(response, 'Looking forward to Kyoto!')
        self.assertContains(response, 'alice')

    def test_trip_chat_stranger(self):
        self.client.force_login(self.stranger)
        response = self.client.get(reverse('trip_chat', args=[self.trip.id]))
        self.assertEqual(response.status_code, 404)
