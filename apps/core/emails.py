from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_templated_email(*, to, subject, template, context=None):
    """
    Send a multipart (plain text + HTML) email.

    Renders `<template>.txt` and `<template>.html`, e.g. template='waitlist/emails/confirmation'.
    Raises on delivery failure; callers decide whether that should be fatal.
    """
    recipients = [to] if isinstance(to, str) else list(to)
    context = {'subject': subject, **(context or {})}

    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string(f'{template}.txt', context),
        to=recipients,
    )
    message.attach_alternative(render_to_string(f'{template}.html', context), 'text/html')
    return message.send()
