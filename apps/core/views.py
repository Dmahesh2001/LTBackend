from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Liveness/readiness probe for load balancers and uptime monitors."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=['Health'],
        responses=inline_serializer(
            name='HealthCheck',
            fields={
                'status': serializers.CharField(),
                'database': serializers.CharField(),
            },
        ),
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            database = 'ok'
        except Exception:
            database = 'unavailable'

        healthy = database == 'ok'
        return Response(
            {'status': 'ok' if healthy else 'degraded', 'database': database},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
