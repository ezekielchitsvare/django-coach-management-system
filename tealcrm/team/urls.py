from django.urls import path

from . import views

app_name = 'team'

urlpatterns = [
    path('', views.teams_list, name='list'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit_team, name='edit'),
    path('<int:pk>/activate/', views.teams_activate, name='activate'),
    path('<int:pk>/add-member/', views.add_team_member, name='add_member'),
    path('<int:pk>/members/<int:user_id>/remove/', views.remove_team_member, name='remove_member'),
    path('<int:pk>/members/<int:user_id>/promote/', views.promote_team_member, name='promote_member'),
    path('<int:pk>/members/<int:user_id>/demote/', views.demote_team_member, name='demote_member'),
    path('plans/', views.plan_list, name='plans'),
    path('plans/<int:pk>/select/', views.select_plan, name='select_plan'),
    path('upgrade/', views.upgrade_plan, name='upgrade'),
]
