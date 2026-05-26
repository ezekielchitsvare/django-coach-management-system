from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import SignupForm
from .models import Userprofile

from team.models import Team, TeamMembership

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            
            team = Team.objects.create(name='The team name', created_by=user)
            TeamMembership.objects.create(
                team=team,
                user=user,
                role=TeamMembership.ROLE_OWNER,
            )

            Userprofile.objects.create(user=user, active_team=team)

            return redirect('/log_in/')
    else:
        form = SignupForm()

    return render(request, 'userprofile/signup.html', {
        'form': form
    })

@login_required
def myaccount(request):
    team = request.user.teams.first()

    return render(request, 'userprofile/myaccount.html', {
        'team': team
    })
