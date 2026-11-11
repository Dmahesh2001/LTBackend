from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.throttling import ScopedRateThrottle

from .serializers import RegisterSerializer, UserSerializer


@extend_schema(tags=['Auth'])
class RegisterView(generics.CreateAPIView):
    """Create a new user account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'


@extend_schema(tags=['Auth'])
class LoginView(TokenObtainPairView):
    """Log in with email and password. Returns an access and a refresh token."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


@extend_schema(tags=['Users'])
class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated user's profile."""

    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user
