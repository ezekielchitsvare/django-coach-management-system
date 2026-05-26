from django.db import models

from django.contrib.auth.models import User

from team.models import Team
from client.models import Client


class Session(models.Model):
    PLANNED = 'planned'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = (
        (PLANNED, 'Planned'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    )

    team = models.ForeignKey(Team, related_name='sessions', on_delete=models.CASCADE)
    client = models.ForeignKey(Client, related_name='sessions', on_delete=models.CASCADE)
    coach = models.ForeignKey(User, related_name='coaching_sessions', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    session_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PLANNED)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, related_name='created_sessions', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-session_date',)

    def __str__(self):
        return f"{self.client.name} - {self.title}"
