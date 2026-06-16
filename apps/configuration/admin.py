from django.contrib import admin

from .models import AnimalIdentification, Breed, IdentificationType


@admin.register(IdentificationType)
class IdentificationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'is_unique', 'is_active')
    list_filter = ('is_unique', 'is_active', 'farm')
    search_fields = ('name',)


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'is_active')
    list_filter = ('is_active', 'farm')
    search_fields = ('name',)


@admin.register(AnimalIdentification)
class AnimalIdentificationAdmin(admin.ModelAdmin):
    list_display = ('animal', 'identification_type', 'value')
    list_filter = ('identification_type',)
    search_fields = ('value', 'animal__name')
