import json

from rest_framework import serializers

from apps.configuration.models import AnimalIdentification, Breed, IdentificationType, digits_validator
from apps.reproduction.api.serializers import ReproductiveEventSerializer
from apps.reproduction.services import summarize_reproduction

from ..models import Animal, AnimalPhoto


def _photo_url(photo, context):
    """URL absoluta de una foto (o None), usando el request del contexto si lo hay."""
    if photo is None:
        return None
    request = context.get('request') if context else None
    url = photo.image.url
    return request.build_absolute_uri(url) if request else url


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

    # Escribible para soporte offline: el cliente puede generar el UUID al crear
    # sin conexión y enviarlo aquí (idempotente al sincronizar). Si se omite, el
    # modelo genera uno con uuid4.
    id = serializers.UUIDField(required=False)
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
    # Lectura: lista de fotos (objetos). Escritura: lista de archivos para adjuntar
    # en el mismo POST/PATCH (multipart). Las fotos existentes se conservan; para
    # quitarlas se usa el endpoint anidado de fotos.
    photos = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False,
        help_text='Imágenes a adjuntar (multipart, clave repetida "photos").',
    )
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
        read_only_fields = ('is_active', 'created_at', 'updated_at')

    def get_reproduction(self, obj):
        return summarize_reproduction(obj)

    def to_internal_value(self, data):
        # En multipart/form-data (cuando se suben fotos en el mismo request), las
        # fotos llegan como archivos repetidos bajo "photos" y las identificaciones
        # como string JSON. Se normaliza a un dict plano para el procesamiento DRF.
        if hasattr(data, 'getlist'):
            normalized = {key: data.get(key) for key in data.keys()}
            raw_ids = normalized.get('identifications')
            if isinstance(raw_ids, str):
                try:
                    normalized['identifications'] = json.loads(raw_ids) if raw_ids.strip() else []
                except json.JSONDecodeError:
                    raise serializers.ValidationError(
                        {'identifications': 'Debe ser una lista JSON válida.'}
                    )
            if 'photos' in data:
                normalized['photos'] = data.getlist('photos')
            data = normalized
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['identifications'] = AnimalIdentificationSerializer(
            instance.identifications.all(), many=True,
        ).data
        data['photos'] = AnimalPhotoSerializer(
            instance.photos.all(), many=True, context=self.context,
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

    def _add_photos(self, animal, photos):
        # Append: no reemplaza las existentes (para quitarlas está el endpoint de fotos).
        for image in photos:
            AnimalPhoto.objects.create(animal=animal, image=image)

    def create(self, validated_data):
        identifications = validated_data.pop('identifications', None)
        photos = validated_data.pop('photos', None)
        animal = super().create(validated_data)
        if identifications is not None:
            self._sync_identifications(animal, identifications)
        if photos:
            self._add_photos(animal, photos)
        return animal

    def update(self, instance, validated_data):
        identifications = validated_data.pop('identifications', None)
        photos = validated_data.pop('photos', None)
        animal = super().update(instance, validated_data)
        if identifications is not None:
            self._sync_identifications(animal, identifications)
        if photos:
            self._add_photos(animal, photos)
        return animal


class AnimalListSerializer(serializers.ModelSerializer):
    """Serializer liviano para el LISTADO. No trae el arreglo completo de fotos
    (solo la principal) ni colecciones pesadas; para todo eso está la ficha
    completa (`GET /animals/{id}/full/`). Así el listado escala sin recargarse."""

    sex_display = serializers.CharField(source='get_sex_display', read_only=True)
    mother_name = serializers.CharField(source='mother.name', read_only=True, default=None)
    father_name = serializers.CharField(source='father.name', read_only=True, default=None)
    breed_name = serializers.CharField(source='breed.name', read_only=True, default=None)
    identifications = AnimalIdentificationSerializer(many=True, read_only=True)
    primary_photo = serializers.SerializerMethodField(help_text='URL de la foto más reciente, o null.')
    births_count = serializers.IntegerField(read_only=True, default=0)
    offspring_count = serializers.IntegerField(read_only=True, default=0)
    reproduction = serializers.SerializerMethodField(
        help_text='Resumen reproductivo para el chip de estado (solo hembras).',
    )

    class Meta:
        model = Animal
        fields = (
            'id', 'name', 'sex', 'sex_display', 'birth_date',
            'mother', 'mother_name', 'father', 'father_name',
            'breed', 'breed_name', 'identifications', 'primary_photo',
            'births_count', 'offspring_count', 'reproduction',
            'is_active', 'created_at', 'updated_at',
        )

    def get_primary_photo(self, obj):
        # ordering del modelo es -created_at → el primero es el más reciente.
        return _photo_url(next(iter(obj.photos.all()), None), self.context)

    def get_reproduction(self, obj):
        return summarize_reproduction(obj)


class AnimalOffspringSerializer(serializers.ModelSerializer):
    """Cría (resumen mínimo) para la ficha completa."""

    sex_display = serializers.CharField(source='get_sex_display', read_only=True)

    class Meta:
        model = Animal
        fields = ('id', 'name', 'sex', 'sex_display', 'birth_date')


class AnimalDetailSerializer(AnimalSerializer):
    """Ficha COMPLETA del animal: hereda todo lo del animal (datos, raza,
    identificaciones, fotos, resumen reproductivo) y suma las colecciones
    relacionadas (historial de eventos reproductivos y crías). Solo lectura;
    se sirve en el endpoint dedicado `full/` para no recargar el listado."""

    reproductive_events = serializers.SerializerMethodField(
        help_text='Historial completo de eventos reproductivos (más reciente primero).',
    )
    offspring = serializers.SerializerMethodField(
        help_text='Crías de este animal (como madre o como padre).',
    )

    class Meta(AnimalSerializer.Meta):
        fields = AnimalSerializer.Meta.fields + ('reproductive_events', 'offspring')

    def get_reproductive_events(self, obj):
        events = sorted(
            (e for e in obj.reproductive_events.all() if e.is_active),
            key=lambda e: (e.date, e.pk), reverse=True,
        )
        return ReproductiveEventSerializer(events, many=True, context=self.context).data

    def get_offspring(self, obj):
        children = sorted(
            [*obj.maternal_offspring.all(), *obj.paternal_offspring.all()],
            key=lambda a: a.birth_date, reverse=True,
        )
        return AnimalOffspringSerializer(children, many=True, context=self.context).data
