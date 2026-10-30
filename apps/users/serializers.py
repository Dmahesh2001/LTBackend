from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'date_joined']
        read_only_fields = ['id', 'email', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

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
