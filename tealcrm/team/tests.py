import html

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from team.models import Plan, Team, TeamMembership
from team.plan_limits import (
    PLAN_LIMIT_MESSAGE,
    TEAM_ROLES_MESSAGE,
    can_access_analytics,
    can_use_email_reminders,
    can_use_export_tools,
    can_use_team_roles,
    get_team_plan,
)
from userprofile.models import Userprofile


class TeamPlanEnforcementTests(TestCase):
    def setUp(self):
        username = f'owner_{self._testMethodName}'
        self.owner = User.objects.create_user(username=username, password='testpass123')
        self.starter_team = Team.objects.create(name='Starter Team', created_by=self.owner)
        TeamMembership.objects.create(
            team=self.starter_team,
            user=self.owner,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.owner, active_team=self.starter_team)

        self.professional_plan = Plan.objects.create(
            name='Professional',
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
        self.business_plan = Plan.objects.create(
            name='Business',
            setup_fee=0,
            monthly_price=49,
            max_members=15,
            max_leads=None,
            max_clients=None,
            max_sessions_per_month=None,
            has_analytics=True,
            has_team_roles=True,
            has_email_reminders=True,
            has_advanced_analytics=True,
            has_export_tools=True,
        )

    def test_team_without_plan_uses_starter_fallback(self):
        starter_plan = get_team_plan(self.starter_team)

        self.assertEqual(starter_plan.name, 'Starter')
        self.assertEqual(starter_plan.max_members, 1)
        self.assertEqual(starter_plan.max_leads, 10)
        self.assertEqual(starter_plan.max_clients, 5)
        self.assertEqual(starter_plan.max_sessions_per_month, 10)
        self.assertFalse(can_access_analytics(self.starter_team))
        self.assertFalse(can_use_email_reminders(self.starter_team))
        self.assertFalse(can_use_team_roles(self.starter_team))
        self.assertFalse(can_use_export_tools(self.starter_team))

    def test_professional_and_business_features_match_plan_flags(self):
        self.starter_team.plan = self.professional_plan
        self.starter_team.save(update_fields=['plan'])

        self.assertTrue(can_access_analytics(self.starter_team))
        self.assertTrue(can_use_email_reminders(self.starter_team))
        self.assertTrue(can_use_team_roles(self.starter_team))
        self.assertFalse(can_use_export_tools(self.starter_team))

        self.starter_team.plan = self.business_plan
        self.starter_team.save(update_fields=['plan'])

        self.assertTrue(can_access_analytics(self.starter_team))
        self.assertTrue(can_use_email_reminders(self.starter_team))
        self.assertTrue(can_use_team_roles(self.starter_team))
        self.assertTrue(can_use_export_tools(self.starter_team))

    def test_owner_cannot_add_members_past_starter_limit(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('team:add_member', args=[self.starter_team.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('team:plans'))
        self.assertIn(PLAN_LIMIT_MESSAGE, html.unescape(response.content.decode()))

    def test_promote_controls_are_blocked_without_team_roles(self):
        teammate = User.objects.create_user(
            username=f'promotee_{self._testMethodName}',
            password='testpass123',
        )
        TeamMembership.objects.create(
            team=self.starter_team,
            user=teammate,
            role=TeamMembership.ROLE_MEMBER,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('team:promote_member', args=[self.starter_team.pk, teammate.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, TEAM_ROLES_MESSAGE)
        membership = TeamMembership.objects.get(team=self.starter_team, user=teammate)
        self.assertEqual(membership.role, TeamMembership.ROLE_MEMBER)
