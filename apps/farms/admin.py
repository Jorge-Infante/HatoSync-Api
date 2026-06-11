from django.contrib import admin

from .models import Farm, FarmMember


class FarmMemberInline(admin.TabularInline):
    model = FarmMember
    extra = 1
    autocomplete_fields = ['user']


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'department', 'city', 'is_active', 'created_at')
    list_filter = ('is_active', 'department', 'country')
    search_fields = ('name', 'legal_name', 'tax_id')
    inlines = [FarmMemberInline]


@admin.register(FarmMember)
class FarmMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'farm', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'user__full_name', 'farm__name')
    autocomplete_fields = ['user', 'farm']
