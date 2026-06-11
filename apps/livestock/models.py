from django.db import models
from django.utils import timezone


def animal_photo_upload_to(instance, filename):
    return f'farms/{instance.animal.farm_id}/animals/{instance.animal_id}/{filename}'


class Animal(models.Model):
    """Animal de una finca."""

    class Sex(models.TextChoices):
        MALE = 'MALE', 'Macho'
        FEMALE = 'FEMALE', 'Hembra'

    farm = models.ForeignKey(
        'farms.Farm', on_delete=models.CASCADE,
        related_name='animals', verbose_name='finca',
    )
    name = models.CharField('nombre', max_length=255)
    sex = models.CharField('sexo', max_length=10, choices=Sex.choices)
    birth_date = models.DateField('fecha de nacimiento', default=timezone.localdate)
    mother = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='maternal_offspring', verbose_name='madre',
    )
    father = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='paternal_offspring', verbose_name='padre',
    )
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    class Meta:
        db_table = 'livestock_animal'
        verbose_name = 'animal'
        verbose_name_plural = 'animales'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['farm', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_sex_display()})'


class AnimalPhoto(models.Model):
    """Foto de un animal (un animal puede tener varias)."""

    animal = models.ForeignKey(
        Animal, on_delete=models.CASCADE,
        related_name='photos', verbose_name='animal',
    )
    image = models.ImageField('imagen', upload_to=animal_photo_upload_to)
    caption = models.CharField('descripción', max_length=255, blank=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)

    class Meta:
        db_table = 'livestock_animalphoto'
        verbose_name = 'foto de animal'
        verbose_name_plural = 'fotos de animales'
        ordering = ['-created_at']

    def __str__(self):
        return f'Foto de {self.animal.name}'
