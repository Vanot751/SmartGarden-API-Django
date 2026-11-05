from rest_framework import serializers
from .models import GardenModule, UserPlant, TelemetryLog


class TelemetryLogSerializer(serializers.ModelSerializer):
    """
    Serializador para registros históricos e ingesta de telemetría IoT.
    """
    class Meta:
        model = TelemetryLog
        fields = ('id', 'module', 'temperatura', 'humedad', 'luz', 'timestamp')
        read_only_fields = ('id', 'timestamp')
        extra_kwargs = {
            'module': {'required': False}
        }

    def validate_module(self, value):
        request = self.context.get('request')
        if request and value and value.user != request.user:
            raise serializers.ValidationError(
                'No tienes permiso para registrar telemetría en un módulo de otro usuario.'
            )
        return value


class UserPlantSerializer(serializers.ModelSerializer):
    """
    Serializador para la planta asignada 1-a-1 a un GardenModule.
    """
    class Meta:
        model = UserPlant
        fields = (
            'id',
            'module',
            'api_species_id',
            'apodo',
            'temp_min',
            'temp_max',
            'humedad_optima',
            'assigned_at',
        )
        read_only_fields = ('id', 'assigned_at')

    def validate_module(self, value):
        request = self.context.get('request')
        if request and value.user != request.user:
            raise serializers.ValidationError(
                'No puedes asignar una planta a un módulo que pertenece a otro usuario.'
            )
        return value

    def validate(self, attrs):
        temp_min = attrs.get('temp_min', getattr(self.instance, 'temp_min', 15.0))
        temp_max = attrs.get('temp_max', getattr(self.instance, 'temp_max', 30.0))
        if temp_min >= temp_max:
            raise serializers.ValidationError(
                {'temp_min': 'La temperatura mínima debe ser menor que la temperatura máxima.'}
            )
        return attrs


class GardenModuleSerializer(serializers.ModelSerializer):
    """
    Serializador para módulos de hardware (macetas inteligentes).
    El campo 'user' es de solo lectura y se asigna automáticamente en el backend.
    """
    user = serializers.ReadOnlyField(source='user.username')
    plant = UserPlantSerializer(read_only=True)

    class Meta:
        model = GardenModule
        fields = ('id', 'user', 'mac_address', 'nombre', 'plant', 'created_at')
        read_only_fields = ('id', 'user', 'plant', 'created_at')

