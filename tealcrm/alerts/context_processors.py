from .models import Notification


def unread_notifications(request):
    unread_notifications_count = 0
    latest_unread_notifications = Notification.objects.none()

    if request.user.is_authenticated:
        userprofile = getattr(request.user, 'userprofile', None)
        active_team = getattr(userprofile, 'active_team', None)

        if active_team:
            unread_notifications = Notification.objects.filter(
                team=active_team,
                user=request.user,
                is_read=False,
            ).select_related('session')
            unread_notifications_count = unread_notifications.count()
            latest_unread_notifications = unread_notifications.order_by('-created_at')[:5]

    return {
        'unread_notifications_count': unread_notifications_count,
        'latest_unread_notifications': latest_unread_notifications,
    }
