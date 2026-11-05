import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend
from .models import GardenModule, UserPlant, TelemetryLog
from .serializers import (
    GardenModuleSerializer,
    UserPlantSerializer,
    TelemetryLogSerializer,
)
from .filters import TelemetryLogFilter


class GardenModuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet Multi-inquilino para gestionar los módulos IoT (macetas) del usuario autenticado.
    """
    serializer_class = GardenModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Aislamiento estricto: solo módulos pertenecientes al usuario autenticado
        return GardenModule.objects.filter(user=self.request.user).select_related('user', 'plant')

    def perform_create(self, serializer):
        # Inyección automática del usuario propietario desde el token JWT
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='telemetry')
    def telemetry(self, request, pk=None):
        """
        Endpoint de Ingesta IoT: POST /api/modules/{id}/telemetry/
        Recibe {"temperatura": float, "humedad": float, "luz": float} y crea el registro en TelemetryLog.
        """
        module = self.get_object()  # Valida pertenencia al usuario vía get_queryset()
        serializer = TelemetryLogSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(module=module)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserPlantViewSet(viewsets.ModelViewSet):
    """
    ViewSet Multi-inquilino para gestionar las plantas asignadas a los módulos del usuario.
    """
    serializer_class = UserPlantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Aislamiento estricto: solo plantas cuyos módulos pertenezcan al usuario autenticado
        return UserPlant.objects.filter(module__user=self.request.user).select_related('module')


class TelemetryLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet Multi-inquilino para consultar y registrar telemetría de los módulos del usuario.
    Soporta filtrado por rangos de fecha (?start_date=...&end_date=...) y módulo (?module=...).
    """
    serializer_class = TelemetryLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TelemetryLogFilter

    def get_queryset(self):
        # Aislamiento estricto: ningún usuario puede ver telemetría de otro usuario
        return TelemetryLog.objects.filter(module__user=self.request.user).select_related('module')

    def perform_create(self, serializer):
        module = serializer.validated_data.get('module')
        if not module:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'module': 'Este campo es obligatorio al crear directamente en /api/telemetry/.'})
        serializer.save()


class PlantSearchProxy(APIView):
    """
    Endpoint Proxy para consultar la Free Plant API sin exponer la API Key en el cliente React.
    Uso: GET /api/plants/search/?q=monstera
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response(
                {'error': 'Debes proporcionar un término de búsqueda en el parámetro "q".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Petición segura de servidor a servidor inyectando la API Key desde settings.py
            external_response = requests.get(
                settings.PLANT_API_BASE_URL,
                params={
                    'key': settings.PLANT_API_KEY,
                    'q': query,
                },
                timeout=10
            )
            external_response.raise_for_status()
            raw_data = external_response.json()

            # Normalización/limpieza del payload para el frontend
            raw_items = raw_data.get('data', raw_data if isinstance(raw_data, list) else [])
            cleaned_results = [
                {
                    'api_species_id': str(item.get('id')),
                    'common_name': item.get('common_name'),
                    'scientific_name': (
                        item.get('scientific_name')[0]
                        if isinstance(item.get('scientific_name'), list) and item.get('scientific_name')
                        else item.get('scientific_name')
                    ),
                    'watering': item.get('watering'),
                    'sunlight': item.get('sunlight', []),
                    'thumbnail': (
                        item.get('default_image', {}).get('thumbnail')
                        if isinstance(item.get('default_image'), dict)
                        else None
                    ),
                }
                for item in raw_items
            ]

            return Response(
                {
                    'query': query,
                    'count': len(cleaned_results),
                    'results': cleaned_results,
                },
                status=status.HTTP_200_OK
            )

        except requests.exceptions.Timeout:
            return Response(
                {'error': 'Tiempo de espera agotado al contactar el servicio botánico externo.'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            return Response(
                {
                    'error': 'Error de comunicación con la API externa de plantas.',
                    'detail': str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY
            )
