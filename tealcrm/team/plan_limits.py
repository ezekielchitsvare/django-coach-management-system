from client.models import Client
from coaching_sessions.models import Session
from django.utils import timezone
from lead.models import Lead

from .models import Plan, TeamMembership

STARTER_PLAN_DEFAULTS = {
    'name': 'Starter',
    'setup_fee': 0,
    'monthly_price': 0,
    'description': 'A lightweight plan for getting started with Teal CRM.',
    'max_members': 1,
    'max_leads': 10,
    'max_clients': 5,
    'max_sessions_per_month': 10,
    'has_analytics': False,
    'has_team_roles': False,
    'has_email_reminders': False,
    'has_advanced_analytics': False,
    'has_export_tools': False,
}

PLAN_ORDER = ('Starter', 'Professional', 'Business')

PLAN_LIMIT_MESSAGE = "You've reached your plan limit. Upgrade your plan to continue."
LEAD_LIMIT_MESSAGE = PLAN_LIMIT_MESSAGE
CLIENT_LIMIT_MESSAGE = PLAN_LIMIT_MESSAGE
MEMBER_LIMIT_MESSAGE = PLAN_LIMIT_MESSAGE
SESSION_LIMIT_MESSAGE = PLAN_LIMIT_MESSAGE
ANALYTICS_MESSAGE = 'Session analytics are available on Professional and Business plans.'
EMAIL_REMINDERS_MESSAGE = 'Email reminders are available on Professional and Business plans.'
TEAM_ROLES_MESSAGE = 'Advanced team roles are available on Professional and Business plans.'
ADVANCED_ANALYTICS_MESSAGE = 'Advanced analytics are available on the Business plan.'
EXPORT_TOOLS_MESSAGE = 'Export tools are available on the Business plan.'


def _starter_plan():
    return Plan(**STARTER_PLAN_DEFAULTS)


def get_team_plan(team):
    if team and getattr(team, 'plan', None):
        return team.plan

    return _starter_plan()


def get_plan_name(plan):
    if not plan:
        return STARTER_PLAN_DEFAULTS['name']

    return plan.name or STARTER_PLAN_DEFAULTS['name']


def format_limit(max_limit):
    if max_limit in (None, ''):
        return 'Unlimited'

    return str(max_limit)


def limit_reached(current_count, max_limit):
    return max_limit not in (None, '') and current_count >= max_limit


def _response(allowed, message, include_message):
    if include_message:
        return allowed, None if allowed else message

    return allowed


def can_add_lead(team, include_message=False):
    if not team:
        return _response(False, LEAD_LIMIT_MESSAGE, include_message)

    plan = get_team_plan(team)
    current_count = Lead.objects.filter(team=team).count()
    allowed = not limit_reached(current_count, plan.max_leads)
    return _response(allowed, LEAD_LIMIT_MESSAGE, include_message)


def can_add_client(team, include_message=False):
    if not team:
        return _response(False, CLIENT_LIMIT_MESSAGE, include_message)

    plan = get_team_plan(team)
    current_count = Client.objects.filter(team=team).count()
    allowed = not limit_reached(current_count, plan.max_clients)
    return _response(allowed, CLIENT_LIMIT_MESSAGE, include_message)


def can_add_member(team, include_message=False):
    if not team:
        return _response(False, MEMBER_LIMIT_MESSAGE, include_message)

    plan = get_team_plan(team)
    current_count = TeamMembership.objects.filter(team=team).count()
    allowed = not limit_reached(current_count, plan.max_members)
    return _response(allowed, MEMBER_LIMIT_MESSAGE, include_message)


def can_add_session(team, session_date=None, include_message=False):
    if not team:
        return _response(False, SESSION_LIMIT_MESSAGE, include_message)

    plan = get_team_plan(team)

    if session_date:
        year = session_date.year
        month = session_date.month
    else:
        today = timezone.localdate()
        year = today.year
        month = today.month

    current_count = Session.objects.filter(
        team=team,
        session_date__year=year,
        session_date__month=month,
    ).count()
    allowed = not limit_reached(current_count, plan.max_sessions_per_month)
    return _response(allowed, SESSION_LIMIT_MESSAGE, include_message)


def can_access_analytics(team, include_message=False):
    allowed = bool(team and get_team_plan(team).has_analytics)
    return _response(allowed, ANALYTICS_MESSAGE, include_message)


def can_use_email_reminders(team, include_message=False):
    allowed = bool(team and get_team_plan(team).has_email_reminders)
    return _response(allowed, EMAIL_REMINDERS_MESSAGE, include_message)


def can_use_team_roles(team, include_message=False):
    allowed = bool(team and get_team_plan(team).has_team_roles)
    return _response(allowed, TEAM_ROLES_MESSAGE, include_message)


def can_use_advanced_analytics(team, include_message=False):
    allowed = bool(team and get_team_plan(team).has_advanced_analytics)
    return _response(allowed, ADVANCED_ANALYTICS_MESSAGE, include_message)


def can_use_export_tools(team, include_message=False):
    allowed = bool(team and get_team_plan(team).has_export_tools)
    return _response(allowed, EXPORT_TOOLS_MESSAGE, include_message)


def _plan_sort_key(plan):
    plan_name = get_plan_name(plan)
    try:
        return (PLAN_ORDER.index(plan_name), plan.monthly_price, plan_name.lower())
    except ValueError:
        return (len(PLAN_ORDER), plan.monthly_price, plan_name.lower())


def _plan_matches_current(plan, current_plan):
    if not current_plan:
        return False

    if plan.pk and current_plan.pk:
        return plan.pk == current_plan.pk

    return get_plan_name(plan).lower() == get_plan_name(current_plan).lower()


def get_plan_rows(plans, current_plan=None):
    rows = []

    for plan in sorted(plans, key=_plan_sort_key):
        rows.append({
            'plan': plan,
            'is_current': _plan_matches_current(plan, current_plan),
            'is_most_popular': get_plan_name(plan) == 'Professional',
            'limits': [
                {'label': 'Members', 'value': format_limit(plan.max_members)},
                {'label': 'Leads', 'value': format_limit(plan.max_leads)},
                {'label': 'Clients', 'value': format_limit(plan.max_clients)},
                {
                    'label': 'Sessions/month',
                    'value': format_limit(getattr(plan, 'max_sessions_per_month', None)),
                },
            ],
            'features': [
                {'label': 'Analytics', 'enabled': bool(getattr(plan, 'has_analytics', False))},
                {'label': 'Email reminders', 'enabled': bool(getattr(plan, 'has_email_reminders', False))},
                {'label': 'Team roles', 'enabled': bool(getattr(plan, 'has_team_roles', False))},
                {
                    'label': 'Advanced analytics',
                    'enabled': bool(getattr(plan, 'has_advanced_analytics', False)),
                },
                {'label': 'Export tools', 'enabled': bool(getattr(plan, 'has_export_tools', False))},
            ],
        })

    return rows
