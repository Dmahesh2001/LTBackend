from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_reports_database_ok(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok', 'database': 'ok'})


class ApiDocsTests(APITestCase):
    def test_schema_and_swagger_ui_are_public(self):
        for name in ('schema', 'swagger-ui', 'redoc'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
