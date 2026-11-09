from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'phone')
    list_editable = ('email_verified',)
    search_fields = ('user__username', 'user__email')

