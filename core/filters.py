import django_filters
from .models import TelemetryLog


class TelemetryLogFilter(django_filters.FilterSet):
    """
    FilterSet para filtrar registros de telemetría por rango de fechas (start_date / end_date)
    y por módulo IoT, ideal para alimentar los gráficos históricos en React.
    """
    start_date = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='gte',
        label='Fecha/Hora inicial (ISO 8601, ej: 2026-11-01T00:00:00Z)'
    )
    end_date = django_filters.DateTimeFilter(
        field_name='timestamp',
        lookup_expr='lte',
        label='Fecha/Hora final (ISO 8601, ej: 2026-11-05T23:59:59Z)'
    )

    class Meta:
        model = TelemetryLog
        fields = ['module', 'start_date', 'end_date']

