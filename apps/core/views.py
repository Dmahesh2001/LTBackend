from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    """
    Liveness probe for the hosting platform's health checks, which run every few seconds.

    Checks only that the app is up. It deliberately skips the database and Redis so frequent
    checks don't keep Neon awake or use up the Redis command quota.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        tags=['Health'],
        responses=inline_serializer(name='Liveness', fields={'status': serializers.CharField()}),
    )
    def get(self, request):
        return Response({'status': 'ok'})


class HealthCheckView(APIView):
    """
    Full health check (database and Redis) for uptime monitors and humans.

    Returns 503 only when the database is down. A cache (Redis) outage is reported as
    "degraded" with 200, since the app keeps working without it (rate limits fail open).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    # Load balancers poll this every few seconds from one IP; never rate limit it.
    throttle_classes = []

    @extend_schema(
        tags=['Health'],
        responses=inline_serializer(
            name='HealthCheck',
            fields={
                'status': serializers.CharField(),
                'database': serializers.CharField(),
                'cache': serializers.CharField(),
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

        try:
            cache.set('health-check', 'ok', timeout=10)
            cache_status = 'ok' if cache.get('health-check') == 'ok' else 'unavailable'
        except Exception:
            cache_status = 'unavailable'

        healthy = database == 'ok' and cache_status == 'ok'
        return Response(
            {'status': 'ok' if healthy else 'degraded', 'database': database, 'cache': cache_status},
            status=status.HTTP_503_SERVICE_UNAVAILABLE if database != 'ok' else status.HTTP_200_OK,
        )
