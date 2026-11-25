from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .views import (
    PLANT_IMAGE_CACHE,
    LOCAL_PLANT_PLACEHOLDER,
    SPANISH_PLANT_SEARCH_ALIASES,
    PlantSearchProxy,
    CHILEAN_PLANT_CATALOG,
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


class EmailOrUsernameLoginTests(APITestCase):
    def setUp(self):
        self.password = 'StrongGardenPass123!'
        self.user = get_user_model().objects.create_user(
            username='garden-user',
            email='garden@example.com',
            password=self.password,
        )

    def test_login_with_username_returns_tokens_and_canonical_username(self):
        response = self.client.post(
            '/api/token/',
            {
                'username': 'garden-user',
                'password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['username'], 'garden-user')

    def test_login_with_email_case_insensitive_on_auth_login_and_token(self):
        for endpoint in ('/api/token/', '/api/auth/login/'):
            response = self.client.post(
                endpoint,
                {
                    'username': 'GARDEN@EXAMPLE.COM',
                    'password': self.password,
                },
                format='json',
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('access', response.data)
            self.assertEqual(response.data['username'], 'garden-user')

    def test_login_with_explicit_email_field(self):
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'garden@example.com',
                'password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'garden-user')

    def test_login_with_email_rejects_wrong_password(self):
        response = self.client.post(
            '/api/auth/login/',
            {
                'username': 'garden@example.com',
                'password': 'WrongPassword123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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
    def test_catalog_copihue_resolves_by_scientific_name(self, mock_get):
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            'results': [{
                'default_photo': {'medium_url': 'https://example.com/copihue.jpg'},
            }],
        }
        copihue = next(
            item for item in CHILEAN_PLANT_CATALOG
            if item['common_name'] == 'Copihue'
        )

        normalized = PlantSearchProxy._normalize_catalog([copihue])

        self.assertEqual(
            normalized[0]['thumbnail'],
            'https://example.com/copihue.jpg',
        )

    @patch('core.views.requests.get')
    def test_catalog_never_reuses_generic_local_thumbnail(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError()
        copihue = next(
            item for item in CHILEAN_PLANT_CATALOG
            if item['common_name'] == 'Copihue'
        )

        normalized = PlantSearchProxy._normalize_catalog([copihue])

        self.assertEqual(normalized[0]['thumbnail'], LOCAL_PLANT_PLACEHOLDER)
        self.assertNotEqual(normalized[0]['thumbnail'], copihue['thumbnail'])

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
