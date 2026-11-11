from unittest import mock

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status

from apps.core.testing import APITestCase
from apps.core.throttling import ScopedRateThrottle

from .models import WaitlistEntry


@override_settings(WAITLIST_CONFIRMATION_EMAILS=True)
class WaitlistSignupTests(APITestCase):
    url = reverse('waitlist-signup')

    def test_signup_creates_entry_and_sends_confirmation(self):
        response = self.client.post(self.url, {'email': 'pet.lover@example.com'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'pet.lover@example.com')

        entry = WaitlistEntry.objects.get()
        self.assertIsNotNone(entry.confirmation_sent_at)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['pet.lover@example.com'])
        self.assertEqual(message.subject, "You're on the Love and Tails waitlist")
        self.assertIn("You're on the list!", message.body)
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn("You're on the list!", html)

    def test_duplicate_signup_is_idempotent_and_does_not_resend(self):
        self.client.post(self.url, {'email': 'pet.lover@example.com'})
        response = self.client.post(self.url, {'email': '  Pet.Lover@Example.com '})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WaitlistEntry.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(self.url, {'email': 'not-an-email'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertFalse(WaitlistEntry.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_signup_succeeds_even_if_email_delivery_fails(self):
        with mock.patch('apps.waitlist.emails.send_templated_email', side_effect=OSError('SMTP down')):
            with self.assertLogs('apps.waitlist.emails', level='ERROR'):
                response = self.client.post(self.url, {'email': 'pet.lover@example.com'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(WaitlistEntry.objects.get().confirmation_sent_at)

    @override_settings(WAITLIST_CONFIRMATION_EMAILS=False)
    def test_signup_is_saved_without_email_when_sending_is_off(self):
        response = self.client.post(self.url, {'email': 'pet.lover@example.com'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], "You're on the waitlist!")
        self.assertIsNone(WaitlistEntry.objects.get().confirmation_sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_signups_are_rate_limited_per_ip(self):
        limit = int(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['waitlist'].split('/')[0])
        for i in range(limit):
            response = self.client.post(self.url, {'email': f'user{i}@example.com'})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.url, {'email': 'one-too-many@example.com'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(WaitlistEntry.objects.filter(email='one-too-many@example.com').exists())

    def test_signup_still_works_when_redis_is_down(self):
        with mock.patch.object(ScopedRateThrottle, 'cache') as broken_cache:
            broken_cache.get.side_effect = RedisConnectionError('Redis is down')
            with self.assertLogs('apps.core.throttling', level='ERROR'):
                response = self.client.post(self.url, {'email': 'pet.lover@example.com'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WaitlistEntry.objects.filter(email='pet.lover@example.com').exists())
