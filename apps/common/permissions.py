from rest_framework.permissions import BasePermission


class HasActiveFarm(BasePermission):
    """
    Exige que el usuario tenga una finca activa y pertenezca a ella
    (los superusuarios pueden operar sobre cualquier finca activa).
    """

    message = (
        'No tienes una finca activa o no perteneces a ella. '
        'Selecciona una con POST /api/v1/auth/me/active-farm/.'
    )

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or user.active_farm_id is None:
            return False
        if user.is_superuser:
            return True
        return user.farm_memberships.filter(
            farm_id=user.active_farm_id,
            farm__is_active=True,
            is_active=True,
        ).exists()
