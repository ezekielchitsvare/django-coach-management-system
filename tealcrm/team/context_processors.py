def active_team(request):
    active_team = None
    active_team_membership = None
    can_manage_team = False
    can_manage_billing = False

    if request.user.is_authenticated:
        userprofile = getattr(request.user, 'userprofile', None)

        if userprofile and userprofile.active_team and userprofile.active_team.is_member(request.user):
            active_team = userprofile.active_team
        else:
            active_team = request.user.teams.first()

        if active_team:
            active_team_membership = active_team.get_membership(request.user)
            can_manage_team = active_team.can_manage_team(request.user)
            can_manage_billing = active_team.can_manage_billing(request.user)

    return {
        'active_team': active_team,
        'active_team_membership': active_team_membership,
        'can_manage_team': can_manage_team,
        'can_manage_billing': can_manage_billing,
    }
