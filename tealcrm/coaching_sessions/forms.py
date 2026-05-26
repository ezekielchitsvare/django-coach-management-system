from django import forms
from .models import Session

class AddSessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ('client', 'title', 'session_date', 'duration_minutes', 'status', 'notes')
        widgets = {
            'client': forms.Select(attrs={
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
                'placeholder': 'Session title...',
            }),
            'session_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full rounded-xl bg-slate-800 text-white border border-slate-600 p-3 focus:ring-2 focus:ring-teal-500',
                'rows': 5,
                'placeholder': 'Add notes...',
            }),
        }