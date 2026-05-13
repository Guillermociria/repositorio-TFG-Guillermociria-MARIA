from django.contrib import admin
from .models import Technique


@admin.register(Technique)
class TechniqueAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'tech_id', 'created_at']
    prepopulated_fields = {'tech_id': ('name',)}
    search_fields = ['name', 'tech_id']
