from rest_framework.permissions import IsAuthenticated

from .permissions import HasActiveFarm


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
