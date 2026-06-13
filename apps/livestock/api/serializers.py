from rest_framework import serializers

from apps.reproduction.services import summarize_reproduction

from ..models import Animal, AnimalPhoto


class AnimalPhotoSerializer(serializers.ModelSerializer):
    """Serializer para fotos de un animal."""

    class Meta:
        model = AnimalPhoto
        fields = ('id', 'image', 'caption', 'created_at')
        read_only_fields = ('id', 'created_at')


class AnimalSerializer(serializers.ModelSerializer):
    """Serializer para animales. La finca se asigna desde la finca activa del usuario."""

    sex_display = serializers.CharField(source='get_sex_display', read_only=True)
    mother_name = serializers.CharField(source='mother.name', read_only=True, default=None)
    father_name = serializers.CharField(source='father.name', read_only=True, default=None)
    photos = AnimalPhotoSerializer(many=True, read_only=True)
    # Anotados en el queryset del viewset (siempre exactos, no se almacenan).
    births_count = serializers.IntegerField(read_only=True, default=0, help_text='Partos como madre.')
    offspring_count = serializers.IntegerField(read_only=True, default=0, help_text='Hijos como padre.')
    reproduction = serializers.SerializerMethodField(
        help_text='Estado reproductivo derivado de los eventos (solo hembras).',
    )

    class Meta:
        model = Animal
        fields = (
            'id', 'name', 'sex', 'sex_display', 'birth_date',
            'mother', 'mother_name', 'father', 'father_name',
            'births_count', 'offspring_count', 'reproduction',
            'photos', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'is_active', 'created_at', 'updated_at')

    def get_reproduction(self, obj):
        return summarize_reproduction(obj)

    def _validate_parent(self, parent, expected_sex, label):
        active_farm_id = self.context['request'].user.active_farm_id
        if parent.farm_id != active_farm_id:
            raise serializers.ValidationError({label: 'El animal no pertenece a tu finca activa.'})
        if parent.sex != expected_sex:
            expected = 'hembra' if expected_sex == Animal.Sex.FEMALE else 'macho'
            raise serializers.ValidationError({label: f'Debe ser un animal {expected}.'})
        if self.instance and parent.pk == self.instance.pk:
            raise serializers.ValidationError({label: 'Un animal no puede ser su propio padre/madre.'})

    def validate(self, attrs):
        mother = attrs.get('mother')
        father = attrs.get('father')
        if mother:
            self._validate_parent(mother, Animal.Sex.FEMALE, 'mother')
        if father:
            self._validate_parent(father, Animal.Sex.MALE, 'father')
        return attrs
