from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class RegisterViewTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'garden-user',
                'email': 'garden@example.com',
                'password': 'StrongGardenPass123!',
                'password2': 'StrongGardenPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(
            get_user_model().objects.filter(username='garden-user').exists()
        )

    def test_register_rejects_duplicate_username(self):
        get_user_model().objects.create_user(
            username='garden-user',
            password='StrongGardenPass123!',
        )

        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'garden-user',
                'password': 'AnotherGardenPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
