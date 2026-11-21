import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ai.services import (
    parse_itinerary,
    save_itinerary,
    generate_itinerary,
    ItineraryError,
)
from itinerary.models import Day, Stop
from trips.models import Trip, TripMember


class ParseItineraryTests(TestCase):
    def setUp(self):
        self.valid_data = {
            "summary": "A delightful 2-day tour.",
            "budget_warning": "",
            "days": [
                {
                    "day_number": 1,
                    "title": "Day 1 Highlights",
                    "stops": [
                        {
                            "name": "City Park",
                            "description": "A relaxing walk in the park.",
                            "time_of_day": "morning",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 0,
                        }
                    ],
                },
                {
                    "day_number": 2,
                    "title": "Day 2 Culinary",
                    "stops": [
                        {
                            "name": "Food Street",
                            "description": "Taste local cuisines.",
                            "time_of_day": "afternoon",
                            "category": "food",
                            "estimated_cost_per_person": 25,
                        }
                    ],
                },
            ],
        }

    def test_parse_valid_json(self):
        text = json.dumps(self.valid_data)
        result = parse_itinerary(text, num_days=2)
        self.assertEqual(result, self.valid_data)

    def test_parse_json_wrapped_in_extra_text_and_code_fences(self):
        text = (
            "Here is the requested itinerary:\n"
            "```json\n"
            f"{json.dumps(self.valid_data)}\n"
            "```\n"
            "Let me know if you need any adjustments!"
        )
        result = parse_itinerary(text, num_days=2)
        self.assertEqual(result, self.valid_data)

    def test_reject_no_json(self):
        with self.assertRaises(ItineraryError) as ctx:
            parse_itinerary("This response does not contain any JSON brackets.", num_days=2)
        self.assertIn("The AI reply did not contain JSON.", str(ctx.exception))

    def test_reject_invalid_json(self):
        with self.assertRaises(ItineraryError) as ctx:
            parse_itinerary("{this is definitely not valid json: true,}", num_days=2)
        self.assertIn("The AI reply was not valid JSON.", str(ctx.exception))

    def test_reject_wrong_number_of_days(self):
        # 2 days in data, but 3 days requested
        with self.assertRaises(ItineraryError) as ctx:
            parse_itinerary(json.dumps(self.valid_data), num_days=3)
        self.assertIn("The AI returned the wrong number of days.", str(ctx.exception))

        # days is not a list
        bad_days = {"summary": "Trip", "days": "not a list"}
        with self.assertRaises(ItineraryError) as ctx:
            parse_itinerary(json.dumps(bad_days), num_days=1)
        self.assertIn("The AI returned the wrong number of days.", str(ctx.exception))

    def test_reject_day_with_no_stops(self):
        empty_stops_data = {
            "summary": "Trip",
            "days": [
                {
                    "day_number": 1,
                    "title": "Day 1",
                    "stops": [],
                }
            ],
        }
        with self.assertRaises(ItineraryError) as ctx:
            parse_itinerary(json.dumps(empty_stops_data), num_days=1)
        self.assertIn("A day had no stops.", str(ctx.exception))


class SaveItineraryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        self.trip = Trip.objects.create(
            owner=self.user,
            destination='Tokyo',
            num_days=2,
            budget=Decimal('2000.00'),
            interests=['food', 'sightseeing'],
        )

    def test_save_itinerary_creates_days_and_stops_and_fixes_bad_values(self):
        data = {
            "summary": "Tokyo tour summary.",
            "budget_warning": "High cost destination.",
            "days": [
                {
                    "day_number": 1,
                    "title": "Day 1",
                    "stops": [
                        {
                            "name": "Tokyo Tower",
                            "description": "Sightseeing stop.",
                            "time_of_day": "morning",
                            "category": "unknown_category_xyz",  # should become 'activity'
                            "estimated_cost_per_person": -15.50,  # should become 0.00
                        },
                        {
                            "name": "Ramen Shop",
                            "description": "Lunch stop.",
                            "time_of_day": "afternoon",
                            "category": "food",
                            "estimated_cost_per_person": 12.00,
                        },
                    ],
                },
                {
                    "day_number": 2,
                    "title": "Day 2",
                    "stops": [
                        {
                            "name": "Ueno Park",
                            "description": "Park stroll.",
                            "time_of_day": "morning",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 0,
                        }
                    ],
                },
            ],
        }

        save_itinerary(self.trip, data)

        self.assertEqual(self.trip.days.count(), 2)
        self.assertEqual(Stop.objects.filter(day__trip=self.trip).count(), 3)

        # Check trip fields updated
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.summary, "Tokyo tour summary.")
        self.assertEqual(self.trip.budget_warning, "High cost destination.")

        # Check fixed bad values on first stop
        day1 = self.trip.days.get(day_number=1)
        first_stop = day1.stops.get(name="Tokyo Tower")
        self.assertEqual(first_stop.category, "activity")
        self.assertEqual(first_stop.estimated_cost_per_person, Decimal("0.00"))

    def test_save_itinerary_replaces_old_itinerary_instead_of_duplicating(self):
        data1 = {
            "summary": "First version",
            "budget_warning": "",
            "days": [
                {
                    "day_number": 1,
                    "title": "Old Day 1",
                    "stops": [
                        {
                            "name": "Old Stop 1",
                            "description": "Old",
                            "time_of_day": "morning",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 10,
                        }
                    ],
                },
                {
                    "day_number": 2,
                    "title": "Old Day 2",
                    "stops": [
                        {
                            "name": "Old Stop 2",
                            "description": "Old",
                            "time_of_day": "afternoon",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 20,
                        }
                    ],
                },
            ],
        }
        save_itinerary(self.trip, data1)
        self.assertEqual(self.trip.days.count(), 2)
        self.assertEqual(Stop.objects.filter(day__trip=self.trip).count(), 2)

        data2 = {
            "summary": "New replaced version",
            "budget_warning": "New warning",
            "days": [
                {
                    "day_number": 1,
                    "title": "New Day 1",
                    "stops": [
                        {
                            "name": "Brand New Stop",
                            "description": "New",
                            "time_of_day": "morning",
                            "category": "food",
                            "estimated_cost_per_person": 30,
                        }
                    ],
                }
            ],
        }
        save_itinerary(self.trip, data2)

        # Old days and stops replaced
        self.assertEqual(self.trip.days.count(), 1)
        self.assertEqual(Stop.objects.filter(day__trip=self.trip).count(), 1)
        new_day = self.trip.days.first()
        self.assertEqual(new_day.title, "New Day 1")
        new_stop = new_day.stops.first()
        self.assertEqual(new_stop.name, "Brand New Stop")
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.summary, "New replaced version")


class GenerateItineraryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )
        self.trip = Trip.objects.create(
            owner=self.user,
            destination='Kyoto',
            num_days=2,
            budget=Decimal('1500.00'),
            interests=['culture', 'food'],
        )
        TripMember.objects.create(trip=self.trip, user=self.user, role='owner')

    @patch('ai.services.call_llm')
    def test_generate_itinerary_retries_on_unusable_first_reply(self, mock_call_llm):
        good_data = {
            "summary": "2 days in Kyoto",
            "budget_warning": "",
            "days": [
                {
                    "day_number": 1,
                    "title": "Day 1 Temples",
                    "stops": [
                        {
                            "name": "Kinkaku-ji",
                            "description": "Golden Pavilion",
                            "time_of_day": "morning",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 5,
                        }
                    ],
                },
                {
                    "day_number": 2,
                    "title": "Day 2 Bamboo",
                    "stops": [
                        {
                            "name": "Arashiyama",
                            "description": "Bamboo Grove",
                            "time_of_day": "afternoon",
                            "category": "sightseeing",
                            "estimated_cost_per_person": 0,
                        }
                    ],
                },
            ],
        }

        # First reply is unusable (invalid JSON), second reply is valid JSON
        mock_call_llm.side_effect = [
            "Sorry, could not generate a plan right now.",
            json.dumps(good_data),
        ]

        generate_itinerary(self.trip)

        # Verified retry occurred
        self.assertEqual(mock_call_llm.call_count, 2)
        self.assertEqual(self.trip.days.count(), 2)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.summary, "2 days in Kyoto")


class AiChatbotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )

    def test_chatbot_unauthenticated_rejected_401(self):
        response = self.client.post(
            reverse('chatbot_reply'),
            data='{"message": "What is good in Paris?"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'error': 'Please log in to use the assistant.'})

    def test_chatbot_empty_message_rejected_400(self):
        self.client.force_login(self.user)

        # Empty string
        response_empty = self.client.post(
            reverse('chatbot_reply'),
            data='{"message": ""}',
            content_type='application/json',
        )
        self.assertEqual(response_empty.status_code, 400)
        self.assertEqual(response_empty.json(), {'error': 'Please type a question.'})

        # Whitespace-only string
        response_spaces = self.client.post(
            reverse('chatbot_reply'),
            data='{"message": "   \\n\\t  "}',
            content_type='application/json',
        )
        self.assertEqual(response_spaces.status_code, 400)
        self.assertEqual(response_spaces.json(), {'error': 'Please type a question.'})

    def test_chatbot_message_over_500_characters_rejected_400(self):
        self.client.force_login(self.user)
        long_message = 'A' * 501
        response = self.client.post(
            reverse('chatbot_reply'),
            data=json.dumps({"message": long_message}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('500 characters', response.json().get('error', ''))

    def test_chatbot_method_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('chatbot_reply'))
        self.assertEqual(response.status_code, 405)

    def test_chatbot_invalid_payload(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('chatbot_reply'),
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    @patch('ai.views.call_llm')
    def test_chatbot_success(self, mock_call_llm):
        mock_call_llm.return_value = 'Spring and autumn are the best seasons to visit Tokyo.'
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('chatbot_reply'),
            data='{"message": "Best time to visit Tokyo?"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'reply': 'Spring and autumn are the best seasons to visit Tokyo.'},
        )
