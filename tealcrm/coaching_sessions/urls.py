from django.urls import path
from . import views

app_name = 'sessions'

urlpatterns = [
    path('', views.session_list, name='list'),
    path('dashboard/', views.session_dashboard, name='dashboard'),
    path('add/', views.session_add, name='add'),
    path('day/', views.session_day, name='day'),
    path('calendar/', views.session_calendar, name='calendar'),
    path('<int:pk>/', views.session_detail, name='detail'),
    path('<int:pk>/edit/', views.session_edit, name='edit'),
    path('<int:pk>/delete/', views.session_delete, name='delete'),
    
]