from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import FarmScopedMixin
from apps.common.permissions import HasActiveFarm
from apps.reproduction.models import ReproductiveEvent

from ..models import Animal, AnimalPhoto
from ..services import GENEALOGY_DEFAULT_DEPTH, build_genealogy
from .serializers import AnimalPhotoSerializer, AnimalSerializer


class AnimalViewSet(FarmScopedMixin, viewsets.ModelViewSet):
    """CRUD de animales de la finca activa del usuario."""

    serializer_class = AnimalSerializer
    queryset = (
        Animal.objects.filter(is_active=True)
        .select_related('mother', 'father', 'breed')
        .prefetch_related(
            'photos',
            'identifications__identification_type',
            Prefetch(
                'reproductive_events',
                queryset=ReproductiveEvent.objects.filter(is_active=True),
            ),
        )
        .annotate(
            # Partos (como madre): fechas de nacimiento distintas entre sus
            # hijos activos — los gemelos comparten fecha y cuentan como 1.
            births_count=Count(
                'maternal_offspring__birth_date',
                filter=Q(maternal_offspring__is_active=True),
                distinct=True,
            ),
            # Hijos (como padre): total de crías activas.
            offspring_count=Count(
                'paternal_offspring',
                filter=Q(paternal_offspring__is_active=True),
                distinct=True,
            ),
        )
    )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])

    @action(detail=True, methods=['get'])
    def genealogy(self, request, pk=None):
        """Árbol de ancestros del animal (?depth=1..5, default 3 = bisabuelos).

        Cada nodo trae id/nombre/sexo/foto y sus padres anidados; con el id,
        el front puede navegar a la genealogía de cualquier ancestro.
        """
        animal = self.get_object()
        try:
            depth = int(request.query_params.get('depth', GENEALOGY_DEFAULT_DEPTH))
        except (TypeError, ValueError):
            depth = GENEALOGY_DEFAULT_DEPTH
        return Response(build_genealogy(animal, depth, request=request))


class AnimalPhotoViewSet(viewsets.ModelViewSet):
    """Fotos de un animal de la finca activa (no usa FarmScopedMixin
    porque la finca llega a través del animal, no de un FK propio)."""

    serializer_class = AnimalPhotoSerializer
    permission_classes = (IsAuthenticated, HasActiveFarm)
    # Solo multipart: permite subir el archivo desde Swagger y desde el front.
    parser_classes = (MultiPartParser, FormParser)
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AnimalPhoto.objects.none()
        return AnimalPhoto.objects.filter(
            animal_id=self.kwargs['animal_id'],
            animal__farm_id=self.request.user.active_farm_id,
            animal__is_active=True,
        )

    def perform_create(self, serializer):
        animal = get_object_or_404(
            Animal,
            pk=self.kwargs['animal_id'],
            farm_id=self.request.user.active_farm_id,
            is_active=True,
        )
        serializer.save(animal=animal)
