from django.conf import settings
from rest_framework.permissions import BasePermission


class CanViewAPIDocs(BasePermission):
    """API docs are public when API_DOCS_PUBLIC is on (dev/staging); otherwise staff only."""

    def has_permission(self, request, view):
        return settings.API_DOCS_PUBLIC or bool(request.user and request.user.is_staff)
