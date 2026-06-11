from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import DeferredFilesMixin

from .managers import UserManager


def user_avatar_upload_to(instance, filename):
    return f'users/{instance.pk}/avatar/{filename}'


class User(DeferredFilesMixin, AbstractUser):
    """Custom user model with email as login."""

    DEFERRED_FILE_FIELDS = ('avatar',)

    username = None
    email = models.EmailField('correo electrónico', unique=True)
    full_name = models.CharField('nombre completo', max_length=255)
    phone = models.CharField('teléfono', max_length=20, blank=True)
    avatar = models.ImageField('avatar', upload_to=user_avatar_upload_to, null=True, blank=True)
    active_farm = models.ForeignKey(
        'farms.Farm', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='active_users', verbose_name='finca activa',
        help_text='Finca sobre la que opera el usuario actualmente (multi-tenancy).',
    )
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['-created_at']

    def __str__(self):
        return self.email
