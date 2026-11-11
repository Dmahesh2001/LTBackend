from django.conf import settings
from django.contrib import admin, messages

from .emails import send_waitlist_confirmation
from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at', 'confirmation_sent_at']
    list_filter = [('confirmation_sent_at', admin.EmptyFieldListFilter)]
    search_fields = ['email']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'confirmation_sent_at']
    actions = ['resend_confirmation']

    @admin.action(description='Send waitlist confirmation email')
    def resend_confirmation(self, request, queryset):
        if not settings.WAITLIST_CONFIRMATION_EMAILS:
            self.message_user(
                request,
                'Email sending is off. Configure an email provider (EMAIL_HOST) first.',
                messages.ERROR,
            )
            return
        sent = sum(send_waitlist_confirmation(entry) for entry in queryset)
        failed = queryset.count() - sent
        if sent:
            self.message_user(request, f'Sent {sent} confirmation email(s).', messages.SUCCESS)
        if failed:
            self.message_user(request, f'{failed} email(s) failed to send. Check the logs.', messages.ERROR)
