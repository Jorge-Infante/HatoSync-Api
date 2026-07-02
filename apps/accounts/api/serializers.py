from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer para datos del usuario (lectura y actualización de perfil)."""

    active_farm_name = serializers.CharField(source='active_farm.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'phone', 'avatar',
            'active_farm', 'active_farm_name',
            'is_active', 'created_at', 'updated_at',
        )
        # active_farm se cambia solo via POST /auth/me/active-farm/
        read_only_fields = ('id', 'email', 'active_farm', 'is_active', 'created_at', 'updated_at')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuario. Retorna tokens + data."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone', 'password')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            'user': UserSerializer(instance).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
        }


class ActiveFarmSerializer(serializers.Serializer):
    """Cambiar la finca activa del usuario autenticado."""

    # La finca usa PK UUID (migración 2026-06).
    farm_id = serializers.UUIDField()

    def validate_farm_id(self, value):
        from apps.farms.models import Farm

        user = self.context['request'].user

        if user.is_superuser:
            if not Farm.objects.filter(pk=value, is_active=True).exists():
                raise serializers.ValidationError('La finca no existe o está inactiva.')
            return value

        is_member = user.farm_memberships.filter(
            farm_id=value, farm__is_active=True, is_active=True,
        ).exists()
        if not is_member:
            raise serializers.ValidationError('No perteneces a esta finca.')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.active_farm_id = self.validated_data['farm_id']
        user.save(update_fields=['active_farm'])
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer para login. Retorna tokens + data del usuario."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Credenciales inválidas.')
        if not user.is_active:
            raise serializers.ValidationError('Cuenta desactivada.')

        # Si no tiene finca activa, se asigna la primera a la que pertenezca.
        if user.active_farm_id is None:
            membership = user.farm_memberships.filter(
                is_active=True, farm__is_active=True,
            ).select_related('farm').first()
            if membership:
                user.active_farm = membership.farm
                user.save(update_fields=['active_farm'])

        attrs['user'] = user
        return attrs

    def to_representation(self, validated_data):
        user = validated_data['user']
        refresh = RefreshToken.for_user(user)
        return {
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
        }
