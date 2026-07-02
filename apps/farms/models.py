import uuid

from django.conf import settings
from django.db import models

from apps.common.models import DeferredFilesMixin


def farm_logo_upload_to(instance, filename):
    return f'farms/{instance.pk}/logo/{filename}'


class Farm(DeferredFilesMixin, models.Model):
    """Finca o empresa ganadera."""

    DEFERRED_FILE_FIELDS = ('logo',)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('nombre', max_length=255)
    legal_name = models.CharField('razón social', max_length=255, blank=True)
    tax_id = models.CharField('NIT/RUT', max_length=50, blank=True)
    phone = models.CharField('teléfono', max_length=20)
    email = models.EmailField('correo electrónico', blank=True)
    address = models.CharField('dirección', max_length=255)
    department = models.CharField('departamento', max_length=100)
    city = models.CharField('ciudad', max_length=100)
    country = models.CharField('país', max_length=5, default='CO')
    latitude = models.DecimalField(
        'latitud', max_digits=10, decimal_places=7, null=True, blank=True,
    )
    longitude = models.DecimalField(
        'longitud', max_digits=10, decimal_places=7, null=True, blank=True,
    )
    logo = models.ImageField('logo', upload_to=farm_logo_upload_to, null=True, blank=True)
    is_active = models.BooleanField('activa', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    class Meta:
        db_table = 'farms_farm'
        verbose_name = 'finca'
        verbose_name_plural = 'fincas'
        ordering = ['name']

    def __str__(self):
        return self.name


class FarmMember(models.Model):
    """Relación entre un usuario y una finca con su rol."""

    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Propietario'
        ADMIN = 'ADMIN', 'Administrador'
        EMPLOYEE = 'EMPLOYEE', 'Empleado'
        PARTNER = 'PARTNER', 'Socio'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        Farm, on_delete=models.CASCADE, related_name='members', verbose_name='finca',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='farm_memberships', verbose_name='usuario',
    )
    role = models.CharField('rol', max_length=10, choices=Role.choices)
    is_active = models.BooleanField('activo', default=True)
    joined_at = models.DateTimeField('fecha de ingreso', auto_now_add=True)

    class Meta:
        db_table = 'farms_farmmember'
        verbose_name = 'miembro de finca'
        verbose_name_plural = 'miembros de finca'
        constraints = [
            models.UniqueConstraint(fields=['farm', 'user'], name='unique_farm_member'),
        ]

    def __str__(self):
        return f'{self.user} - {self.farm} ({self.get_role_display()})'
