import html
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from client.models import Client
from coaching_sessions.models import Session
from team.models import Plan, Team, TeamMembership
from team.plan_limits import PLAN_LIMIT_MESSAGE
from userprofile.models import Userprofile


class CoachingSessionPlanEnforcementTests(TestCase):
    def setUp(self):
        username = f'session_owner_{self._testMethodName}'
        self.user = User.objects.create_user(username=username, password='testpass123')
        self.starter_plan = Plan.objects.create(
            name=f'Starter {self._testMethodName}',
            setup_fee=0,
            monthly_price=0,
            max_members=1,
            max_leads=10,
            max_clients=5,
            max_sessions_per_month=10,
            has_analytics=False,
        )
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
        )
        self.team = Team.objects.create(
            name='Session Team',
            created_by=self.user,
            plan=self.starter_plan,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.user, active_team=self.team)
        self.client_record = Client.objects.create(
            team=self.team,
            name='Session Client',
            email='session-client@example.com',
            created_by=self.user,
        )

    def test_starter_plan_blocks_more_than_10_sessions_in_a_month(self):
        session_month = timezone.now().replace(day=15, hour=10, minute=0, second=0, microsecond=0)
        for index in range(10):
            Session.objects.create(
                team=self.team,
                client=self.client_record,
                coach=self.user,
                title=f'Session {index}',
                session_date=session_month + timedelta(days=index % 5),
                status=Session.PLANNED,
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('sessions:add'),
            {
                'client': self.client_record.pk,
                'title': 'Overflow Session',
                'session_date': session_month.strftime('%Y-%m-%dT%H:%M'),
                'duration_minutes': 60,
                'status': Session.PLANNED,
                'notes': 'Blocked by plan',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('team:plans'))
        self.assertEqual(Session.objects.filter(team=self.team).count(), 10)
        self.assertIn(PLAN_LIMIT_MESSAGE, html.unescape(response.content.decode()))

    def test_starter_plan_locks_analytics_and_professional_unlocks_it(self):
        self.client.force_login(self.user)

        locked_response = self.client.get(reverse('sessions:dashboard'))
        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, 'Session analytics are available on Professional and Business plans.')

        self.team.plan = self.professional_plan
        self.team.save(update_fields=['plan'])

        unlocked_response = self.client.get(reverse('sessions:dashboard'))
        self.assertEqual(unlocked_response.status_code, 200)
        self.assertContains(unlocked_response, 'Session Dashboard')
