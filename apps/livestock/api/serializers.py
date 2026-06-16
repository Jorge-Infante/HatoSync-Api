from rest_framework import serializers

from apps.configuration.models import AnimalIdentification, Breed, IdentificationType, digits_validator
from apps.reproduction.services import summarize_reproduction

from ..models import Animal, AnimalPhoto


class AnimalPhotoSerializer(serializers.ModelSerializer):
    """Serializer para fotos de un animal."""

    class Meta:
        model = AnimalPhoto
        fields = ('id', 'image', 'caption', 'created_at')
        read_only_fields = ('id', 'created_at')


class AnimalIdentificationSerializer(serializers.ModelSerializer):
    """Lectura de una identificación del animal (tipo + valor)."""

    identification_type_name = serializers.CharField(
        source='identification_type.name', read_only=True,
    )

    class Meta:
        model = AnimalIdentification
        fields = ('id', 'identification_type', 'identification_type_name', 'value')


class AnimalIdentificationWriteSerializer(serializers.Serializer):
    """Escritura de una identificación: tipo + valor numérico."""

    identification_type = serializers.PrimaryKeyRelatedField(
        queryset=IdentificationType.objects.filter(is_active=True),
    )
    value = serializers.CharField(max_length=50, validators=[digits_validator])


class AnimalSerializer(serializers.ModelSerializer):
    """Serializer para animales. La finca se asigna desde la finca activa del usuario."""

    sex_display = serializers.CharField(source='get_sex_display', read_only=True)
    mother_name = serializers.CharField(source='mother.name', read_only=True, default=None)
    father_name = serializers.CharField(source='father.name', read_only=True, default=None)
    breed = serializers.PrimaryKeyRelatedField(
        queryset=Breed.objects.filter(is_active=True), required=False, allow_null=True,
    )
    breed_name = serializers.CharField(source='breed.name', read_only=True, default=None)
    # Identificaciones configuradas por la finca (chapeta, hierro, etc.). Se aceptan
    # en la escritura como lista [{identification_type, value}, ...] y se devuelven
    # resueltas (con el nombre del tipo) en `to_representation`.
    identifications = AnimalIdentificationWriteSerializer(many=True, required=False)
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
            'breed', 'breed_name', 'identifications',
            'births_count', 'offspring_count', 'reproduction',
            'photos', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'is_active', 'created_at', 'updated_at')

    def get_reproduction(self, obj):
        return summarize_reproduction(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['identifications'] = AnimalIdentificationSerializer(
            instance.identifications.all(), many=True,
        ).data
        return data

    def _validate_parent(self, parent, expected_sex, label):
        active_farm_id = self.context['request'].user.active_farm_id
        if parent.farm_id != active_farm_id:
            raise serializers.ValidationError({label: 'El animal no pertenece a tu finca activa.'})
        if parent.sex != expected_sex:
            expected = 'hembra' if expected_sex == Animal.Sex.FEMALE else 'macho'
            raise serializers.ValidationError({label: f'Debe ser un animal {expected}.'})
        if self.instance and parent.pk == self.instance.pk:
            raise serializers.ValidationError({label: 'Un animal no puede ser su propio padre/madre.'})

    def _validate_identifications(self, identifications):
        active_farm_id = self.context['request'].user.active_farm_id
        seen_types = set()
        for item in identifications:
            id_type = item['identification_type']
            if id_type.farm_id != active_farm_id:
                raise serializers.ValidationError(
                    {'identifications': f'El tipo "{id_type.name}" no pertenece a tu finca activa.'}
                )
            if id_type.pk in seen_types:
                raise serializers.ValidationError(
                    {'identifications': f'El tipo "{id_type.name}" está repetido.'}
                )
            seen_types.add(id_type.pk)
            if id_type.is_unique:
                clash = AnimalIdentification.objects.filter(
                    identification_type=id_type, value=item['value'], animal__is_active=True,
                )
                if self.instance is not None:
                    clash = clash.exclude(animal_id=self.instance.pk)
                if clash.exists():
                    raise serializers.ValidationError(
                        {'identifications': f'Ya existe un animal con {id_type.name} = {item["value"]}.'}
                    )

    def validate(self, attrs):
        mother = attrs.get('mother')
        father = attrs.get('father')
        if mother:
            self._validate_parent(mother, Animal.Sex.FEMALE, 'mother')
        if father:
            self._validate_parent(father, Animal.Sex.MALE, 'father')
        breed = attrs.get('breed')
        if breed and breed.farm_id != self.context['request'].user.active_farm_id:
            raise serializers.ValidationError({'breed': 'La raza no pertenece a tu finca activa.'})
        identifications = attrs.get('identifications')
        if identifications is not None:
            self._validate_identifications(identifications)
        return attrs

    def _sync_identifications(self, animal, identifications):
        animal.identifications.all().delete()
        AnimalIdentification.objects.bulk_create([
            AnimalIdentification(
                animal=animal,
                identification_type=item['identification_type'],
                value=item['value'],
            )
            for item in identifications
        ])

    def create(self, validated_data):
        identifications = validated_data.pop('identifications', None)
        animal = super().create(validated_data)
        if identifications is not None:
            self._sync_identifications(animal, identifications)
        return animal

    def update(self, instance, validated_data):
        identifications = validated_data.pop('identifications', None)
        animal = super().update(instance, validated_data)
        if identifications is not None:
            self._sync_identifications(animal, identifications)
        return animal
