from django.contrib import admin

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'category', 'price_level', 'is_active')
    list_filter = ('city', 'category', 'price_level', 'is_active')
    search_fields = ('name', 'city', 'description')
    list_editable = ('is_active',)