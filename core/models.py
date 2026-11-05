from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator

mac_validator = RegexValidator(
    regex=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
    message='Ingrese una dirección MAC válida (ej. AA:BB:CC:DD:EE:FF).'
)


class GardenModule(models.Model):
    """
    Representa el hardware físico (maceta inteligente IoT) asociado a un usuario.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='garden_modules',
        verbose_name='Propietario'
    )
    mac_address = models.CharField(
        max_length=17,
        unique=True,
        validators=[mac_validator],
        help_text='Identificador único de hardware (formato AA:BB:CC:DD:EE:FF)'
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre del Módulo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Módulo de Jardín'
        verbose_name_plural = 'Módulos de Jardín'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.mac_address}) - {self.user.username}"


class UserPlant(models.Model):
    """
    Planta asignada 1-a-1 a un módulo específico con sus umbrales personalizados.
    """
    module = models.OneToOneField(
        GardenModule,
        on_delete=models.CASCADE,
        related_name='plant',
        verbose_name='Módulo IoT'
    )
    api_species_id = models.CharField(
        max_length=100,
        verbose_name='ID de Especie (API Externa)'
    )
    apodo = models.CharField(max_length=100, verbose_name='Apodo de la Planta')

    # Umbrales personalizables
    temp_min = models.FloatField(
        default=15.0,
        help_text='Temperatura mínima tolerable en °C'
    )
    temp_max = models.FloatField(
        default=30.0,
        help_text='Temperatura máxima tolerable en °C'
    )
    humedad_optima = models.FloatField(
        default=60.0,
        help_text='Porcentaje de humedad de suelo óptima (%)'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Planta de Usuario'
        verbose_name_plural = 'Plantas de Usuarios'

    def __str__(self):
        return f"{self.apodo} [Especie #{self.api_species_id}] en {self.module.nombre}"


class TelemetryLog(models.Model):
    """
    Registro histórico de lecturas enviadas por los sensores del módulo.
    """
    module = models.ForeignKey(
        GardenModule,
        on_delete=models.CASCADE,
        related_name='telemetry_logs',
        verbose_name='Módulo IoT'
    )
    temperatura = models.FloatField(help_text='Temperatura ambiente en °C')
    humedad = models.FloatField(help_text='Humedad relativa/suelo en %')
    luz = models.FloatField(help_text='Nivel de luminosidad en Lux / %')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Registro de Telemetría'
        verbose_name_plural = 'Registros de Telemetría'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.module.mac_address} | T:{self.temperatura}°C H:{self.humedad}% L:{self.luz}"

