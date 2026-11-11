import logging

from django.utils import timezone

from apps.core.emails import send_templated_email

logger = logging.getLogger(__name__)


def send_waitlist_confirmation(entry):
    """Email the user that they're on the waitlist. Returns True if it was sent."""
    try:
        send_templated_email(
            to=entry.email,
            subject="You're on the Love and Tails waitlist",
            template='waitlist/emails/confirmation',
        )
    except Exception:
        logger.exception('Failed to send waitlist confirmation for entry %s', entry.pk)
        return False

    entry.confirmation_sent_at = timezone.now()
    entry.save(update_fields=['confirmation_sent_at'])
    return True
