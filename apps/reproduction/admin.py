from django.contrib import admin

from .models import ReproductiveEvent


@admin.register(ReproductiveEvent)
class ReproductiveEventAdmin(admin.ModelAdmin):
    list_display = ('animal', 'event_type', 'date', 'result', 'sire', 'offspring', 'is_active')
    list_filter = ('event_type', 'result', 'is_active')
    search_fields = ('animal__name',)
    date_hierarchy = 'date'
