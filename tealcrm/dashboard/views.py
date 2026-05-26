from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from alerts.services import create_upcoming_session_notifications
from client.models import Client
from coaching_sessions.models import Session
from lead.models import Lead
from team.models import TeamMembership
from team.plan_limits import get_team_plan


def _build_usage_item(label, used, max_limit):
    is_unlimited = max_limit is None

    if is_unlimited:
        percentage = 100
    elif max_limit <= 0:
        percentage = 100 if used > 0 else 0
    else:
        percentage = min(round((used / max_limit) * 100), 100)

    is_limit_reached = not is_unlimited and used >= max_limit
    is_warning = not is_unlimited and percentage >= 80

    return {
        'label': label,
        'used': used,
        'max_limit': max_limit,
        'limit_display': 'Unlimited' if is_unlimited else max_limit,
        'percentage': percentage,
        'is_unlimited': is_unlimited,
        'is_warning': is_warning,
        'is_limit_reached': is_limit_reached,
    }


@login_required
def dashboard(request):
    team = getattr(getattr(request.user, 'userprofile', None), 'active_team', None)

    if not team:
        return render(request, 'dashboard/dashboard.html', {
            'team': None,
        })

    create_upcoming_session_notifications(request.user, team)

    plan = get_team_plan(team)
    now = timezone.now()
    today = timezone.localdate()

    leads_queryset = Lead.objects.filter(team=team, converted_to_client=False)
    clients_queryset = Client.objects.filter(team=team)
    sessions_queryset = Session.objects.filter(team=team)
    sessions_this_month_queryset = sessions_queryset.filter(
        session_date__year=today.year,
        session_date__month=today.month,
    )

    total_leads = leads_queryset.count()
    total_clients = clients_queryset.count()
    total_sessions = sessions_queryset.count()
    sessions_this_month = sessions_this_month_queryset.count()
    completed_sessions_this_month = sessions_this_month_queryset.filter(
        status=Session.COMPLETED,
    ).count()

    recent_leads = leads_queryset.order_by('-created_at')[:5]
    recent_clients = clients_queryset.order_by('-created_at')[:5]
    upcoming_sessions = sessions_queryset.filter(
        status=Session.PLANNED,
        session_date__gte=now,
    ).select_related('client', 'coach').order_by('session_date')[:5]

    members_used = TeamMembership.objects.filter(team=team).count()

    usage_items = [
        _build_usage_item('Members', members_used, plan.max_members),
        _build_usage_item('Leads', total_leads, plan.max_leads),
        _build_usage_item('Clients', total_clients, plan.max_clients),
        _build_usage_item(
            'Sessions this month',
            sessions_this_month,
            plan.max_sessions_per_month,
        ),
    ]

    usage_warning = any(item['is_warning'] for item in usage_items)
    usage_limit_reached = any(item['is_limit_reached'] for item in usage_items)

    return render(request, 'dashboard/dashboard.html', {
        'team': team,
        'plan': plan,
        'can_manage_billing': team.can_manage_billing(request.user),
        'welcome_name': request.user.first_name or request.user.username,
        'total_leads': total_leads,
        'total_clients': total_clients,
        'total_sessions': total_sessions,
        'sessions_this_month': sessions_this_month,
        'completed_sessions_this_month': completed_sessions_this_month,
        'upcoming_sessions': upcoming_sessions,
        'recent_leads': recent_leads,
        'recent_clients': recent_clients,
        'usage_items': usage_items,
        'usage_warning': usage_warning,
        'usage_limit_reached': usage_limit_reached,
    })
