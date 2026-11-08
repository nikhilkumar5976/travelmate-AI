from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Place


class PlacesReadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        self.place1 = Place.objects.create(
            name='Eiffel Tower',
            city='Paris',
            category='sightseeing',
            description='Historic iron tower',
            price_level=2,
            latitude=48.8584,
            longitude=2.2945,
            is_active=True,
        )
        self.place2 = Place.objects.create(
            name='Louvre Museum',
            city='Paris',
            category='sightseeing',
            description='World famous art museum',
            price_level=2,
            is_active=True,
        )
        self.place3 = Place.objects.create(
            name='Shinjuku Gyoen',
            city='Tokyo',
            category='nature',
            description='Beautiful garden in Tokyo',
            price_level=1,
            is_active=True,
        )
        self.inactive_place = Place.objects.create(
            name='Closed Attraction',
            city='Paris',
            category='sightseeing',
            description='Temporarily closed',
            price_level=1,
            is_active=False,
        )

    def test_explore_unauthenticated(self):
        response = self.client.get(reverse('explore'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_explore_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('explore'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'places/explore.html')
        self.assertContains(response, 'Eiffel Tower')
        self.assertContains(response, 'Louvre Museum')
        self.assertContains(response, 'Shinjuku Gyoen')
        self.assertNotContains(response, 'Closed Attraction')

    def test_explore_filter_by_city(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('explore'), {'city': 'Tokyo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shinjuku Gyoen')
        self.assertNotContains(response, 'Eiffel Tower')

    def test_explore_filter_by_category(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('explore'), {'category': 'nature'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shinjuku Gyoen')
        self.assertNotContains(response, 'Eiffel Tower')
