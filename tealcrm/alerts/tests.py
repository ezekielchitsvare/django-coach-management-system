from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from alerts.models import Notification
from alerts.services import send_upcoming_session_email_reminders
from client.models import Client
from coaching_sessions.models import Session
from team.models import Plan, Team, TeamMembership
from userprofile.models import Userprofile


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='https://app.tealcrm.test',
)
class SessionReminderTests(TestCase):
    def setUp(self):
        username = f'coach_{self._testMethodName}'
        self.professional_plan = Plan.objects.create(
            name=f'Professional {self._testMethodName}',
            setup_fee=0,
            monthly_price=19,
            max_members=5,
            max_leads=500,
            max_clients=200,
            max_sessions_per_month=None,
            has_analytics=True,
            has_team_roles=True,
            has_email_reminders=True,
            has_advanced_analytics=False,
            has_export_tools=False,
        )
        self.starter_plan = Plan.objects.create(
            name=f'Starter {self._testMethodName}',
            setup_fee=0,
            monthly_price=0,
            max_members=1,
            max_leads=10,
            max_clients=5,
            max_sessions_per_month=10,
            has_analytics=False,
            has_team_roles=False,
            has_email_reminders=False,
            has_advanced_analytics=False,
            has_export_tools=False,
        )
        self.user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123',
        )
        self.team = Team.objects.create(
            name='Teal CRM',
            created_by=self.user,
            plan=self.professional_plan,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.user, active_team=self.team)
        self.client_record = Client.objects.create(
            team=self.team,
            name='Acme Client',
            created_by=self.user,
        )
        self.session = Session.objects.create(
            team=self.team,
            client=self.client_record,
            coach=self.user,
            title='Discovery Call',
            session_date=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            status=Session.PLANNED,
            created_by=self.user,
        )

    def test_session_pages_create_in_app_notifications_without_sending_email(self):
        self.client.force_login(self.user)

        for url in (
            reverse('sessions:list'),
            reverse('sessions:dashboard'),
            reverse('sessions:calendar'),
            reverse('dashboard:index'),
        ):
            Notification.objects.all().delete()
            mail.outbox.clear()

            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            notification = Notification.objects.get(session=self.session, user=self.user)
            self.assertFalse(notification.email_sent)
            self.assertEqual(len(mail.outbox), 0)

    def test_email_reminders_use_site_url_and_mark_notification_sent(self):
        sent_count = send_upcoming_session_email_reminders(None, self.user, self.team)

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)

        notification = Notification.objects.get(session=self.session, user=self.user)
        self.assertTrue(notification.email_sent)
        self.assertIsNotNone(notification.email_sent_at)
        self.assertIn('https://app.tealcrm.test', mail.outbox[0].body)
        self.assertIn(reverse('sessions:detail', args=[self.session.pk]), mail.outbox[0].body)

    def test_management_command_sends_once_then_skips_duplicates(self):
        first_stdout = StringIO()
        second_stdout = StringIO()

        call_command('send_session_reminders', stdout=first_stdout)
        call_command('send_session_reminders', stdout=second_stdout)

        self.assertIn('Sent 1 session reminder email(s).', first_stdout.getvalue())
        self.assertIn('Sent 0 session reminder email(s).', second_stdout.getvalue())
        self.assertEqual(len(mail.outbox), 1)

    def test_email_reminders_are_disabled_when_plan_feature_is_off(self):
        self.team.plan = self.starter_plan
        self.team.save(update_fields=['plan'])

        sent_count = send_upcoming_session_email_reminders(None, self.user, self.team)

        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)
