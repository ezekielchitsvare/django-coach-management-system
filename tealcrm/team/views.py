from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.utils import get_safe_return_url

from .forms import AddTeamMemberForm, TeamForm
from .models import Plan, Team, TeamMembership
from .plan_limits import (
    TEAM_ROLES_MESSAGE,
    can_add_member,
    can_use_team_roles,
    get_plan_rows,
    get_team_plan,
)



def _team_queryset_for_user(user):
    return Team.objects.filter(memberships__user=user).select_related('created_by', 'plan').distinct()


def _permission_denied_redirect(request, fallback_url):
    referer = request.META.get('HTTP_REFERER')

    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        messages.error(request, "You don't have permission to do that.")
        return redirect(referer)

    messages.error(request, "You don't have permission to do that.")
    return redirect(fallback_url)


def _get_scoped_active_team(request, pk):
    active_team = getattr(getattr(request.user, 'userprofile', None), 'active_team', None)

    if not active_team or active_team.pk != pk or not active_team.is_member(request.user):
        return None

    return (
        Team.objects.select_related('created_by', 'plan')
        .prefetch_related('memberships__user')
        .get(pk=active_team.pk)
    )


def _can_manage_members(team, user):
    if not team or not user or not team.is_member(user):
        return False

    if can_use_team_roles(team):
        return team.can_manage_team(user)

    return team.can_manage_billing(user)


def _can_manage_role_controls(team, user):
    return bool(team and can_use_team_roles(team) and team.can_manage_billing(user))


def _get_member_rows(team, acting_user, allow_actions=True):
    role_priority = {
        TeamMembership.ROLE_OWNER: 0,
        TeamMembership.ROLE_ADMIN: 1,
        TeamMembership.ROLE_MEMBER: 2,
    }

    memberships = list(team.memberships.select_related('user'))
    memberships.sort(key=lambda membership: (
        role_priority.get(membership.role, 99),
        membership.user.username.lower(),
    ))

    acting_is_owner = allow_actions and team.is_owner(acting_user)
    acting_can_manage_members = allow_actions and _can_manage_members(team, acting_user)
    acting_can_manage_roles = allow_actions and _can_manage_role_controls(team, acting_user)
    acting_is_admin_only = (
        acting_can_manage_members
        and can_use_team_roles(team)
        and team.is_admin(acting_user)
        and not acting_is_owner
    )

    rows = []
    for membership in memberships:
        can_promote = (
            acting_can_manage_roles
            and membership.role == TeamMembership.ROLE_MEMBER
            and membership.user_id != acting_user.id
        )
        can_demote = (
            acting_can_manage_roles
            and membership.role == TeamMembership.ROLE_ADMIN
            and membership.user_id != acting_user.id
        )
        can_remove = False

        if membership.role != TeamMembership.ROLE_OWNER and membership.user_id != acting_user.id:
            if acting_can_manage_members and acting_is_owner:
                can_remove = True
            elif acting_is_admin_only and membership.role == TeamMembership.ROLE_MEMBER:
                can_remove = True

        rows.append({
            'membership': membership,
            'can_promote': can_promote,
            'can_demote': can_demote,
            'can_remove': can_remove,
        })

    return rows


def _sync_removed_users_active_team(user, removed_team):
    userprofile = getattr(user, 'userprofile', None)

    if userprofile and userprofile.active_team_id == removed_team.id:
        userprofile.active_team = user.teams.exclude(pk=removed_team.pk).first()
        userprofile.save(update_fields=['active_team'])


@login_required
def add_team_member(request, pk):
    team = _get_scoped_active_team(request, pk)
    if not team:
        return _permission_denied_redirect(request, 'team:list')

    if not _can_manage_members(team, request.user):
        return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    allowed, message = can_add_member(team, include_message=True)
    if not allowed:
        messages.error(request, message)
        return redirect(get_safe_return_url(request, reverse('team:plans')))

    if request.method == 'POST':
        form = AddTeamMemberForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return redirect('team:detail', pk=pk)

            if team.memberships.filter(user=user).exists():
                messages.error(request, 'This user is already a team member.')
                return redirect('team:detail', pk=pk)

            allowed, message = can_add_member(team, include_message=True)
            if not allowed:
                messages.error(request, message)
                return redirect(get_safe_return_url(request, reverse('team:plans')))

            TeamMembership.objects.create(
                team=team,
                user=user,
                role=TeamMembership.ROLE_MEMBER,
            )
            messages.success(request, f'{user.username} was added to the team.')
            return redirect('team:detail', pk=pk)
    else:
        form = AddTeamMemberForm()

    return render(request, 'team/add_team_member.html', {
        'team': team,
        'form': form,
    })


@login_required
def select_plan(request, pk):
    team = request.user.userprofile.active_team

    if not team or not team.can_manage_billing(request.user):
        return _permission_denied_redirect(request, 'team:plans')

    plan = get_object_or_404(Plan, pk=pk)

    team.plan = plan
    team.save(update_fields=['plan'])

    messages.success(request, f'Your team is now on the {plan.name} plan.')

    return redirect('team:plans')


@login_required
def plan_list(request):
    team = request.user.userprofile.active_team
    current_plan = get_team_plan(team) if team else None
    plans = Plan.objects.all()

    return render(request, 'team/plan_list.html', {
        'team': team,
        'plan_rows': get_plan_rows(plans, current_plan),
        'current_plan': current_plan,
        'can_manage_billing_for_team': team.can_manage_billing(request.user) if team else False,
    })


@login_required
def upgrade_plan(request):
    team = request.user.userprofile.active_team

    if not team or not team.can_manage_billing(request.user):
        fallback_url = reverse('team:detail', kwargs={'pk': team.pk}) if team else 'team:list'
        return _permission_denied_redirect(request, fallback_url)

    current_plan = get_team_plan(team)

    return render(request, 'team/upgrade_plan.html', {
        'team': team,
        'plan': current_plan,
        'current_plan_row': get_plan_rows([current_plan], current_plan)[0],
    })


@login_required
def teams_list(request):
    teams = _team_queryset_for_user(request.user).prefetch_related('memberships__user')
    team_rows = [
        {
            'team': team,
            'membership': team.get_membership(request.user),
        }
        for team in teams
    ]

    return render(request, 'team/teams_list.html', {'team_rows': team_rows})


@login_required
def teams_activate(request, pk):
    team = get_object_or_404(_team_queryset_for_user(request.user), pk=pk)
    userprofile = request.user.userprofile
    userprofile.active_team = team
    userprofile.save(update_fields=['active_team'])

    return redirect('team:detail', pk=pk)


@login_required
def detail(request, pk):
    team = get_object_or_404(
        _team_queryset_for_user(request.user).prefetch_related('memberships__user'),
        pk=pk,
    )
    active_team = getattr(getattr(request.user, 'userprofile', None), 'active_team', None)
    is_active_team = active_team and active_team.pk == team.pk
    team_roles_enabled = can_use_team_roles(team)
    can_manage_members_for_team = bool(is_active_team and _can_manage_members(team, request.user))

    return render(request, 'team/detail.html', {
        'team': team,
        'member_rows': _get_member_rows(team, request.user, allow_actions=bool(is_active_team)),
        'can_manage_team_for_team': bool(is_active_team and team.can_manage_team(request.user)),
        'can_manage_members_for_team': can_manage_members_for_team,
        'can_manage_billing_for_team': bool(is_active_team and team.can_manage_billing(request.user)),
        'current_team_membership': team.get_membership(request.user),
        'is_active_team': is_active_team,
        'team_roles_enabled': team_roles_enabled,
        'team_roles_message': TEAM_ROLES_MESSAGE,
        'current_plan': get_team_plan(team),
    })


@login_required
def edit_team(request, pk):
    team = _get_scoped_active_team(request, pk)
    if not team:
        return _permission_denied_redirect(request, 'team:list')

    if not team.can_manage_team(request.user):
        return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)

        if form.is_valid():
            form.save()
            messages.success(request, 'The changes were saved!')
            return redirect('team:detail', pk=pk)
    else:
        form = TeamForm(instance=team)

    return render(request, 'team/edit_team.html', {
        'team': team,
        'form': form,
    })


@login_required
@require_POST
def remove_team_member(request, pk, user_id):
    team = _get_scoped_active_team(request, pk)
    if not team:
        return _permission_denied_redirect(request, 'team:list')

    if not _can_manage_members(team, request.user):
        return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    membership = get_object_or_404(
        TeamMembership.objects.select_related('user'),
        team=team,
        user_id=user_id,
    )

    if membership.role == TeamMembership.ROLE_OWNER:
        messages.error(request, 'The team owner cannot be removed.')
        return redirect('team:detail', pk=pk)

    if membership.user_id == request.user.id:
        messages.error(request, 'Use a different owner or admin to change your own membership.')
        return redirect('team:detail', pk=pk)

    if can_use_team_roles(team) and team.is_admin(request.user) and not team.is_owner(request.user):
        if membership.role != TeamMembership.ROLE_MEMBER:
            return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    removed_user = membership.user
    membership.delete()
    _sync_removed_users_active_team(removed_user, team)

    messages.success(request, f'{removed_user.username} was removed from the team.')
    return redirect('team:detail', pk=pk)


@login_required
@require_POST
def promote_team_member(request, pk, user_id):
    team = _get_scoped_active_team(request, pk)
    if not team:
        return _permission_denied_redirect(request, 'team:list')

    if not can_use_team_roles(team):
        messages.error(request, TEAM_ROLES_MESSAGE)
        return redirect('team:detail', pk=pk)

    if not team.can_manage_billing(request.user):
        return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    membership = get_object_or_404(
        TeamMembership.objects.select_related('user'),
        team=team,
        user_id=user_id,
    )

    if membership.user_id == request.user.id:
        messages.error(request, 'You cannot change your own role here.')
        return redirect('team:detail', pk=pk)

    if membership.role != TeamMembership.ROLE_MEMBER:
        messages.error(request, 'Only regular members can be promoted to admin.')
        return redirect('team:detail', pk=pk)

    membership.role = TeamMembership.ROLE_ADMIN
    membership.save(update_fields=['role'])

    messages.success(request, f'{membership.user.username} is now an admin.')
    return redirect('team:detail', pk=pk)


@login_required
@require_POST
def demote_team_member(request, pk, user_id):
    team = _get_scoped_active_team(request, pk)
    if not team:
        return _permission_denied_redirect(request, 'team:list')

    if not can_use_team_roles(team):
        messages.error(request, TEAM_ROLES_MESSAGE)
        return redirect('team:detail', pk=pk)

    if not team.can_manage_billing(request.user):
        return _permission_denied_redirect(request, reverse('team:detail', kwargs={'pk': pk}))

    membership = get_object_or_404(
        TeamMembership.objects.select_related('user'),
        team=team,
        user_id=user_id,
    )

    if membership.role == TeamMembership.ROLE_OWNER:
        messages.error(request, 'The owner role cannot be demoted.')
        return redirect('team:detail', pk=pk)

    if membership.user_id == request.user.id:
        messages.error(request, 'You cannot change your own role here.')
        return redirect('team:detail', pk=pk)

    if membership.role != TeamMembership.ROLE_ADMIN:
        messages.error(request, 'Only admins can be demoted to member.')
        return redirect('team:detail', pk=pk)

    membership.role = TeamMembership.ROLE_MEMBER
    membership.save(update_fields=['role'])

    messages.success(request, f'{membership.user.username} is now a member.')
    return redirect('team:detail', pk=pk)
