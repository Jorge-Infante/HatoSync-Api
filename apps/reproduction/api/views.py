from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.mixins import IdempotentCreateMixin
from apps.common.permissions import HasActiveFarm
from apps.livestock.models import Animal

from ..models import ReproductiveEvent
from .serializers import BirthSerializer, ReproductiveEventSerializer, WeanSerializer


def get_active_female(request, animal_id):
    """Resuelve la hembra de la finca activa o falla con 404/400."""
    animal = get_object_or_404(
        Animal, pk=animal_id, farm_id=request.user.active_farm_id, is_active=True,
    )
    if animal.sex != Animal.Sex.FEMALE:
        raise ValidationError('Los eventos reproductivos se registran sobre la hembra.')
    return animal


class ReproductiveEventViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    """Eventos reproductivos de una hembra de la finca activa."""

    serializer_class = ReproductiveEventSerializer
    permission_classes = (IsAuthenticated, HasActiveFarm)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ReproductiveEvent.objects.none()
        return ReproductiveEvent.objects.filter(
            animal_id=self.kwargs['animal_id'],
            animal__farm_id=self.request.user.active_farm_id,
            is_active=True,
        ).select_related('sire', 'offspring')

    def perform_create(self, serializer):
        serializer.save(animal=get_active_female(self.request, self.kwargs['animal_id']))

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class BaseReproductiveActionView(generics.GenericAPIView):
    """Acción de conveniencia sobre una hembra: crea el evento correspondiente."""

    permission_classes = (IsAuthenticated, HasActiveFarm)

    def post(self, request, animal_id):
        animal = get_active_female(request, animal_id)
        serializer = self.get_serializer(
            data=request.data, context={'request': request, 'animal': animal},
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(self.build_response(event), status=status.HTTP_201_CREATED)

    def build_response(self, event):
        return ReproductiveEventSerializer(event).data


class WeanView(BaseReproductiveActionView):
    """Destetar: registra el evento WEANING (fecha opcional, default hoy)."""

    serializer_class = WeanSerializer


class BirthView(BaseReproductiveActionView):
    """Registrar parto: crea el evento BIRTH y opcionalmente la cría."""

    serializer_class = BirthSerializer

    def build_response(self, event):
        data = ReproductiveEventSerializer(event).data
        calf = getattr(event, 'calf', None)
        data['calf'] = None
        if calf:
            data['calf'] = {
                'id': calf.pk, 'name': calf.name, 'sex': calf.sex,
                'birth_date': str(calf.birth_date),
                'mother': calf.mother_id, 'father': calf.father_id,
            }
        return data
