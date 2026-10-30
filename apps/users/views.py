from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserSerializer


@extend_schema(tags=['Auth'])
class RegisterView(generics.CreateAPIView):
    """Create a new user account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Users'])
class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated user's profile."""

    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user
