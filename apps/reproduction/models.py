from django.db import models
from django.utils import timezone


class ReproductiveStatus(models.TextChoices):
    """Estado reproductivo de una hembra. No se almacena: se deriva
    del último evento relevante (ver services.summarize_reproduction)."""

    OPEN = 'OPEN', 'Vacía'
    SERVED = 'SERVED', 'Servida'
    PREGNANT = 'PREGNANT', 'Preñada'
    CALVED = 'CALVED', 'Parida'


class ReproductiveEvent(models.Model):
    """Evento reproductivo de una hembra. Es la fuente de verdad:
    estado, días abiertos y fecha probable de parto se derivan de aquí."""

    class EventType(models.TextChoices):
        BIRTH = 'BIRTH', 'Parto'
        INSEMINATION = 'INSEMINATION', 'Inseminación'
        NATURAL_MATING = 'NATURAL_MATING', 'Monta natural'
        PREGNANCY_CHECK = 'PREGNANCY_CHECK', 'Chequeo de preñez'
        ABORTION = 'ABORTION', 'Aborto'
        WEANING = 'WEANING', 'Destete'

    class CheckResult(models.TextChoices):
        POSITIVE = 'POSITIVE', 'Positivo'
        NEGATIVE = 'NEGATIVE', 'Negativo'

    animal = models.ForeignKey(
        'livestock.Animal', on_delete=models.CASCADE,
        related_name='reproductive_events', verbose_name='animal',
    )
    event_type = models.CharField('tipo de evento', max_length=20, choices=EventType.choices)
    date = models.DateField('fecha', default=timezone.localdate)
    result = models.CharField(
        'resultado', max_length=10, choices=CheckResult.choices, blank=True,
        help_text='Solo para chequeos de preñez.',
    )
    gestation_days = models.PositiveSmallIntegerField(
        'días de gestación estimados', null=True, blank=True,
        help_text='Estimación del palpador en un chequeo positivo (monta libre sin servicio registrado).',
    )
    sire = models.ForeignKey(
        'livestock.Animal', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sired_events', verbose_name='toro/padre',
    )
    offspring = models.ForeignKey(
        'livestock.Animal', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='offspring_events', verbose_name='cría',
    )
    notes = models.TextField('notas', blank=True)
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('fecha de actualización', auto_now=True)

    class Meta:
        db_table = 'reproduction_reproductiveevent'
        verbose_name = 'evento reproductivo'
        verbose_name_plural = 'eventos reproductivos'
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['animal', 'date']),
            models.Index(fields=['animal', 'event_type']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} de {self.animal.name} ({self.date})'
