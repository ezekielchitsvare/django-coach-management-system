import calendar
from datetime import date, timedelta, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from client.models import Client
from alerts.services import create_upcoming_session_notifications
from core.utils import get_safe_next_url, get_safe_return_url
from team.plan_limits import PLAN_LIMIT_MESSAGE, can_access_analytics, can_add_session
from .models import Session
from .forms import AddSessionForm

@login_required
def session_list(request):
    team = request.user.userprofile.active_team
    create_upcoming_session_notifications(request.user, team)
    sessions = Session.objects.filter(team=team)

    status = request.GET.get('status')
    client_id = request.GET.get('client')
    next_url = get_safe_next_url(request)

    if status:
        sessions = sessions.filter(status=status)

    if client_id:
        sessions = sessions.filter(client_id=client_id)

    return render(request, 'coaching_sessions/session_list.html', {
        'sessions': sessions,
        'current_status': status,
        'current_client_id': client_id,
        'next_url': next_url,
        'can_access_analytics': can_access_analytics(team),
    })

@login_required
def session_add(request):
    team = request.user.userprofile.active_team
    next_url = get_safe_next_url(request)

    form = AddSessionForm(request.POST or None)
    selected_session_date = None
    can_schedule_session = True

    # always filter the client field by active team
    form.fields['client'].queryset = Client.objects.filter(team=team)

    client_id = request.GET.get('client')
    selected_date = request.GET.get('date')

    if client_id:
        form.fields['client'].initial = client_id

    if selected_date and request.method != 'POST':
        form.fields['session_date'].initial = f'{selected_date} 09:00'
        try:
            selected_session_date = date.fromisoformat(selected_date)
        except ValueError:
            selected_session_date = None

    if selected_session_date:
        can_schedule_session = can_add_session(team, selected_session_date)
        if not can_schedule_session:
            messages.error(request, PLAN_LIMIT_MESSAGE)
            return redirect(get_safe_return_url(request, reverse('team:plans')))

    if request.method == 'POST' and form.is_valid():
        session = form.save(commit=False)
        allowed, message = can_add_session(team, session.session_date, include_message=True)
        if not allowed:
            messages.error(request, message)
            return redirect(get_safe_return_url(request, reverse('team:plans')))
        else:
            session.team = team
            session.created_by = request.user
            session.coach = request.user
            session.save()

            messages.success(request, 'Session created successfully.')
            if next_url:
                return redirect(next_url)

            return redirect('sessions:calendar')

    return render(request, 'coaching_sessions/session_form.html', {
        'form': form,
        'can_add_session': can_schedule_session,
        'session_limit_message': PLAN_LIMIT_MESSAGE,
        'next_url': next_url,
    })

@login_required
def session_detail(request, pk):
    team = request.user.userprofile.active_team
    session = get_object_or_404(Session, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    return render(request, 'coaching_sessions/session_detail.html', {
        'session': session,
        'next_url': next_url,
    })


@login_required
def session_edit(request, pk):
    team = request.user.userprofile.active_team
    session = get_object_or_404(Session, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    form = AddSessionForm(request.POST or None, instance=session)
    form.fields['client'].queryset = Client.objects.filter(team=team)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'The session was updated.')
        if next_url:
            return redirect(next_url)

        return redirect('sessions:detail', pk=session.pk)

    return render(request, 'coaching_sessions/session_form.html', {
        'form': form,
        'session': session,
        'next_url': next_url,
    })


@login_required
def session_delete(request, pk):
    team = request.user.userprofile.active_team
    session = get_object_or_404(Session, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    if request.method == 'POST':
        session.delete()
        messages.success(request, 'The session was deleted.')

        if next_url:
            return redirect(next_url)

        return redirect('sessions:list')

    return render(request, 'coaching_sessions/session_confirm_delete.html', {
        'session': session,
        'next_url': next_url,
    })


@login_required
def session_dashboard(request):
    team = request.user.userprofile.active_team
    create_upcoming_session_notifications(request.user, team)
    next_url = get_safe_next_url(request)
    allowed, message = can_access_analytics(team, include_message=True)

    if not allowed:
        return render(request, 'coaching_sessions/session_dashboard_locked.html', {
            'next_url': next_url,
            'analytics_upgrade_message': message,
        })

    sessions = Session.objects.filter(team=team)

    period = request.GET.get('period', 'all')
    today = timezone.localdate()

    if period == '7d':
        start_date = today - timedelta(days=7)
        sessions = sessions.filter(session_date__date__gte=start_date)

    elif period == '30d':
        start_date = today - timedelta(days=30)
        sessions = sessions.filter(session_date__date__gte=start_date)

    elif period == 'month':
        sessions = sessions.filter(
            session_date__year=today.year,
            session_date__month=today.month,
        )

    else:
        period = 'all'

    total_sessions = sessions.count()
    planned_sessions = sessions.filter(status=Session.PLANNED).count()
    completed_sessions = sessions.filter(status=Session.COMPLETED).count()
    cancelled_sessions = sessions.filter(status=Session.CANCELLED).count()

    completion_rate = 0
    if total_sessions > 0:
        completion_rate = round((completed_sessions / total_sessions) * 100)

    

    sessions_this_month = sessions.filter(
        session_date__year=today.year,
        session_date__month=today.month,
    ).count()

    sessions_per_client_qs = (
    sessions
    .values('client__id', 'client__name')
    .annotate(total=Count('id'))
    .order_by('-total', 'client__name')
)
        # --- Previous period comparison ---
    previous_sessions = Session.objects.filter(team=team)

    if period == '7d':
        prev_start = today - timedelta(days=14)
        prev_end = today - timedelta(days=7)
        previous_sessions = previous_sessions.filter(
            session_date__date__gte=prev_start,
            session_date__date__lt=prev_end,
        )

    elif period == '30d':
        prev_start = today - timedelta(days=60)
        prev_end = today - timedelta(days=30)
        previous_sessions = previous_sessions.filter(
            session_date__date__gte=prev_start,
            session_date__date__lt=prev_end,
        )

    elif period == 'month':
        first_day_this_month = today.replace(day=1)
        last_month_end = first_day_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        previous_sessions = previous_sessions.filter(
            session_date__date__gte=last_month_start,
            session_date__date__lte=last_month_end,
        )

    else:
        previous_sessions = Session.objects.none()

    prev_total_sessions = previous_sessions.count()

    sessions_change = None
    if prev_total_sessions > 0:
        sessions_change = round(
            ((total_sessions - prev_total_sessions) / prev_total_sessions) * 100
        )

    # Completion rate comparison
    prev_completed = previous_sessions.filter(status=Session.COMPLETED).count()

    prev_completion_rate = 0
    if prev_total_sessions > 0:
        prev_completion_rate = round((prev_completed / prev_total_sessions) * 100)

    completion_change = None

    if prev_total_sessions > 0:
        completion_change = completion_rate - prev_completion_rate

    max_client_sessions = sessions_per_client_qs[0]['total'] if sessions_per_client_qs else 0

    sessions_per_client = []

    for item in sessions_per_client_qs:
        percentage = 0

        if max_client_sessions > 0:
            percentage = round((item['total'] / max_client_sessions) * 100)

        sessions_per_client.append({
            'client_id': item['client__id'],
            'client_name': item['client__name'],
            'total': item['total'],
            'percentage': percentage,
        })

            # Top client
    top_client = None

    top_client_data = (
        sessions
        .values('client__name')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    if top_client_data:
        top_client = {
            'name': top_client_data['client__name'],
            'total': top_client_data['total'],
        }

        # Most active weekday
    weekday_counts = {}
    most_active_day = None

    for session in sessions:
        weekday = session.session_date.strftime('%A')
        weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1

    if weekday_counts:
        most_active_day = max(weekday_counts, key=weekday_counts.get)

    return render(request, 'coaching_sessions/session_dashboard.html', {
        'total_sessions': total_sessions,
        'planned_sessions': planned_sessions,
        'completed_sessions': completed_sessions,
        'cancelled_sessions': cancelled_sessions,
        'completion_rate': completion_rate,
        'sessions_this_month': sessions_this_month,
        'sessions_per_client': sessions_per_client,
        'max_client_sessions': max_client_sessions,
        'current_period': period,
        'top_client': top_client,
        'most_active_day': most_active_day,
        'next_url': next_url,
        'sessions_change': sessions_change,
        'completion_change': completion_change,
    })


@login_required
def session_calendar(request):
    team = request.user.userprofile.active_team
    create_upcoming_session_notifications(request.user, team)
    next_url = get_safe_next_url(request)
    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        current_month = date(year, month, 1)
    except (TypeError, ValueError):
        current_month = date(today.year, today.month, 1)

    status = request.GET.get('status')
    valid_statuses = {choice[0] for choice in Session.STATUS_CHOICES}
    if status not in valid_statuses:
        status = None

    prev_month = current_month - timedelta(days=1)
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    month_sessions = Session.objects.filter(
        team=team,
        session_date__year=current_month.year,
        session_date__month=current_month.month,
    )

    sessions = month_sessions.select_related('client').order_by('session_date')
    if status:
        sessions = sessions.filter(status=status)

    sessions_by_day = {}
    for session in sessions:
        session_day = session.session_date.date()
        sessions_by_day.setdefault(session_day, []).append(session)

    calendar_weeks = []
    calendar_builder = calendar.Calendar(firstweekday=0)
    for week in calendar_builder.monthdatescalendar(current_month.year, current_month.month):
        week_days = []
        for day in week:
            week_days.append({
                'date': day,
                'is_current_month': day.month == current_month.month,
                'is_today': day == today,
                'sessions': sessions_by_day.get(day, []),
            })
        calendar_weeks.append(week_days)

    status_filters = [
        {'label': 'All', 'value': '', 'count': month_sessions.count()},
        {'label': 'Planned', 'value': Session.PLANNED, 'count': month_sessions.filter(status=Session.PLANNED).count()},
        {'label': 'Completed', 'value': Session.COMPLETED, 'count': month_sessions.filter(status=Session.COMPLETED).count()},
        {'label': 'Cancelled', 'value': Session.CANCELLED, 'count': month_sessions.filter(status=Session.CANCELLED).count()},
    ]

    return render(request, 'coaching_sessions/session_calendar.html', {
        'calendar_weeks': calendar_weeks,
        'month_label': current_month.strftime('%B %Y'),
        'month': current_month.month,
        'year': current_month.year,
        'today': today,
        'today_month': today.month,
        'today_year': today.year,
        'current_status': status,
        'status_filters': status_filters,
        'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'prev_month': prev_month.month,
        'prev_year': prev_month.year,
        'next_month': next_month.month,
        'next_year': next_month.year,
        'next_url': next_url,
        'can_access_analytics': can_access_analytics(team),
    })

@login_required
def session_day(request):
    team = request.user.userprofile.active_team
    next_url = get_safe_next_url(request)

    date_param = request.GET.get('date')

    if date_param:
        selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
    else:
        selected_date = date.today()

    sessions = Session.objects.filter(
        team=team,
        session_date__date=selected_date
    ).order_by('session_date')

    return render(request, 'coaching_sessions/session_day.html', {
        'selected_date': selected_date,
        'sessions': sessions,
        'next_url': next_url,
    })
