"""Derivación del estado reproductivo a partir de los eventos.

Nada de esto se almacena: el estado, los días abiertos y la fecha probable
de parto se calculan siempre desde la historia de eventos, así nunca se
desincronizan (ver decisión de diseño en CLAUDE.md).
"""
from datetime import timedelta

from django.utils import timezone

from .models import ReproductiveEvent, ReproductiveStatus

BOVINE_GESTATION_DAYS = 283

_EVENT_TYPE = ReproductiveEvent.EventType
_SERVICE_TYPES = (_EVENT_TYPE.INSEMINATION, _EVENT_TYPE.NATURAL_MATING)

_EMPTY_SUMMARY = {
    'status': None,
    'status_display': None,
    'calf_at_side': None,
    'open_days': None,
    'conception_date': None,
    'conception_source': None,
    'expected_due_date': None,
}


def summarize_reproduction(animal):
    """Resume la situación reproductiva de una hembra.

    Retorna un dict con: status (OPEN/SERVED/PREGNANT/CALVED), calf_at_side,
    open_days, conception_date, conception_source (SERVICE|ESTIMATED) y
    expected_due_date. Para machos, todas las claves en None.

    Usa `animal.reproductive_events.all()` para aprovechar el prefetch
    del viewset; los eventos inactivos se descartan aquí.
    """
    from apps.livestock.models import Animal

    if animal.sex != Animal.Sex.FEMALE:
        return dict(_EMPTY_SUMMARY)

    events = [e for e in animal.reproductive_events.all() if e.is_active]
    events.sort(key=lambda e: (e.date, e.pk))

    last_birth = next((e for e in reversed(events) if e.event_type == _EVENT_TYPE.BIRTH), None)
    last_weaning = next((e for e in reversed(events) if e.event_type == _EVENT_TYPE.WEANING), None)

    # Último evento que define estado. El destete solo afecta el caso "parida":
    # cierra la lactancia (vaca vacía) sin tocar servicios/preñeces posteriores.
    status_event = None
    for event in reversed(events):
        if event.event_type in (_EVENT_TYPE.BIRTH, _EVENT_TYPE.ABORTION, *_SERVICE_TYPES):
            status_event = event
            break
        if event.event_type == _EVENT_TYPE.PREGNANCY_CHECK and event.result:
            status_event = event
            break

    if status_event is None or status_event.event_type == _EVENT_TYPE.ABORTION:
        status = ReproductiveStatus.OPEN
    elif status_event.event_type == _EVENT_TYPE.BIRTH:
        # Parida = con cría al pie. Si ya se destetó (y no hay servicio
        # posterior al parto), la vaca queda vacía.
        weaned_after_birth = last_weaning and (
            (last_weaning.date, last_weaning.pk) > (status_event.date, status_event.pk)
        )
        status = ReproductiveStatus.OPEN if weaned_after_birth else ReproductiveStatus.CALVED
    elif status_event.event_type in _SERVICE_TYPES:
        status = ReproductiveStatus.SERVED
    elif status_event.result == ReproductiveEvent.CheckResult.POSITIVE:
        status = ReproductiveStatus.PREGNANT
    else:
        status = ReproductiveStatus.OPEN

    # Fecha de concepción: el servicio registrado manda; si no hay
    # (monta libre), se estima con los días de gestación del palpador.
    conception_date = None
    conception_source = None
    if status == ReproductiveStatus.PREGNANT:
        check = status_event
        service = next(
            (e for e in reversed(events)
             if e.event_type in _SERVICE_TYPES and (e.date, e.pk) <= (check.date, check.pk)),
            None,
        )
        if service:
            conception_date, conception_source = service.date, 'SERVICE'
        elif check.gestation_days:
            conception_date = check.date - timedelta(days=check.gestation_days)
            conception_source = 'ESTIMATED'
        else:
            conception_date, conception_source = check.date, 'ESTIMATED'

    # Días abiertos: del último parto a la concepción (preñada) o a hoy.
    open_days = None
    if last_birth:
        end = conception_date if status == ReproductiveStatus.PREGNANT else timezone.localdate()
        open_days = max((end - last_birth.date).days, 0)

    calf_at_side = bool(last_birth) and (
        last_weaning is None or (last_weaning.date, last_weaning.pk) < (last_birth.date, last_birth.pk)
    )

    expected_due_date = (
        conception_date + timedelta(days=BOVINE_GESTATION_DAYS) if conception_date else None
    )

    return {
        'status': status.value,
        'status_display': status.label,
        'calf_at_side': calf_at_side,
        'open_days': open_days,
        'conception_date': conception_date,
        'conception_source': conception_source,
        'expected_due_date': expected_due_date,
    }
