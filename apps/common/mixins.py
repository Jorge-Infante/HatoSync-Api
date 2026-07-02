from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import HasActiveFarm


class IdempotentCreateMixin:
    """
    Creación idempotente para soporte offline.

    El cliente genera el UUID del registro al crearlo sin conexión; al
    sincronizar lo envía como `id`. Si ese id ya existe en el scope del viewset
    (p. ej. un reintento tras una respuesta perdida), se devuelve el registro
    existente (200) en vez de fallar por clave duplicada. Requiere un serializer
    cuyo `id` sea escribible.
    """

    def create(self, request, *args, **kwargs):
        obj_id = request.data.get('id')
        if obj_id:
            try:
                existing = self.get_queryset().filter(pk=obj_id).first()
            except Exception:
                existing = None
            if existing is not None:
                return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)


class FarmScopedMixin:
    """
    Multi-tenancy por finca activa.

    Para viewsets de modelos con FK `farm`: limita el queryset a la finca
    activa del usuario y asigna esa finca automáticamente al crear registros.
    El viewset debe definir el atributo `queryset` base.
    """

    permission_classes = (IsAuthenticated, HasActiveFarm)

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        return queryset.filter(farm_id=self.request.user.active_farm_id)

    def perform_create(self, serializer):
        serializer.save(farm_id=self.request.user.active_farm_id)
