from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import LoginView, MeView, RegisterView

auth_tag = extend_schema_view(post=extend_schema(tags=['Auth']))

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/token/', LoginView.as_view(), name='token-obtain-pair'),
    path('auth/token/refresh/', auth_tag(TokenRefreshView).as_view(), name='token-refresh'),
    path('auth/token/verify/', auth_tag(TokenVerifyView).as_view(), name='token-verify'),
    path('auth/logout/', auth_tag(TokenBlacklistView).as_view(), name='auth-logout'),
    path('users/me/', MeView.as_view(), name='users-me'),
]
