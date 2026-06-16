from django.core.validators import RegexValidator
from django.db import models

# El valor de una identificación siempre es numérico, pero se guarda como texto
# para preservar el formato exacto (p. ej. los ceros a la izquierda en "0001").
digits_validator = RegexValidator(r'^\d+$', 'El valor debe contener solo dígitos.')


class IdentificationType(models.Model):
    """Tipo de identificación que cada finca configura (p. ej. Chapeta, Hierro)."""

    farm = models.ForeignKey(
        'farms.Farm', on_delete=models.CASCADE,
        related_name='identification_types', verbose_name='finca',
    )
    name = models.CharField('nombre', max_length=100)
    is_unique = models.BooleanField(
        'valor único', default=True,
        help_text='Si el valor no puede repetirse entre animales de la finca '
                  '(p. ej. chapeta sí, hierro no).',
    )
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)

    class Meta:
        db_table = 'configuration_identificationtype'
        verbose_name = 'tipo de identificación'
        verbose_name_plural = 'tipos de identificación'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['farm', 'name'],
                condition=models.Q(is_active=True),
                name='uq_identificationtype_farm_name_active',
            ),
        ]

    def __str__(self):
        return self.name


class Breed(models.Model):
    """Raza que cada finca configura (clasificación y KPIs)."""

    farm = models.ForeignKey(
        'farms.Farm', on_delete=models.CASCADE,
        related_name='breeds', verbose_name='finca',
    )
    name = models.CharField('nombre', max_length=100)
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)

    class Meta:
        db_table = 'configuration_breed'
        verbose_name = 'raza'
        verbose_name_plural = 'razas'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['farm', 'name'],
                condition=models.Q(is_active=True),
                name='uq_breed_farm_name_active',
            ),
        ]

    def __str__(self):
        return self.name


class AnimalIdentification(models.Model):
    """Valor de un tipo de identificación para un animal (p. ej. Chapeta = 0001).

    Tabla intermedia entre Animal y IdentificationType: un animal puede tener
    varias identificaciones (chapeta, hierro, etc.), una por tipo.
    """

    animal = models.ForeignKey(
        'livestock.Animal', on_delete=models.CASCADE,
        related_name='identifications', verbose_name='animal',
    )
    identification_type = models.ForeignKey(
        IdentificationType, on_delete=models.PROTECT,
        related_name='values', verbose_name='tipo de identificación',
    )
    value = models.CharField('valor', max_length=50, validators=[digits_validator])
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    class Meta:
        db_table = 'configuration_animalidentification'
        verbose_name = 'identificación de animal'
        verbose_name_plural = 'identificaciones de animales'
        ordering = ['identification_type__name']
        constraints = [
            models.UniqueConstraint(
                fields=['animal', 'identification_type'],
                name='uq_animalidentification_animal_type',
            ),
        ]

    def __str__(self):
        return f'{self.identification_type.name}: {self.value}'
