import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from coaching_sessions.models import Session

from .models import Notification

logger = logging.getLogger(__name__)

UPCOMING_SESSION_REMINDER_TITLE = 'Upcoming session reminder'


def _get_upcoming_sessions(user, team):
    if not user or not team:
        return Session.objects.none()

    now = timezone.now()
    next_24_hours = now + timedelta(hours=24)

    return Session.objects.filter(
        team=team,
        coach=user,
        status=Session.PLANNED,
        session_date__gte=now,
        session_date__lte=next_24_hours,
    ).select_related('client')


def _build_notification_message(session):
    session_time = timezone.localtime(session.session_date)
    return (
        f'{session.title} with {session.client.name} is scheduled for '
        f'{date_format(session_time, "N j, Y, P")}.'
    )


def _build_email_body(request, session):
    session_time = timezone.localtime(session.session_date)
    session_path = reverse('sessions:detail', args=[session.pk])
    session_url = request.build_absolute_uri(session_path)

    return '\n'.join([
        f'Session title: {session.title}',
        f'Client: {session.client.name}',
        f'Date/time: {date_format(session_time, "N j, Y, P")}',
        f'Duration: {session.duration_minutes} minutes',
        f'Session link: {session_url}',
    ])


def _get_or_create_upcoming_notification(team, user, session):
    message = _build_notification_message(session)
    notification, created = Notification.objects.get_or_create(
        team=team,
        user=user,
        session=session,
        title=UPCOMING_SESSION_REMINDER_TITLE,
        defaults={'message': message},
    )

    if notification.message != message:
        notification.message = message
        notification.save(update_fields=['message'])

    return notification, created


def create_upcoming_session_notifications(user, team):
    created_count = 0

    for session in _get_upcoming_sessions(user, team):
        _, created = _get_or_create_upcoming_notification(team, user, session)

        if created:
            created_count += 1

    return created_count


def send_upcoming_session_email_reminders(request, user, team):
    if not user or not team or not user.email:
        return 0

    sent_count = 0

    for session in _get_upcoming_sessions(user, team):
        notification, _ = _get_or_create_upcoming_notification(team, user, session)

        if notification.email_sent:
            continue

        subject = f'Upcoming session reminder: {session.title}'
        message = _build_email_body(request, session)

        try:
            delivered = send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                'Failed to send upcoming session reminder email for notification %s',
                notification.pk,
            )
            continue

        if delivered:
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=['email_sent', 'email_sent_at'])
            sent_count += 1

    return sent_count


def trigger_upcoming_session_reminders(request, user, team):
    create_upcoming_session_notifications(user, team)
    return send_upcoming_session_email_reminders(request, user, team)
