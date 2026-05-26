from django import forms
from .models import Client, Comment, ClientFile
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render




class AddClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('name', 'email', 'description',)
        labels = {
            'name': 'Client name',
            'email': 'Email address',
            'description': 'Description',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'Enter client name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'name@example.com',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'Add background, priorities, or a concise relationship summary.',
                'rows': 6,
            }),
        }

class AddCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full min-h-32 rounded-xl border border-gray-300 bg-white p-4 text-gray-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500',
                'placeholder': 'Write a comment...',
                'rows': 4,
            })
        }


class AddFileForm(forms.ModelForm):
    class Meta:
        model = ClientFile
        fields = ('file',)
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'block w-full rounded-xl border border-gray-300 bg-white p-4 text-gray-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500',
            })
        }

@login_required
def clients_add_comment(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, pk=pk, team=team)

    if request.method == 'POST':
        form = AddCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.team = team
            comment.client = client
            comment.created_by = request.user
            comment.save()

    return redirect('clients:detail', pk=pk)
