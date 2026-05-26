from django.shortcuts import render

from team.models import Plan
from team.plan_limits import get_plan_rows

def index(request):
    return render(request, 'core/index.html') 

def about(request):
    return render(request, 'core/about.html')

def pricing(request):
    return render(request, 'core/pricing.html', {
        'plan_rows': get_plan_rows(Plan.objects.all()),
    })

