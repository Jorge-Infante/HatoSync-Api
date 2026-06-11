from django.db import transaction
from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.accounts.models import User

from ..models import Farm, FarmMember


class FarmMemberSerializer(serializers.ModelSerializer):
    """Serializer para miembros de finca."""

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = FarmMember
        fields = ('id', 'user', 'user_id', 'role', 'role_display', 'is_active', 'joined_at')
        read_only_fields = ('id', 'joined_at')


class FarmSerializer(serializers.ModelSerializer):
    """Serializer para fincas, incluye sus miembros activos."""

    members = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = (
            'id', 'name', 'legal_name', 'tax_id', 'phone', 'email',
            'address', 'department', 'city', 'country',
            'latitude', 'longitude', 'logo',
            'is_active', 'members', 'members_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def _active_members(self, obj):
        # Usa la caché del prefetch si el queryset la trae; si no, consulta.
        return [m for m in obj.members.all() if m.is_active]

    def get_members(self, obj):
        return FarmMemberSerializer(self._active_members(obj), many=True).data

    def get_members_count(self, obj):
        return len(self._active_members(obj))

    def create(self, validated_data):
        farm = super().create(validated_data)
        user = self.context['request'].user
        # El superusuario administra la plataforma, no es miembro de las fincas.
        if not user.is_superuser:
            FarmMember.objects.create(farm=farm, user=user, role=FarmMember.Role.OWNER)
        user.active_farm = farm
        user.save(update_fields=['active_farm'])
        return farm


class FarmDetailSerializer(FarmSerializer):
    """Serializer detallado de finca (los miembros ya vienen en FarmSerializer)."""


# --- Setup (crear finca + usuarios en una sola petición) ---


class SetupMemberSerializer(serializers.Serializer):
    """Un miembro nuevo para el setup de finca."""

    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20, required=False, default='')
    password = serializers.CharField(write_only=True, min_length=8)
    # OWNER se excluye: ese rol se asigna automáticamente al creador de la finca.
    role = serializers.ChoiceField(
        choices=[c for c in FarmMember.Role.choices if c[0] != FarmMember.Role.OWNER],
    )


class FarmSetupSerializer(serializers.Serializer):
    """
    Crea una finca + usuarios + membresías en una sola petición.
    El usuario autenticado queda como OWNER.
    """

    # Datos de la finca
    name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(max_length=255, required=False, default='')
    tax_id = serializers.CharField(max_length=50, required=False, default='')
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, default='')
    address = serializers.CharField(max_length=255)
    department = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=5, required=False, default='CO')

    # Miembros (opcional)
    members = SetupMemberSerializer(many=True, required=False)

    def validate_members(self, members):
        emails = [m['email'] for m in members]
        if len(emails) != len(set(emails)):
            raise serializers.ValidationError('Hay emails duplicados en la lista de miembros.')

        request_user = self.context['request'].user
        if not request_user.is_superuser and request_user.email in emails:
            raise serializers.ValidationError(
                f'{request_user.email} ya será OWNER de la finca, no lo incluyas como miembro.'
            )

        existing = User.objects.filter(email__in=emails).values_list('email', flat=True)
        if existing:
            raise serializers.ValidationError(
                f'Ya existen usuarios con estos emails: {", ".join(existing)}'
            )

        return members

    @transaction.atomic
    def create(self, validated_data):
        members_data = validated_data.pop('members', [])
        request_user = self.context['request'].user

        # 1. Crear finca
        farm = Farm.objects.create(**validated_data)

        # 2. Owner (el superusuario administra la plataforma, no es miembro)
        if not request_user.is_superuser:
            FarmMember.objects.create(farm=farm, user=request_user, role=FarmMember.Role.OWNER)
        request_user.active_farm = farm
        request_user.save(update_fields=['active_farm'])

        # 3. Crear usuarios y membresías
        for member_data in members_data:
            role = member_data.pop('role')
            user = User.objects.create_user(**member_data)
            FarmMember.objects.create(farm=farm, user=user, role=role)

        return farm

    def to_representation(self, farm):
        return FarmDetailSerializer(farm).data
