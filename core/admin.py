from django.contrib import admin
from .models import GardenModule, UserPlant, TelemetryLog


@admin.register(GardenModule)
class GardenModuleAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'mac_address', 'user', 'created_at')
    search_fields = ('nombre', 'mac_address', 'user__username')
    list_filter = ('created_at',)


@admin.register(UserPlant)
class UserPlantAdmin(admin.ModelAdmin):
    list_display = ('apodo', 'api_species_id', 'module', 'temp_min', 'temp_max', 'humedad_optima')
    search_fields = ('apodo', 'api_species_id', 'module__nombre')


@admin.register(TelemetryLog)
class TelemetryLogAdmin(admin.ModelAdmin):
    list_display = ('module', 'temperatura', 'humedad', 'luz', 'timestamp')
    list_filter = ('module', 'timestamp')
    readonly_fields = ('timestamp',)

