from django.utils import timezone
from rest_framework import serializers

from apps.livestock.models import Animal

from ..models import ReproductiveEvent

_EVENT_TYPE = ReproductiveEvent.EventType
_SERVICE_TYPES = (_EVENT_TYPE.INSEMINATION, _EVENT_TYPE.NATURAL_MATING)


class ReproductiveEventSerializer(serializers.ModelSerializer):
    """Serializer para eventos reproductivos. El animal llega por la URL."""

    # Escribible para soporte offline (UUID generado por el cliente; idempotente).
    id = serializers.UUIDField(required=False)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    sire_name = serializers.CharField(source='sire.name', read_only=True, default=None)
    offspring_name = serializers.CharField(source='offspring.name', read_only=True, default=None)

    class Meta:
        model = ReproductiveEvent
        fields = (
            'id', 'event_type', 'event_type_display', 'date',
            'result', 'gestation_days',
            'sire', 'sire_name', 'offspring', 'offspring_name',
            'notes', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('is_active', 'created_at', 'updated_at')

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura.')
        return value

    def _current(self, attrs, field):
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)

    def _validate_same_farm(self, related, label):
        if related.farm_id != self.context['request'].user.active_farm_id:
            raise serializers.ValidationError({label: 'El animal no pertenece a tu finca activa.'})

    def validate(self, attrs):
        event_type = self._current(attrs, 'event_type')
        result = self._current(attrs, 'result')
        gestation_days = self._current(attrs, 'gestation_days')
        sire = self._current(attrs, 'sire')
        offspring = self._current(attrs, 'offspring')

        if event_type == _EVENT_TYPE.PREGNANCY_CHECK and not result:
            raise serializers.ValidationError({'result': 'Un chequeo de preñez requiere resultado.'})
        if result and event_type != _EVENT_TYPE.PREGNANCY_CHECK:
            raise serializers.ValidationError({'result': 'Solo aplica para chequeos de preñez.'})
        if gestation_days and not (
            event_type == _EVENT_TYPE.PREGNANCY_CHECK and result == ReproductiveEvent.CheckResult.POSITIVE
        ):
            raise serializers.ValidationError(
                {'gestation_days': 'Solo aplica para chequeos de preñez positivos.'}
            )

        if sire:
            if event_type not in (*_SERVICE_TYPES, _EVENT_TYPE.BIRTH):
                raise serializers.ValidationError(
                    {'sire': 'Solo aplica para servicios (inseminación/monta) o partos.'}
                )
            self._validate_same_farm(sire, 'sire')
            if sire.sex != Animal.Sex.MALE:
                raise serializers.ValidationError({'sire': 'Debe ser un animal macho.'})

        if offspring:
            if event_type not in (_EVENT_TYPE.BIRTH, _EVENT_TYPE.WEANING):
                raise serializers.ValidationError({'offspring': 'Solo aplica para partos o destetes.'})
            self._validate_same_farm(offspring, 'offspring')

        return attrs


class WeanSerializer(serializers.Serializer):
    """Destetar: crea el evento WEANING. El animal llega por contexto."""

    date = serializers.DateField(required=False)
    offspring = serializers.PrimaryKeyRelatedField(
        queryset=Animal.objects.filter(is_active=True), required=False, allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura.')
        return value

    def validate_offspring(self, value):
        if value and value.farm_id != self.context['request'].user.active_farm_id:
            raise serializers.ValidationError('El animal no pertenece a tu finca activa.')
        return value

    def create(self, validated_data):
        return ReproductiveEvent.objects.create(
            animal=self.context['animal'],
            event_type=_EVENT_TYPE.WEANING,
            date=validated_data.get('date') or timezone.localdate(),
            offspring=validated_data.get('offspring'),
            notes=validated_data.get('notes', ''),
        )


class CalfSerializer(serializers.Serializer):
    """Datos mínimos de la cría a registrar junto con el parto."""

    name = serializers.CharField(max_length=255)
    sex = serializers.ChoiceField(choices=Animal.Sex.choices)


class BirthSerializer(serializers.Serializer):
    """Registrar parto: crea el evento BIRTH y, opcionalmente, la cría
    como animal de la finca (con madre/padre ya asignados)."""

    date = serializers.DateField(required=False)
    sire = serializers.PrimaryKeyRelatedField(
        queryset=Animal.objects.filter(is_active=True), required=False, allow_null=True,
    )
    calf = CalfSerializer(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura.')
        return value

    def validate_sire(self, value):
        if value:
            if value.farm_id != self.context['request'].user.active_farm_id:
                raise serializers.ValidationError('El animal no pertenece a tu finca activa.')
            if value.sex != Animal.Sex.MALE:
                raise serializers.ValidationError('Debe ser un animal macho.')
        return value

    def create(self, validated_data):
        cow = self.context['animal']
        date = validated_data.get('date') or timezone.localdate()
        sire = validated_data.get('sire')

        calf = None
        if validated_data.get('calf'):
            calf = Animal.objects.create(
                farm=cow.farm,
                name=validated_data['calf']['name'],
                sex=validated_data['calf']['sex'],
                birth_date=date,
                mother=cow,
                father=sire,
            )

        event = ReproductiveEvent.objects.create(
            animal=cow,
            event_type=_EVENT_TYPE.BIRTH,
            date=date,
            sire=sire,
            offspring=calf,
            notes=validated_data.get('notes', ''),
        )
        event.calf = calf  # para la respuesta de la vista
        return event
