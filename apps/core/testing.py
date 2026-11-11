from django.core.cache import cache
from rest_framework import test


class APITestCase(test.APITestCase):
    """Base test case: every test starts with fresh rate-limit counters."""

    def setUp(self):
        super().setUp()
        cache.clear()
