from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status

from apps.core.testing import APITestCase
from apps.users.models import User


def rate_limit(scope):
    return int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'][scope].split('/')[0])


class HealthCheckTests(APITestCase):
    def test_health_reports_database_and_cache_ok(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok', 'database': 'ok', 'cache': 'ok'})

    def test_cache_outage_is_degraded_not_down(self):
        with mock.patch('apps.core.views.cache.set', side_effect=RedisConnectionError('Redis is down')):
            response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'degraded', 'database': 'ok', 'cache': 'unavailable'})

    def test_health_is_never_rate_limited(self):
        for _ in range(rate_limit('anon') + 1):
            response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_liveness_does_not_touch_database_or_cache(self):
        with (
            mock.patch('apps.core.views.cache.set') as cache_set,
            self.assertNumQueries(0),
        ):
            response = self.client.get(reverse('health-live'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok'})
        cache_set.assert_not_called()


class DefaultRateLimitTests(APITestCase):
    def test_anonymous_requests_are_rate_limited(self):
        url = reverse('token-verify')
        for _ in range(rate_limit('anon')):
            self.assertNotEqual(self.client.post(url, {'token': 'x'}).status_code, 429)

        response = self.client.post(url, {'token': 'x'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Retry-After', response.headers)


class ApiDocsTests(APITestCase):
    doc_urls = ('schema', 'swagger-ui', 'redoc')

    @override_settings(API_DOCS_PUBLIC=True)
    def test_docs_are_public_when_enabled(self):
        for name in self.doc_urls:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_200_OK)

    @override_settings(API_DOCS_PUBLIC=False)
    def test_docs_are_staff_only_when_not_public(self):
        user = User.objects.create_user(email='user@example.com', password='Str0ng-pass-123')
        staff = User.objects.create_user(email='staff@example.com', password='Str0ng-pass-123', is_staff=True)

        for name in self.doc_urls:
            with self.subTest(name=name, who='anonymous'):
                self.client.force_authenticate(None)
                self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_401_UNAUTHORIZED)
            with self.subTest(name=name, who='regular user'):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_403_FORBIDDEN)
            with self.subTest(name=name, who='staff'):
                self.client.force_authenticate(staff)
                self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_200_OK)

    def test_root_redirects_to_swagger_ui(self):
        response = self.client.get('/')
        self.assertRedirects(response, reverse('swagger-ui'), fetch_redirect_response=False)


@override_settings(CORS_ALLOWED_ORIGINS=['https://app.example.com'])
class CorsTests(APITestCase):
    def test_allowed_origin_can_call_the_api_without_cookies(self):
        response = self.client.get(reverse('health'), headers={'Origin': 'https://app.example.com'})
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'https://app.example.com')
        self.assertNotIn('Access-Control-Allow-Credentials', response.headers)

    def test_other_origins_are_not_allowed(self):
        response = self.client.get(reverse('health'), headers={'Origin': 'https://evil.example.com'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_cors_only_applies_to_the_api(self):
        response = self.client.get(reverse('admin:login'), headers={'Origin': 'https://app.example.com'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)
