from django.db.models import Prefetch
from rest_framework import generics, status, viewsets
from rest_framework.response import Response

from apps.common.mixins import FarmScopedMixin

from ..models import Farm, FarmMember
from .serializers import (
    FarmDetailSerializer,
    FarmMemberSerializer,
    FarmSerializer,
    FarmSetupSerializer,
)


class FarmViewSet(viewsets.ModelViewSet):
    """CRUD de fincas del usuario autenticado."""

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Farm.objects.none()
        queryset = Farm.objects.filter(is_active=True)
        # El superusuario ve todas las fincas (para poder cambiar de finca activa);
        # los demás solo las fincas a las que pertenecen.
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                members__user=self.request.user,
                members__is_active=True,
            )
        return queryset.prefetch_related(
            Prefetch(
                'members',
                queryset=FarmMember.objects.filter(is_active=True).select_related('user'),
            ),
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FarmDetailSerializer
        return FarmSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class FarmSetupView(generics.CreateAPIView):
    """Crear finca + usuarios + membresías en una sola petición."""

    serializer_class = FarmSetupSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        return Response(serializer.to_representation(farm), status=status.HTTP_201_CREATED)


class FarmMemberViewSet(FarmScopedMixin, viewsets.ModelViewSet):
    """Gestión de miembros de la finca activa del usuario."""

    serializer_class = FarmMemberSerializer
    queryset = FarmMember.objects.select_related('user')
    http_method_names = ['get', 'post', 'patch', 'delete']

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])
