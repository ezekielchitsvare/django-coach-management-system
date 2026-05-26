from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from client.models import Client
from coaching_sessions.models import Session
from lead.models import Lead
from team.models import Plan, Team, TeamMembership
from userprofile.models import Userprofile


class DashboardViewTests(TestCase):
    def setUp(self):
        username = f'dashboard_owner_{self._testMethodName}'
        self.user = User.objects.create_user(username=username, password='testpass123')
        self.other_user = User.objects.create_user(username=f'{username}_other', password='testpass123')
        self.plan = Plan.objects.create(
            name=f'Professional {self._testMethodName}',
            setup_fee=0,
            monthly_price=19,
            max_members=5,
            max_leads=10,
            max_clients=10,
            max_sessions_per_month=10,
            has_analytics=True,
            has_team_roles=True,
            has_email_reminders=True,
        )
        self.team = Team.objects.create(
            name='Active Team',
            created_by=self.user,
            plan=self.plan,
        )
        self.other_team = Team.objects.create(
            name='Other Team',
            created_by=self.other_user,
            plan=self.plan,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.ROLE_OWNER,
        )
        TeamMembership.objects.create(
            team=self.other_team,
            user=self.other_user,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.user, active_team=self.team)
        Userprofile.objects.create(user=self.other_user, active_team=self.other_team)

    def test_dashboard_handles_missing_active_team(self):
        self.user.userprofile.active_team = None
        self.user.userprofile.save(update_fields=['active_team'])

        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select or create a team to get started.')

    def test_dashboard_scopes_activity_and_usage_to_active_team(self):
        now = timezone.now()
        current_client = Client.objects.create(
            team=self.team,
            name='Current Client',
            email='current@example.com',
            created_by=self.user,
        )
        other_client = Client.objects.create(
            team=self.other_team,
            name='Other Client',
            email='other@example.com',
            created_by=self.other_user,
        )
        Lead.objects.create(
            team=self.team,
            name='Current Lead',
            email='lead@example.com',
            priority=Lead.HIGH,
            status=Lead.NEW,
            created_by=self.user,
        )
        Lead.objects.create(
            team=self.other_team,
            name='Other Lead',
            email='otherlead@example.com',
            created_by=self.other_user,
        )
        Session.objects.create(
            team=self.team,
            client=current_client,
            coach=self.user,
            title='Discovery Call',
            session_date=now + timedelta(days=1),
            status=Session.PLANNED,
            created_by=self.user,
        )
        Session.objects.create(
            team=self.team,
            client=current_client,
            coach=self.user,
            title='Completed Session',
            session_date=now,
            status=Session.COMPLETED,
            created_by=self.user,
        )
        Session.objects.create(
            team=self.other_team,
            client=other_client,
            coach=self.other_user,
            title='Other Team Session',
            session_date=now + timedelta(days=2),
            status=Session.PLANNED,
            created_by=self.other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_leads'], 1)
        self.assertEqual(response.context['total_clients'], 1)
        self.assertEqual(response.context['total_sessions'], 2)
        self.assertEqual(response.context['sessions_this_month'], 2)
        self.assertEqual(response.context['completed_sessions_this_month'], 1)
        self.assertEqual(response.context['recent_leads'][0].name, 'Current Lead')
        self.assertEqual(response.context['recent_clients'][0].name, 'Current Client')
        self.assertEqual(response.context['upcoming_sessions'][0].title, 'Discovery Call')
