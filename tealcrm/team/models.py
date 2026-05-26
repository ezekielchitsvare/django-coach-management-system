    
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    name = models.CharField(max_length=50)
    setup_fee = models.IntegerField()
    monthly_price = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    max_leads = models.IntegerField(null=True, blank=True)
    max_clients = models.IntegerField(null=True, blank=True)
    max_members = models.IntegerField(default=1)
    max_sessions_per_month = models.PositiveIntegerField(null=True, blank=True)
    has_analytics = models.BooleanField(default=False)
    has_team_roles = models.BooleanField(default=False)
    has_email_reminders = models.BooleanField(default=False)
    has_advanced_analytics = models.BooleanField(default=False)
    has_export_tools = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Team(models.Model):
    plan = models.ForeignKey(Plan, related_name='teams', blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='teams', through='TeamMembership')
    created_by = models.ForeignKey(User, related_name='created_teams', on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)

    def get_membership(self, user):
        if not user or not user.is_authenticated:
            return None

        membership = self.memberships.filter(user=user).first()

        if membership:
            return membership

        if self.created_by_id == user.id:
            return TeamMembership(team=self, user=user, role=TeamMembership.ROLE_OWNER)

        return None

    def is_owner(self, user):
        membership = self.get_membership(user)
        return bool(membership and membership.role == TeamMembership.ROLE_OWNER)

    def is_admin(self, user):
        membership = self.get_membership(user)
        return bool(
            membership and membership.role in {TeamMembership.ROLE_OWNER, TeamMembership.ROLE_ADMIN}
        )

    def is_member(self, user):
        return self.get_membership(user) is not None

    def can_manage_team(self, user):
        return self.is_admin(user)

    def can_manage_billing(self, user):
        return self.is_owner(user)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'

    ROLE_CHOICES = (
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
    )

    team = models.ForeignKey(Team, related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='team_memberships', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = 'team_team_members'
        ordering = ('joined_at', 'id')
        constraints = [
            models.UniqueConstraint(fields=('team', 'user'), name='unique_team_membership'),
        ]

    def __str__(self):
        return f'{self.user.username} in {self.team.name} ({self.role})'
