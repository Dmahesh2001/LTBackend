from django.db import models


class WaitlistEntry(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmation_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the waitlist confirmation email was last sent. Empty if sending failed.',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'waitlist entries'

    def __str__(self):
        return self.email
