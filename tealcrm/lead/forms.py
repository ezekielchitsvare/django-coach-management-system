from django import forms
from .models import Lead, Comment, LeadFile


class AddLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ('name','email','description','priority','status',)
        labels = {
            'name': 'Lead name',
            'email': 'Email address',
            'description': 'Description',
            'priority': 'Priority',
            'status': 'Status',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'Enter lead name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'name@example.com',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
                'placeholder': 'Add a short summary, goals, or recent notes for this lead.',
                'rows': 6,
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 shadow-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20',
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
        model = LeadFile
        fields = ('file',)
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'block w-full rounded-xl border border-gray-300 bg-white p-4 text-gray-900 shadow-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500',
            })
        }
