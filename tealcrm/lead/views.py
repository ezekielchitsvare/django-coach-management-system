from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import redirect,get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, CreateView, View

from core.utils import get_safe_return_url
from .forms import AddCommentForm, AddFileForm
from .forms import AddLeadForm
from .models import Lead
from client.models import Client, Comment as ClientComment
from team.plan_limits import PLAN_LIMIT_MESSAGE, can_add_client, can_add_lead


class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = 'lead/lead_list.html'
    context_object_name = 'leads'

    def get_queryset(self):
        team = self.request.user.userprofile.active_team
        queryset = Lead.objects.filter(
            team=team,
            converted_to_client=False,
        )

        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        priority = self.request.GET.get('priority', '').strip()

        if query:
            queryset = queryset.filter(name__icontains=query)

        valid_statuses = dict(Lead.CHOICES_STATUS)
        if status in valid_statuses:
            queryset = queryset.filter(status=status)

        valid_priorities = dict(Lead.CHOICES_PRIORITY)
        if priority in valid_priorities:
            queryset = queryset.filter(priority=priority)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = Paginator(context['leads'], 25)
        page_obj = paginator.get_page(self.request.GET.get('page'))

        context['page_obj'] = page_obj
        context['leads'] = page_obj.object_list
        context['is_paginated'] = page_obj.has_other_pages()
        context['total_count'] = paginator.count
        context['total_pages'] = paginator.num_pages
        context['q'] = self.request.GET.get('q', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()
        context['selected_priority'] = self.request.GET.get('priority', '').strip()
        context['status_choices'] = Lead.CHOICES_STATUS
        context['priority_choices'] = Lead.CHOICES_PRIORITY

        return context
        
        
class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'lead/lead_detail.html'
    context_object_name = 'lead'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddCommentForm()
        context['fileform'] = AddFileForm()

    
    
        return context

    def get_queryset(self):
        team = self.request.user.userprofile.active_team
        return Lead.objects.filter(team=team, pk=self.kwargs.get('pk'))
    

class LeadDeleteView(LoginRequiredMixin, DeleteView):
    model = Lead
    template_name = 'lead/lead_confirm_delete.html'
    context_object_name = 'lead'
    success_url = reverse_lazy('leads:list')

    def get_queryset(self):
        team = self.request.user.userprofile.active_team
        return Lead.objects.filter(team=team, pk=self.kwargs.get('pk'))

    def form_valid(self, form):
        messages.success(self.request, 'The lead was deleted.')
        return super().form_valid(form)



class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = AddLeadForm
    template_name = 'lead/lead_form.html'
    success_url = reverse_lazy('leads:list')       
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit lead'
        context['can_add_lead'] = True
    
        return context
    
    

    def get_queryset(self):
        team = self.request.user.userprofile.active_team
        return Lead.objects.filter(team=team, pk=self.kwargs.get('pk'))

    def form_valid(self, form):
        messages.success(self.request, 'The changes were saved.')
        return super().form_valid(form)
    
   
    


class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    form_class = AddLeadForm
    template_name = 'lead/lead_form.html'
    success_url = reverse_lazy('leads:list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.request.user.userprofile.active_team
        context['team'] = team
        context['title'] = 'Add lead'
        context['can_add_lead'] = self.can_add_lead()
        context['lead_limit_message'] = PLAN_LIMIT_MESSAGE
    
        return context

    def get_team(self):
        return self.request.user.userprofile.active_team

    def can_add_lead(self):
        return can_add_lead(self.get_team())

    def _limit_redirect(self, message):
        messages.error(self.request, message)
        return redirect(get_safe_return_url(self.request, reverse('team:plans')))

    def dispatch(self, request, *args, **kwargs):
        allowed, message = can_add_lead(self.get_team(), include_message=True)
        if not allowed:
            return self._limit_redirect(message)

        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        team = self.get_team()
        allowed, message = can_add_lead(team, include_message=True)
        if not allowed:
            return self._limit_redirect(message)

        form.instance.created_by = self.request.user
        form.instance.team = team

        messages.success(self.request, 'The lead was created.')
        return super().form_valid(form)
    

class AddFileView(LoginRequiredMixin, View):
   

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        team = request.user.userprofile.active_team
        lead = get_object_or_404(Lead, team=team, pk=pk)

        form = AddFileForm(request.POST, request.FILES)

        if form.is_valid():
            file = form.save(commit=False)
            file.team = team
            file.lead = lead
            file.created_by = request.user
            file.save()

        return redirect('leads:detail', pk=pk)



class AddCommentView(LoginRequiredMixin, View):
   

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        team = request.user.userprofile.active_team
        lead = get_object_or_404(Lead, team=team, pk=pk)

        form = AddCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.team = team
            comment.created_by = request.user
            comment.lead = lead
            comment.save()

        return redirect('leads:detail', pk=pk)


class ConvertToClientView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        team = request.user.userprofile.active_team
        lead = get_object_or_404(Lead, team=team, pk=pk)

        if lead.converted_to_client:
            messages.error(request, 'This lead has already been converted.')
            return redirect('leads:detail', pk=lead.pk)

        allowed, message = can_add_client(team, include_message=True)
        if not allowed:
            messages.error(request, message)
            return redirect(get_safe_return_url(request, reverse('team:plans')))

        client = Client.objects.create(
            name=lead.name,
            email=lead.email,
            description=lead.description,
            created_by=request.user,
            team=team,
        )

        lead.converted_to_client = True
        lead.status = Lead.WON
        lead.save()

        comments = lead.comments.all()

        for comment in comments:
            ClientComment.objects.create(
                client=client,
                content=comment.content,
                created_by=comment.created_by,
                team=team
            )

        messages.success(request, 'The lead was converted to a client.')

        return redirect('clients:detail', pk=client.pk)
