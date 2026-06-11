from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.common.mixins import FarmScopedMixin
from apps.common.permissions import HasActiveFarm

from ..models import Animal, AnimalPhoto
from .serializers import AnimalPhotoSerializer, AnimalSerializer


class AnimalViewSet(FarmScopedMixin, viewsets.ModelViewSet):
    """CRUD de animales de la finca activa del usuario."""

    serializer_class = AnimalSerializer
    queryset = (
        Animal.objects.filter(is_active=True)
        .select_related('mother', 'father')
        .prefetch_related('photos')
    )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


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
