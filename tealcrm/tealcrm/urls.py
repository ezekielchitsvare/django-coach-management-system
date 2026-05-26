from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views
from django.urls import path, include

from core.views import index, about, pricing
from userprofile.forms import LoginForm

urlpatterns = [
    path('', index, name='index'),
    path("__reload__/", include("django_browser_reload.urls")),
    path('dashboard/leads/', include('lead.urls')),
    path('dashboard/clients/', include('client.urls')),
    path('dashboard/', include('userprofile.urls')),
    path('pricing/', pricing, name='pricing'),
    path('dashboard/teams/', include('team.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('dashboard/sessions/', include('coaching_sessions.urls')),
    path('dashboard/notifications/', include(('alerts.urls', 'alerts'), namespace='alerts')),
    path('dashboard/notifications/', include(('alerts.urls', 'alerts'), namespace='notifications')),
    path('about/', about, name='about'),
    path(
        'log_in/',
        views.LoginView.as_view(
            template_name='userprofile/login.html',
            authentication_form=LoginForm
        ),
        name='login'
    ),
    path('log-out/', views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

