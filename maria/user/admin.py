from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('API Keys', {'fields': ('google_api_key', 'openai_api_key', 'anthropic_api_key')}),
        ('Extra', {'fields': ('telefono',)}),
    )
