from django.conf import settings
from django.urls import reverse
from rest_framework import status

from apps.core.testing import APITestCase

from .models import User


class AuthFlowTests(APITestCase):
    password = 'Str0ng-pass-123'

    def test_register_login_and_fetch_profile(self):
        response = self.client.post(
            reverse('auth-register'),
            {'email': 'Owner@Example.com', 'password': self.password, 'first_name': 'Sam'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        self.assertTrue(User.objects.filter(email='Owner@example.com').exists())

        response = self.client.post(
            reverse('token-obtain-pair'),
            {'email': 'Owner@example.com', 'password': self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(reverse('users-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Sam')

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse('auth-register'),
            {'email': 'weak@example.com', 'password': '123'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('users-me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_cannot_change_email(self):
        user = User.objects.create_user(email='a@example.com', password=self.password)
        self.client.force_authenticate(user)
        response = self.client.patch(reverse('users-me'), {'email': 'b@example.com', 'last_name': 'Lee'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, 'a@example.com')
        self.assertEqual(user.last_name, 'Lee')


class TokenSecurityTests(APITestCase):
    password = 'Str0ng-pass-123'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email='owner@example.com', password=self.password)
        response = self.client.post(
            reverse('token-obtain-pair'), {'email': 'owner@example.com', 'password': self.password}
        )
        self.access, self.refresh = response.data['access'], response.data['refresh']

    def test_password_change_logs_out_every_device(self):
        self.user.set_password('An0ther-strong-pass')
        self.user.save()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(self.client.get(reverse('users-me')).status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials()
        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_for_deleted_user_is_rejected(self):
        self.user.delete()
        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_cannot_be_reused_after_rotation(self):
        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_refresh_token(self):
        self.client.post(reverse('auth-logout'), {'refresh': self.refresh})
        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthRateLimitTests(APITestCase):
    def assert_rate_limited(self, url, scope, payload):
        limit = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'][scope].split('/')[0])
        for _ in range(limit):
            self.assertNotEqual(self.client.post(url, payload).status_code, 429)
        self.assertEqual(self.client.post(url, payload).status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_attempts_are_rate_limited(self):
        self.assert_rate_limited(
            reverse('token-obtain-pair'), 'login', {'email': 'owner@example.com', 'password': 'guess'}
        )

    def test_registrations_are_rate_limited(self):
        self.assert_rate_limited(reverse('auth-register'), 'register', {'email': 'not-an-email'})
