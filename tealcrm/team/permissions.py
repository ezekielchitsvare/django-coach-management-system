from django.contrib import messages
from django.shortcuts import redirect


def get_user_membership(user, team):
    if not user or not team:
        return None

    return team.memberships.filter(user=user).first()


def is_team_owner(user, team):
    membership = get_user_membership(user, team)
    return membership and membership.role == 'owner'


def is_team_admin(user, team):
    membership = get_user_membership(user, team)
    return membership and membership.role == 'admin'


def can_manage_team(user, team):
    membership = get_user_membership(user, team)
    return membership and membership.role in ['owner', 'admin']


def can_manage_billing(user, team):
    membership = get_user_membership(user, team)
    return membership and membership.role == 'owner'


def deny_with_message(request, message='You do not have permission to do that.'):
    messages.error(request, message)
    return redirect('team:list')