from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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
