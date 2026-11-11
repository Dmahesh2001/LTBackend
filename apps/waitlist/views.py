from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttling import ScopedRateThrottle

from .emails import send_waitlist_confirmation
from .models import WaitlistEntry
from .serializers import WaitlistSignupResponseSerializer, WaitlistSignupSerializer


class WaitlistSignupView(APIView):
    """
    Join the waitlist.

    New signups receive a confirmation email (when email sending is enabled).
    Submitting an email that is already on the waitlist succeeds without sending another email.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'waitlist'

    @extend_schema(
        tags=['Waitlist'],
        request=WaitlistSignupSerializer,
        responses={
            201: OpenApiResponse(WaitlistSignupResponseSerializer, description='Added to the waitlist.'),
            200: OpenApiResponse(WaitlistSignupResponseSerializer, description='Already on the waitlist.'),
            400: OpenApiResponse(description='Invalid email address.'),
            429: OpenApiResponse(description='Too many requests from this IP.'),
        },
    )
    def post(self, request):
        serializer = WaitlistSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry, created = WaitlistEntry.objects.get_or_create(email=serializer.validated_data['email'])
        if not created:
            return Response(
                {'email': entry.email, 'detail': "You're already on the waitlist."},
                status=status.HTTP_200_OK,
            )

        sent = settings.WAITLIST_CONFIRMATION_EMAILS and send_waitlist_confirmation(entry)
        detail = "You're on the waitlist! Check your inbox for a confirmation." if sent else "You're on the waitlist!"
        return Response({'email': entry.email, 'detail': detail}, status=status.HTTP_201_CREATED)
