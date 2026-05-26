import html

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from client.models import Client
from lead.models import Lead
from team.models import Plan, Team, TeamMembership
from team.plan_limits import PLAN_LIMIT_MESSAGE
from userprofile.models import Userprofile


class LeadPlanEnforcementTests(TestCase):
    def setUp(self):
        username = f'lead_owner_{self._testMethodName}'
        self.user = User.objects.create_user(username=username, password='testpass123')
        self.starter_plan = Plan.objects.create(
            name=f'Starter {self._testMethodName}',
            setup_fee=0,
            monthly_price=0,
            max_members=1,
            max_leads=10,
            max_clients=5,
            max_sessions_per_month=10,
        )
        self.team = Team.objects.create(
            name='Lead Team',
            created_by=self.user,
            plan=self.starter_plan,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.user, active_team=self.team)

    def test_starter_plan_blocks_creating_more_than_10_leads(self):
        for index in range(10):
            Lead.objects.create(
                team=self.team,
                name=f'Lead {index}',
                email=f'lead{index}@example.com',
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('leads:add'),
            {
                'name': 'Overflow Lead',
                'email': 'overflow@example.com',
                'description': 'Blocked by plan',
                'priority': Lead.MEDIUM,
                'status': Lead.NEW,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('team:plans'))
        self.assertEqual(Lead.objects.filter(team=self.team).count(), 10)
        self.assertIn(PLAN_LIMIT_MESSAGE, html.unescape(response.content.decode()))

    def test_lead_conversion_blocks_when_client_limit_is_reached(self):
        lead = Lead.objects.create(
            team=self.team,
            name='Convertible Lead',
            email='convert@example.com',
            created_by=self.user,
        )
        for index in range(5):
            Client.objects.create(
                team=self.team,
                name=f'Client {index}',
                email=f'client{index}@example.com',
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('leads:convert', args=[lead.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('team:plans'))
        self.assertEqual(Client.objects.filter(team=self.team).count(), 5)
        lead.refresh_from_db()
        self.assertFalse(lead.converted_to_client)
        self.assertIn(PLAN_LIMIT_MESSAGE, html.unescape(response.content.decode()))


class LeadListViewTests(TestCase):
    def setUp(self):
        username = f'lead_list_owner_{self._testMethodName}'
        self.user = User.objects.create_user(username=username, password='testpass123')
        self.other_user = User.objects.create_user(username=f'{username}_other', password='testpass123')
        self.plan = Plan.objects.create(
            name=f'Growth {self._testMethodName}',
            setup_fee=0,
            monthly_price=19,
            max_members=5,
            max_leads=500,
            max_clients=200,
            max_sessions_per_month=None,
        )
        self.team = Team.objects.create(
            name='Primary Lead Team',
            created_by=self.user,
            plan=self.plan,
        )
        self.other_team = Team.objects.create(
            name='Secondary Lead Team',
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

    def test_lead_list_filters_by_active_team_search_status_and_priority(self):
        matching_lead = Lead.objects.create(
            team=self.team,
            name='Alpha Prospect',
            email='alpha@example.com',
            priority=Lead.HIGH,
            status=Lead.CONTACTED,
            created_by=self.user,
        )
        Lead.objects.create(
            team=self.team,
            name='Alpha Lost',
            email='lost@example.com',
            priority=Lead.HIGH,
            status=Lead.LOST,
            created_by=self.user,
        )
        Lead.objects.create(
            team=self.other_team,
            name='Alpha Prospect',
            email='other-team@example.com',
            priority=Lead.HIGH,
            status=Lead.CONTACTED,
            created_by=self.other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('leads:list'), {
            'q': 'Alpha',
            'status': Lead.CONTACTED,
            'priority': Lead.HIGH,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['leads']), [matching_lead])

    def test_lead_list_paginates_25_and_orders_newest_first(self):
        for index in range(26):
            Lead.objects.create(
                team=self.team,
                name=f'Lead {index:02d}',
                email=f'lead{index}@example.com',
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.get(reverse('leads:list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.per_page, 25)
        self.assertEqual(len(response.context['leads']), 25)
        self.assertEqual(response.context['leads'][0].name, 'Lead 25')
