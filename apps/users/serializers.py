from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt import serializers as jwt_serializers
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'date_joined']
        read_only_fields = ['id', 'email', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'phone_number']
        read_only_fields = ['id']

    def validate(self, attrs):
        user = User(**{k: v for k, v in attrs.items() if k != 'password'})
        try:
            password_validation.validate_password(attrs['password'], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    """
    SimpleJWT's refresh, plus two checks it lacks:
    - a refresh token for a deleted user returns 401 (SimpleJWT raises DoesNotExist, a 500)
    - a refresh token issued before a password change is rejected
    """

    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])
        user = User.objects.filter(
            **{jwt_settings.USER_ID_FIELD: refresh.payload.get(jwt_settings.USER_ID_CLAIM)}
        ).first()
        password_changed = jwt_settings.CHECK_REVOKE_TOKEN and refresh.payload.get(
            jwt_settings.REVOKE_TOKEN_CLAIM
        ) != get_md5_hash_password(user.password if user else '')
        if user is None or password_changed:
            raise AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        return super().validate(attrs)
