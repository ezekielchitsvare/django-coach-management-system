from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import get_safe_next_url

from .models import Notification


@login_required
def notifications_list(request):
    team = request.user.userprofile.active_team
    notifications = Notification.objects.filter(
        team=team,
        user=request.user,
    ).select_related('session', 'session__client')

    return render(request, 'notifications/notifications_list.html', {
        'notifications': notifications,
    })


@login_required
@require_POST
def mark_notification_read(request, pk):
    team = request.user.userprofile.active_team
    notification = get_object_or_404(
        Notification,
        pk=pk,
        team=team,
        user=request.user,
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    next_url = get_safe_next_url(request)
    if next_url:
        return redirect(next_url)

    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_notifications_read(request):
    team = request.user.userprofile.active_team
    Notification.objects.filter(
        team=team,
        user=request.user,
        is_read=False,
    ).update(is_read=True)

    next_url = get_safe_next_url(request)
    if next_url:
        return redirect(next_url)

    return redirect('notifications:list')
