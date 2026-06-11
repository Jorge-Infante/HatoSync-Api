from django.contrib import admin

from .models import Animal, AnimalPhoto


class AnimalPhotoInline(admin.TabularInline):
    model = AnimalPhoto
    extra = 0


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'sex', 'birth_date', 'farm', 'is_active')
    list_filter = ('sex', 'is_active', 'farm')
    search_fields = ('name',)
    inlines = (AnimalPhotoInline,)
