from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from core.views import (
    GardenModuleViewSet,
    UserPlantViewSet,
    TelemetryLogViewSet,
    PlantSearchProxy,
)

router = DefaultRouter()
router.register(r'modules', GardenModuleViewSet, basename='gardenmodule')
router.register(r'user-plants', UserPlantViewSet, basename='userplant')
router.register(r'telemetry', TelemetryLogViewSet, basename='telemetrylog')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Endpoints de Autenticación JWT
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Documentación OpenAPI 3 / Swagger UI (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Endpoint Proxy de Plantas (antes del router para evitar colisiones de rutas)
    path('api/plants/search/', PlantSearchProxy.as_view(), name='plant_search_proxy'),

    # Rutas generadas por DefaultRouter bajo /api/
    path('api/', include(router.urls)),
]
