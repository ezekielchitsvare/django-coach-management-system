from django import forms
from .models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name',]



class AddTeamMemberForm(forms.Form):
    username = forms.CharField(max_length=150)
