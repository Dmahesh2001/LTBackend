from rest_framework import serializers


class WaitlistSignupSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return value.strip().lower()


class WaitlistSignupResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    detail = serializers.CharField()
