
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from coaching_sessions.models import Session
from core.utils import get_safe_next_url, get_safe_return_url
from team.plan_limits import PLAN_LIMIT_MESSAGE, can_add_client, can_use_export_tools, get_team_plan

from .forms import AddClientForm, AddCommentForm, AddFileForm
from .models import Client


@login_required
def clients_export(request):
    team = request.user.userprofile.active_team
    allowed, message = can_use_export_tools(team, include_message=True)
    if not allowed:
        messages.error(request, message)
        return redirect('clients:list')

    clients = Client.objects.filter(team=team)

    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="clients.csv"'},
    )

    writer = csv.writer(response)
    writer.writerow(['Client', 'Email', 'Description', 'Created at', 'Created by'])

    for client in clients:
        writer.writerow([
            client.name,
            client.email,
            client.description,
            client.created_at,
            client.created_by.username
        ])

    return response


@login_required
def clients_list(request):
    team = request.user.userprofile.active_team
    query = request.GET.get('q', '').strip()

    clients_queryset = Client.objects.filter(team=team)

    if query:
        clients_queryset = clients_queryset.filter(name__icontains=query)

    clients_queryset = clients_queryset.annotate(
        session_count=Count('sessions', distinct=True)
    ).order_by('-created_at')

    paginator = Paginator(clients_queryset, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    clients = page_obj.object_list

    return render(request, 'client/clients_list.html', {
        'clients': clients,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_count': paginator.count,
        'q': query,
        'can_use_export_tools': can_use_export_tools(team),
    })


@login_required
def clients_add_file(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    if request.method == 'POST':
        form = AddFileForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.save(commit=False)
            file.team = team
            file.client = client
            file.created_by = request.user
            file.save()

    if next_url:
        return redirect(next_url)

    return redirect('clients:detail', pk=pk)


@login_required
def clients_add_comment(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    if request.method == 'POST':
        form = AddCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.team = team
            comment.created_by = request.user
            comment.client = client
            comment.save()

    if next_url:
        return redirect(next_url)

    return redirect('clients:detail', pk=pk)

@login_required
def clients_detail(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    sessions = Session.objects.filter(
        team=team,
        client=client
    ).order_by('-session_date')

    return render(request, 'client/clients_detail.html', {
        'client': client,
        'sessions': sessions,
        'form': AddCommentForm(),
        'fileform': AddFileForm(),
        'next_url': next_url,
    })


@login_required
def clients_add(request):
    team = request.user.userprofile.active_team
    next_url = get_safe_next_url(request)
    allowed, message = can_add_client(team, include_message=True)
    if not allowed:
        messages.error(request, message)
        return redirect(get_safe_return_url(request, reverse('team:plans')))

    can_create_client = True

    if request.method == 'POST':
        form = AddClientForm(request.POST)

        if form.is_valid():
            allowed, message = can_add_client(team, include_message=True)
            if not allowed:
                messages.error(request, message)
                return redirect(get_safe_return_url(request, reverse('team:plans')))

            client = form.save(commit=False)
            client.created_by = request.user
            client.team = team
            client.save()

            messages.success(request, 'The client was created.')
            if next_url:
                return redirect(next_url)

            return redirect('clients:list')
    else:
        form = AddClientForm()

    return render(request, 'client/clients_add.html', {
        'form': form,
        'team': team,
        'plan': get_team_plan(team),
        'can_add_client': can_create_client,
        'client_limit_message': PLAN_LIMIT_MESSAGE,
        'next_url': next_url,
    })


@login_required
def clients_delete(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, team=team, pk=pk)
    next_url = get_safe_next_url(request)
    client.delete()

    messages.success(request, 'The client was deleted.')

    if next_url:
        return redirect(next_url)

    return redirect('clients:list')


@login_required
def clients_edit(request, pk):
    team = request.user.userprofile.active_team
    client = get_object_or_404(Client, team=team, pk=pk)
    next_url = get_safe_next_url(request)

    if request.method == 'POST':
        form = AddClientForm(request.POST, instance=client)

        if form.is_valid():
            form.save()
            messages.success(request, 'The changes were saved.')
            if next_url:
                return redirect(next_url)

            return redirect('clients:list')
    else:
        form = AddClientForm(instance=client)

    return render(request, 'client/clients_edit.html', {
        'form': form,
        'client': client,
        'next_url': next_url,
    })
