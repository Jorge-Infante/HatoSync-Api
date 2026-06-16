from rest_framework import serializers

from ..models import Breed, IdentificationType


class IdentificationTypeSerializer(serializers.ModelSerializer):
    """Serializer para tipos de identificación. La finca se asigna desde la activa."""

    class Meta:
        model = IdentificationType
        fields = ('id', 'name', 'is_unique', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class BreedSerializer(serializers.ModelSerializer):
    """Serializer para razas. La finca se asigna desde la activa."""

    class Meta:
        model = Breed
        fields = ('id', 'name', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')
