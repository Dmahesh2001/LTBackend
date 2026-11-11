import logging

from redis.exceptions import RedisError
from rest_framework import throttling

logger = logging.getLogger(__name__)


class FailOpenMixin:
    """
    Rate limits are stored in Redis. If Redis is unreachable, allow the request (and log)
    rather than failing with a 500.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except RedisError:
            logger.exception('Rate limit check failed; allowing request')
            return True


class AnonRateThrottle(FailOpenMixin, throttling.AnonRateThrottle):
    pass


class UserRateThrottle(FailOpenMixin, throttling.UserRateThrottle):
    pass


class ScopedRateThrottle(FailOpenMixin, throttling.ScopedRateThrottle):
    pass
