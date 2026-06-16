from rest_framework import viewsets

from apps.common.mixins import FarmScopedMixin

from ..models import Breed, IdentificationType
from .serializers import BreedSerializer, IdentificationTypeSerializer


class IdentificationTypeViewSet(FarmScopedMixin, viewsets.ModelViewSet):
    """CRUD de tipos de identificación de la finca activa del usuario."""

    serializer_class = IdentificationTypeSerializer
    queryset = IdentificationType.objects.filter(is_active=True)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class BreedViewSet(FarmScopedMixin, viewsets.ModelViewSet):
    """CRUD de razas de la finca activa del usuario."""

    serializer_class = BreedSerializer
    queryset = Breed.objects.filter(is_active=True)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
