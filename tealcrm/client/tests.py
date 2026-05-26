import html

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from client.models import Client
from coaching_sessions.models import Session
from team.models import Plan, Team, TeamMembership
from team.plan_limits import PLAN_LIMIT_MESSAGE
from userprofile.models import Userprofile


class ClientPlanEnforcementTests(TestCase):
    def setUp(self):
        username = f'client_owner_{self._testMethodName}'
        self.user = User.objects.create_user(username=username, password='testpass123')
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
        self.business_plan = Plan.objects.create(
            name=f'Business {self._testMethodName}',
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
            name='Client Team',
            created_by=self.user,
            plan=self.starter_plan,
        )
        TeamMembership.objects.create(
            team=self.team,
            user=self.user,
            role=TeamMembership.ROLE_OWNER,
        )
        Userprofile.objects.create(user=self.user, active_team=self.team)

    def test_starter_plan_blocks_creating_more_than_5_clients(self):
        for index in range(5):
            Client.objects.create(
                team=self.team,
                name=f'Client {index}',
                email=f'client{index}@example.com',
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('clients:add'),
            {
                'name': 'Overflow Client',
                'email': 'overflow@example.com',
                'description': 'Blocked by plan',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], reverse('team:plans'))
        self.assertEqual(Client.objects.filter(team=self.team).count(), 5)
        self.assertIn(PLAN_LIMIT_MESSAGE, html.unescape(response.content.decode()))

    def test_export_tools_require_business_plan(self):
        Client.objects.create(
            team=self.team,
            name='Exportable Client',
            email='client@example.com',
            created_by=self.user,
        )
        self.team.plan = self.professional_plan
        self.team.save(update_fields=['plan'])

        self.client.force_login(self.user)
        locked_response = self.client.get(reverse('clients:export'), follow=True)

        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, 'Export tools are available on the Business plan.')

        self.team.plan = self.business_plan
        self.team.save(update_fields=['plan'])

        export_response = self.client.get(reverse('clients:export'))

        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response['Content-Type'], 'text/csv')


class ClientListViewTests(TestCase):
    def setUp(self):
        username = f'client_list_owner_{self._testMethodName}'
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
            name='Primary Client Team',
            created_by=self.user,
            plan=self.plan,
        )
        self.other_team = Team.objects.create(
            name='Secondary Client Team',
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

    def test_clients_list_filters_by_active_team_and_search_and_annotates_sessions(self):
        matching_client = Client.objects.create(
            team=self.team,
            name='Alpha Client',
            email='alpha@example.com',
            created_by=self.user,
        )
        Client.objects.create(
            team=self.team,
            name='Beta Client',
            email='beta@example.com',
            created_by=self.user,
        )
        Client.objects.create(
            team=self.other_team,
            name='Alpha Client',
            email='other-team@example.com',
            created_by=self.other_user,
        )
        Session.objects.create(
            team=self.team,
            client=matching_client,
            coach=self.user,
            title='Kickoff',
            session_date='2026-05-20T10:00:00Z',
            created_by=self.user,
        )
        Session.objects.create(
            team=self.team,
            client=matching_client,
            coach=self.user,
            title='Follow Up',
            session_date='2026-05-21T10:00:00Z',
            created_by=self.user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('clients:list'), {'q': 'Alpha'})

        self.assertEqual(response.status_code, 200)
        clients = list(response.context['clients'])
        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0].pk, matching_client.pk)
        self.assertEqual(clients[0].session_count, 2)

    def test_clients_list_paginates_25_and_orders_newest_first(self):
        for index in range(26):
            Client.objects.create(
                team=self.team,
                name=f'Client {index:02d}',
                email=f'client{index}@example.com',
                created_by=self.user,
            )

        self.client.force_login(self.user)
        response = self.client.get(reverse('clients:list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.per_page, 25)
        self.assertEqual(len(response.context['clients']), 25)
        self.assertEqual(response.context['clients'][0].name, 'Client 25')
