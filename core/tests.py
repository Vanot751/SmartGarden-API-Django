from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .views import (
    PLANT_IMAGE_CACHE,
    LOCAL_PLANT_PLACEHOLDER,
    SPANISH_PLANT_SEARCH_ALIASES,
    normalizeScientificName,
    resolvePlantImage,
)


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


class PlantImageResolverTests(SimpleTestCase):
    def setUp(self):
        PLANT_IMAGE_CACHE.clear()

    def test_normalizes_cultivar_and_hybrid_names(self):
        self.assertEqual(
            normalizeScientificName("Acer palmatum 'Bloodgood'"),
            'Acer palmatum',
        )
        self.assertEqual(
            normalizeScientificName('Magnolia × soulangeana'),
            'Magnolia soulangeana',
        )

    def test_manzanilla_has_english_search_aliases(self):
        self.assertIn(
            'chamomile',
            SPANISH_PLANT_SEARCH_ALIASES['manzanilla'],
        )

    @patch('core.views.requests.get')
    def test_uses_inaturalist_before_wikipedia_and_fallback(self, mock_get):
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            'results': [{
                'default_photo': {'medium_url': 'https://example.com/plant.jpg'},
            }],
        }

        resolved = resolvePlantImage("Acer palmatum 'Bloodgood'", 'https://fallback.jpg')

        self.assertEqual(resolved, 'https://example.com/plant.jpg')
        self.assertEqual(mock_get.call_count, 1)
        self.assertIn('q', mock_get.call_args.kwargs['params'])

    @patch('core.views.requests.get')
    def test_rejects_upgrade_fallback_and_uses_placeholder(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError()

        resolved = resolvePlantImage(
            'Unknown plant',
            'https://perenual.com/upgrade_access/test.jpg',
        )

        self.assertEqual(resolved, LOCAL_PLANT_PLACEHOLDER)
