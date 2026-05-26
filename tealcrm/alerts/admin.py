from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'team', 'session', 'is_read', 'created_at')
    list_filter = ('team', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'session__title', 'session__client__name')
