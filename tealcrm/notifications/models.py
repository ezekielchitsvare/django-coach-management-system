from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from coaching_sessions.models import Session
from team.models import Team


class Notification(models.Model):
    team = models.ForeignKey(Team, related_name='notifications', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    session = models.ForeignKey(
        Session,
        related_name='notifications',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('team', 'user', 'session', 'title'),
                condition=Q(session__isnull=False),
                name='unique_session_notification_per_user_title',
            ),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.title}'
