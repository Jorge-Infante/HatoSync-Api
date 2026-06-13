"""Servicios de livestock: genealogía."""
from .models import Animal

GENEALOGY_DEFAULT_DEPTH = 3   # padres -> abuelos -> bisabuelos
GENEALOGY_MAX_DEPTH = 5


def build_genealogy(animal, depth=GENEALOGY_DEFAULT_DEPTH, request=None):
    """Árbol de ancestros del animal hasta `depth` generaciones.

    Los ancestros inactivos (vendidos/muertos) SÍ se incluyen — la genealogía
    es histórica — marcados con su `is_active` para que el front los distinga.
    Carga una query por generación (no una por animal); los ancestros repetidos
    (consanguinidad) se buscan una sola vez.
    """
    depth = max(1, min(int(depth), GENEALOGY_MAX_DEPTH))

    # Carga por niveles: padres del nivel actual en una sola query.
    by_id = {animal.pk: animal}
    current = [animal]
    for _ in range(depth):
        parent_ids = set()
        for item in current:
            parent_ids.update((item.mother_id, item.father_id))
        parent_ids.discard(None)
        parent_ids -= set(by_id)
        if not parent_ids:
            break
        current = list(Animal.objects.filter(pk__in=parent_ids).prefetch_related('photos'))
        by_id.update({a.pk: a for a in current})

    def photo_url(item):
        photo = next(iter(item.photos.all()), None)  # ordering -created_at: la más reciente
        if photo is None:
            return None
        url = photo.image.url
        return request.build_absolute_uri(url) if request else url

    def node(item, remaining):
        if item is None:
            return None
        data = {
            'id': item.pk,
            'name': item.name,
            'sex': item.sex,
            'sex_display': item.get_sex_display(),
            'birth_date': item.birth_date,
            'photo': photo_url(item),
            'is_active': item.is_active,
        }
        if remaining > 0:
            data['mother'] = node(by_id.get(item.mother_id), remaining - 1)
            data['father'] = node(by_id.get(item.father_id), remaining - 1)
        else:
            # Última generación pedida: avisa si el árbol sigue hacia arriba
            # (el front puede navegar haciendo genealogy/ sobre este id).
            data['has_more_ancestors'] = bool(item.mother_id or item.father_id)
        return data

    return node(animal, depth)
