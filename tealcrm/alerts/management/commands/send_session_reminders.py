from django.core.management.base import BaseCommand

from alerts.services import send_upcoming_session_email_reminders
from team.models import TeamMembership


class Command(BaseCommand):
    help = 'Send upcoming session reminder emails for all team memberships.'

    def handle(self, *args, **options):
        sent_count = 0

        memberships = TeamMembership.objects.select_related('user', 'team')
        for membership in memberships:
            sent_count += send_upcoming_session_email_reminders(
                None,
                membership.user,
                membership.team,
            )

        self.stdout.write(f'Sent {sent_count} session reminder email(s).')
