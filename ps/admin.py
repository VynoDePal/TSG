from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Station, Session, RateSettings


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Informations personnelles'), {'fields': ('role',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
    )
    search_fields = ('username',)
    ordering = ('username',)


class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'status', 'has_current_session', 'created_at', 'updated_at')
    list_filter = ('type', 'status')
    search_fields = ('name',)
    ordering = ('name',)
    
    def has_current_session(self, obj):
        return obj.current_session is not None
    has_current_session.boolean = True
    has_current_session.short_description = _('Session active')


class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'player', 'station', 'start_time', 'end_time', 'duration', 'cost', 'is_active')
    list_filter = ('is_active', 'start_time')
    search_fields = ('player__username', 'station__name')
    ordering = ('-start_time',)
    readonly_fields = ('duration', 'cost')
    date_hierarchy = 'start_time'
    fieldsets = (
        (None, {
            'fields': ('player', 'station', 'is_active')
        }),
        ('Informations temporelles', {
            'fields': ('start_time', 'end_time', 'duration')
        }),
        ('Facturation', {
            'fields': ('cost',)
        }),
    )


class RateSettingsAdmin(admin.ModelAdmin):
    list_display = ('hourly_rate', 'station_type', 'description', 'created_by', 'is_active', 'updated_at')
    list_filter = ('station_type', 'is_active')
    search_fields = ('description', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    ordering = ('-updated_at',)
    fieldsets = (
        (None, {
            'fields': ('hourly_rate', 'station_type', 'description', 'is_active')
        }),
        (_('Informations de suivi'), {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Station, StationAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(RateSettings, RateSettingsAdmin)
