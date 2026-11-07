from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AiChatbotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='password123'
        )

    def test_chatbot_unauthenticated(self):
        response = self.client.post(
            reverse('chatbot_reply'),
            data='{"message": "What is good in Paris?"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

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
