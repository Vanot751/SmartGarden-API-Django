from django.contrib import admin
from django.conf import settings
from django.views.static import serve
from django.urls import path, include
from django.urls import re_path
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
    TelemetryHistoryView,
    PlantSearchProxy,
)
from config.views import FrontendView

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
    path('api/telemetry/history/', TelemetryHistoryView.as_view(), name='telemetry_history'),

    # Rutas generadas por DefaultRouter bajo /api/
    path('api/', include(router.urls)),

    # Aplicación React compilada; API y administración conservan sus rutas.
    re_path(
        r'^assets/(?P<path>.*)$',
        serve,
        {'document_root': settings.BASE_DIR.parent / 'Web-React' / 'dist' / 'assets'},
    ),
    re_path(
        r'^(?P<path>SmartGarden\.png)$',
        serve,
        {'document_root': settings.BASE_DIR.parent / 'Web-React' / 'dist'},
    ),
    re_path(
        r'^plants/(?P<path>.*)$',
        serve,
        {'document_root': settings.BASE_DIR.parent / 'Web-React' / 'public' / 'plants'},
    ),
    re_path(r'^(?!api/|admin/|static/|assets/).*$',
            FrontendView.as_view(), name='frontend'),
]
