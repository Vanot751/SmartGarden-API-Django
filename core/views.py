import os
import requests
import math
import re
import unicodedata
from urllib.parse import quote
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from django_filters.rest_framework import DjangoFilterBackend
from .models import GardenModule, UserPlant, TelemetryLog
from .serializers import (
    GardenModuleSerializer,
    UserPlantSerializer,
    TelemetryLogSerializer,
    RegisterSerializer,
    EmailOrUsernameTokenObtainPairSerializer,
)
from .filters import TelemetryLogFilter


PLANT_IMAGE_CACHE = {}
LOCAL_PLANT_PLACEHOLDER = '/plants/herb.svg'
SPANISH_PLANT_SEARCH_ALIASES = {
    'manzanilla': ['chamomile', 'Matricaria chamomilla'],
    'camomila': ['chamomile', 'Matricaria chamomilla'],
    'copihue': ['lapageria rosea'],
}


def normalizeScientificName(scientific_name):
    if not isinstance(scientific_name, str):
        return ''

    normalized = scientific_name.strip()
    normalized = re.sub(r"\s*['\u2018\u2019][^'\u2018\u2019]*['\u2018\u2019]", '', normalized)
    normalized = re.sub(r'\s*[×]\s*', ' ', normalized)
    normalized = re.sub(r'\s+[xX]\s+(?=[A-Za-z])', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


normalize_scientific_name = normalizeScientificName


def resolvePlantImage(scientific_name, fallback_url):
    cleaned_name = normalizeScientificName(scientific_name)
    if cleaned_name in PLANT_IMAGE_CACHE:
        return PLANT_IMAGE_CACHE[cleaned_name]

    resolved_url = None

    if cleaned_name:
        try:
            inaturalist_response = requests.get(
                'https://api.inaturalist.org/v1/taxa',
                params={'q': cleaned_name, 'per_page': 1},
                timeout=10,
            )
            inaturalist_response.raise_for_status()
            inaturalist_data = inaturalist_response.json()
            results = inaturalist_data.get('results', [])
            if isinstance(results, list) and results:
                default_photo = results[0].get('default_photo')
                if isinstance(default_photo, dict):
                    medium_url = default_photo.get('medium_url')
                    if isinstance(medium_url, str) and medium_url.strip():
                        resolved_url = medium_url.strip()
        except requests.exceptions.RequestException:
            resolved_url = None

    if not resolved_url and cleaned_name:
        try:
            wikipedia_name = quote(cleaned_name.replace(' ', '_'), safe='')
            wikipedia_response = requests.get(
                f'https://en.wikipedia.org/api/rest_v1/page/summary/{wikipedia_name}',
                timeout=10,
            )
            wikipedia_response.raise_for_status()
            wikipedia_data = wikipedia_response.json()
            thumbnail = wikipedia_data.get('thumbnail')
            if isinstance(thumbnail, dict):
                source = thumbnail.get('source')
                if isinstance(source, str) and source.strip():
                    resolved_url = source.strip()
        except requests.exceptions.RequestException:
            resolved_url = None

    if not resolved_url and isinstance(fallback_url, str):
        fallback_url = fallback_url.strip()
        if fallback_url and 'upgrade_access' not in fallback_url.lower():
            resolved_url = fallback_url

    if not resolved_url:
        resolved_url = LOCAL_PLANT_PLACEHOLDER

    if cleaned_name:
        PLANT_IMAGE_CACHE[cleaned_name] = resolved_url
    return resolved_url


resolve_plant_image = resolvePlantImage

class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    """
    Permite autenticación JWT utilizando nombre de usuario o correo electrónico registrado.
    """
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                },
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


CHILEAN_PLANT_CATALOG = [
    {
        'api_species_id': 'smartgarden-limonero',
        'common_name': 'Limonero en maceta',
        'scientific_name': 'Citrus limon',
        'scientific_names': ['Citrus limon', 'Citrus medica var. limon', 'Citrus × limon'],
        'family': 'Rutaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/limonero.jpg',
        'temp_min': 5,
        'temp_max': 35,
        'humidity_min': 40,
        'watering_ml': 250,
        'description': 'Planta tropical de interior, muy común en hogares chilenos.'
    },
    {
        'api_species_id': 'smartgarden-naranjo',
        'common_name': 'Naranjo en maceta',
        'scientific_name': 'Citrus sinensis',
        'scientific_names': ['Citrus sinensis', 'Citrus × aurantium var. sinensis'],
        'family': 'Rutaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo', 'Luz brillante'],
        'thumbnail': '/plants/naranjo.jpg',
        'temp_min': 4,
        'temp_max': 34,
        'humidity_min': 38,
        'watering_ml': 180,
        'description': 'Cítrico frutal de patio, requiere sol directo, buen drenaje y riego regular.'
    },
    {
        'api_species_id': 'smartgarden-mandarino',
        'common_name': 'Mandarino en maceta',
        'scientific_name': 'Citrus reticulata',
        'scientific_names': ['Citrus reticulata', 'Citrus nobilis var. deliciosa'],
        'family': 'Rutaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo', 'Luz brillante'],
        'thumbnail': '/plants/mandarino.jpg',
        'temp_min': 3,
        'temp_max': 34,
        'humidity_min': 35,
        'watering_ml': 220,
        'description': 'Cítrico compacto productivo, adecuado para terrazas soleadas y macetones.'
    },
    {
        'api_species_id': 'smartgarden-palto',
        'common_name': 'Palto en maceta',
        'scientific_name': 'Persea americana',
        'scientific_names': ['Persea americana', 'Persea gratissima'],
        'family': 'Lauraceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo protegido'],
        'thumbnail': '/plants/palto.jpg',
        'temp_min': 6,
        'temp_max': 32,
        'humidity_min': 45,
        'watering_ml': 300,
        'description': 'Frutal subtropical de raíces sensibles, necesita humedad constante sin encharcar.'
    },
    {
        'api_species_id': 'smartgarden-higuera',
        'common_name': 'Higuera en maceta',
        'scientific_name': 'Ficus carica',
        'scientific_names': ['Ficus carica', 'Ficus communis'],
        'family': 'Moraceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/higuera.jpg',
        'temp_min': -2,
        'temp_max': 38,
        'humidity_min': 25,
        'watering_ml': 180,
        'description': 'Frutal rústico de hoja caduca, productivo en patios soleados y macetones grandes.'
    },
    {
        'api_species_id': 'smartgarden-olivo',
        'common_name': 'Olivo en maceta',
        'scientific_name': 'Olea europaea',
        'scientific_names': ['Olea europaea', 'Olea lancifolia'],
        'family': 'Oleaceae',
        'watering': 'Bajo',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/olivo.jpg',
        'temp_min': 0,
        'temp_max': 38,
        'humidity_min': 20,
        'watering_ml': 100,
        'description': 'Frutal mediterráneo de bajo consumo hídrico, ideal para terrazas soleadas.'
    },
    {
        'api_species_id': 'smartgarden-granado',
        'common_name': 'Granado en maceta',
        'scientific_name': 'Punica granatum',
        'scientific_names': ['Punica granatum', 'Granata punicum'],
        'family': 'Lythraceae',
        'watering': 'Bajo',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/granado.jpg',
        'temp_min': -2, 'temp_max': 38, 'humidity_min': 22, 'watering_ml': 150,
        'description': 'Frutal resistente al calor y la sequía, adecuado para terrazas soleadas.'
    },
    {
        'api_species_id': 'smartgarden-manzano',
        'common_name': 'Manzano enano',
        'scientific_name': 'Malus domestica',
        'family': 'Rosaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/manzano.jpg',
        'temp_min': -5, 'temp_max': 32, 'humidity_min': 45, 'watering_ml': 250,
        'description': 'Frutal de clima templado para macetones, con necesidad de frío invernal.'
    },
    {
        'api_species_id': 'smartgarden-peral',
        'common_name': 'Peral en maceta',
        'scientific_name': 'Pyrus communis',
        'family': 'Rosaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/peral.jpg',
        'temp_min': -4, 'temp_max': 32, 'humidity_min': 45, 'watering_ml': 250,
        'description': 'Frutal caducifolio de porte cónico, ideal para patios y huertos urbanos.'
    },
    {
        'api_species_id': 'smartgarden-duraznero',
        'common_name': 'Duraznero enano',
        'scientific_name': 'Prunus persica',
        'family': 'Rosaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/duraznero.jpg',
        'temp_min': -3, 'temp_max': 34, 'humidity_min': 40, 'watering_ml': 250,
        'description': 'Frutal de carozo muy común en Chile, requiere sol y buen drenaje.'
    },
    {
        'api_species_id': 'smartgarden-ciruelo',
        'common_name': 'Ciruelo en maceta',
        'scientific_name': 'Prunus domestica',
        'family': 'Rosaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/ciruelo.jpg',
        'temp_min': -4, 'temp_max': 34, 'humidity_min': 40, 'watering_ml': 200,
        'description': 'Frutal resistente para macetones profundos y exposición soleada.'
    },
    {
        'api_species_id': 'smartgarden-cerezo',
        'common_name': 'Cerezo en maceta',
        'scientific_name': 'Prunus avium',
        'family': 'Rosaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/cerezo.jpg',
        'temp_min': -6, 'temp_max': 32, 'humidity_min': 45, 'watering_ml': 250,
        'description': 'Frutal de clima templado que necesita acumulación de frío invernal.'
    },
    {
        'api_species_id': 'smartgarden-vid',
        'common_name': 'Vid de uva de mesa',
        'scientific_name': 'Vitis vinifera',
        'family': 'Vitaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/vid.jpg',
        'temp_min': -2, 'temp_max': 36, 'humidity_min': 30, 'watering_ml': 200,
        'description': 'Enredadera frutal para espaldera, muy adaptada a la zona central de Chile.'
    },
    {
        'api_species_id': 'smartgarden-arandano',
        'common_name': 'Arándano',
        'scientific_name': 'Vaccinium corymbosum',
        'family': 'Ericaceae',
        'watering': 'Frecuente',
        'sunlight': ['Sol directo', 'Semisombra'],
        'thumbnail': '/plants/arandano.jpg',
        'temp_min': -3, 'temp_max': 30, 'humidity_min': 55, 'watering_ml': 200,
        'description': 'Frutal menor que requiere sustrato ácido, humedad constante y buen drenaje.'
    },
    {
        'api_species_id': 'smartgarden-frambueso',
        'common_name': 'Frambueso',
        'scientific_name': 'Rubus idaeus',
        'family': 'Rosaceae',
        'watering': 'Frecuente',
        'sunlight': ['Sol moderado', 'Semisombra'],
        'thumbnail': '/plants/frambueso.jpg',
        'temp_min': -4, 'temp_max': 30, 'humidity_min': 50, 'watering_ml': 200,
        'description': 'Frutal menor de clima fresco, necesita humedad regular y soporte.'
    },
    {
        'api_species_id': 'smartgarden-kumquat',
        'common_name': 'Kumquat o naranjo chino',
        'scientific_name': 'Fortunella margarita',
        'family': 'Rutaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/kumquat.jpg',
        'temp_min': 0, 'temp_max': 35, 'humidity_min': 35, 'watering_ml': 150,
        'description': 'Cítrico enano ornamental y productivo, excelente para terrazas.'
    },
    {
        'api_species_id': 'smartgarden-romero',
        'common_name': 'Romero',
        'scientific_name': 'Salvia rosmarinus',
        'scientific_names': ['Salvia rosmarinus', 'Rosmarinus officinalis'],
        'family': 'Lamiaceae',
        'watering': 'Bajo',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/romero.jpg',
        'temp_min': 5, 'temp_max': 36, 'humidity_min': 20, 'watering_ml': 80,
        'description': 'Aromática rústica chilena, tolerante a sequía y muy apta para maceta.'
    },
    {
        'api_species_id': 'smartgarden-menta',
        'common_name': 'Menta o hierbabuena',
        'scientific_name': 'Mentha spicata',
        'scientific_names': ['Mentha spicata', 'Mentha viridis', 'Mentha crispa'],
        'family': 'Lamiaceae',
        'watering': 'Frecuente',
        'sunlight': ['Semisombra luminosa'],
        'thumbnail': '/plants/menta.jpg',
        'temp_min': 8, 'temp_max': 30, 'humidity_min': 50, 'watering_ml': 150,
        'description': 'Aromática culinaria de crecimiento vigoroso que prefiere sustrato húmedo.'
    },
    {
        'api_species_id': 'smartgarden-oregano',
        'common_name': 'Orégano',
        'scientific_name': 'Origanum vulgare',
        'scientific_names': ['Origanum vulgare', 'Origanum creticum'],
        'family': 'Lamiaceae',
        'watering': 'Bajo',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/oregano.jpg',
        'temp_min': 6, 'temp_max': 35, 'humidity_min': 25, 'watering_ml': 100,
        'description': 'Aromática culinaria resistente, necesita sol y sustrato drenante.'
    },
    {
        'api_species_id': 'smartgarden-cilantro',
        'common_name': 'Cilantro',
        'scientific_name': 'Coriandrum sativum',
        'family': 'Apiaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol de mañana', 'Semisombra'],
        'thumbnail': '/plants/cilantro.jpg',
        'temp_min': 8, 'temp_max': 28, 'humidity_min': 45, 'watering_ml': 120,
        'description': 'Hierba culinaria de ciclo corto, sensible al calor excesivo y la sequedad.'
    },
    {
        'api_species_id': 'smartgarden-perejil',
        'common_name': 'Perejil',
        'scientific_name': 'Petroselinum crispum',
        'scientific_names': ['Petroselinum crispum', 'Apium petroselinum', 'Petroselinum sativum'],
        'family': 'Apiaceae',
        'watering': 'Moderado',
        'sunlight': ['Sol moderado', 'Semisombra'],
        'thumbnail': '/plants/perejil.jpg',
        'temp_min': 6, 'temp_max': 28, 'humidity_min': 45, 'watering_ml': 120,
        'description': 'Hierba culinaria de hojas abundantes, agradece humedad constante.'
    },
    {
        'api_species_id': 'smartgarden-lavanda-francesa',
        'common_name': 'Lavanda francesa',
        'scientific_name': 'Lavandula dentata',
        'scientific_names': ['Lavandula dentata', 'Lavandula stoechas', 'Lavandula officinalis'],
        'family': 'Lamiaceae',
        'watering': 'Bajo',
        'sunlight': ['Sol directo'],
        'thumbnail': '/plants/lavanda2.jpg',
        'temp_min': 4, 'temp_max': 35, 'humidity_min': 22, 'watering_ml': 80,
        'description': 'Ornamental aromática mediterránea, tolerante a sequía y calor.'
    },
    # Flores y ornamentales
    {
        'api_species_id': 'smartgarden-hortensia', 'common_name': 'Hortensia',
        'scientific_name': 'Hydrangea macrophylla', 'aliases': ['hortensia'],
        'family': 'Hydrangeaceae', 'watering': 'Alto', 'sunlight': ['Sombra luminosa'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 10, 'temp_max': 26,
        'humidity_min': 60, 'watering_ml': 300,
        'description': 'Ornamental de exterior que prefiere sombra luminosa, humedad alta y sustrato fresco.'
    },
    {
        'api_species_id': 'smartgarden-cardenal', 'common_name': 'Cardenal',
        'scientific_name': 'Pelargonium hortorum', 'aliases': ['geranio', 'cardenal'],
        'family': 'Geraniaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 30,
        'humidity_min': 30, 'watering_ml': 120,
        'description': 'Planta de balcón resistente, con sol directo y riego espaciado.'
    },
    {
        'api_species_id': 'smartgarden-bugambilia', 'common_name': 'Bugambilia',
        'scientific_name': 'Bougainvillea', 'aliases': ['buganvilla', 'bougainvillea'],
        'family': 'Nyctaginaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 38,
        'humidity_min': 20, 'watering_ml': 140,
        'description': 'Enredadera ornamental de sol pleno, muy resistente a la sequía.'
    },
    {
        'api_species_id': 'smartgarden-astromelia', 'common_name': 'Astromelia',
        'scientific_name': 'Alstroemeria', 'aliases': ['astromelia', 'lirio de los incas'],
        'family': 'Alstroemeriaceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 25,
        'humidity_min': 45, 'watering_ml': 180,
        'description': 'Flor de corte que agradece luz suave, sustrato drenado y humedad regular.'
    },
    {
        'api_species_id': 'smartgarden-pensamiento', 'common_name': 'Pensamiento',
        'scientific_name': 'Viola x wittrockiana', 'aliases': ['pensamiento', 'viola'],
        'family': 'Violaceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 2, 'temp_max': 24,
        'humidity_min': 45, 'watering_ml': 140,
        'description': 'Flor de temporada fresca, resistente al frío y adecuada para invierno.'
    },
    {
        'api_species_id': 'smartgarden-dalia', 'common_name': 'Dalia',
        'scientific_name': 'Dahlia', 'aliases': ['dalia'],
        'family': 'Asteraceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 28,
        'humidity_min': 45, 'watering_ml': 200,
        'description': 'Ornamental tuberosa de floración abundante, necesita sol y riego regular.'
    },
    {
        'api_species_id': 'smartgarden-calendula', 'common_name': 'Caléndula',
        'scientific_name': 'Calendula officinalis', 'aliases': ['calendula'],
        'family': 'Asteraceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 5, 'temp_max': 28,
        'humidity_min': 30, 'watering_ml': 120,
        'description': 'Flor medicinal de fácil cultivo, tolerante y apta para maceta.'
    },
    {
        'api_species_id': 'smartgarden-alheli', 'common_name': 'Alhelí',
        'scientific_name': 'Matthiola incana', 'aliases': ['alheli', 'alhelí'],
        'family': 'Brassicaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 5, 'temp_max': 25,
        'humidity_min': 40, 'watering_ml': 140,
        'description': 'Ornamental aromática de temporada, ideal para primavera.'
    },
    {
        'api_species_id': 'smartgarden-copihue', 'common_name': 'Copihue',
        'scientific_name': 'Lapageria rosea', 'aliases': ['copihue'],
        'family': 'Philesiaceae', 'watering': 'Alto', 'sunlight': ['Sombra luminosa'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 24,
        'humidity_min': 65, 'watering_ml': 300,
        'description': 'Enredadera nativa y flor nacional, requiere humedad y protección del sol fuerte.'
    },
    {
        'api_species_id': 'smartgarden-chilco', 'common_name': 'Chilco',
        'scientific_name': 'Fuchsia magellanica', 'aliases': ['chilco', 'fucsia'],
        'family': 'Onagraceae', 'watering': 'Alto', 'sunlight': ['Semisombra'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 6, 'temp_max': 26,
        'humidity_min': 60, 'watering_ml': 280,
        'description': 'Nativa que atrae picaflores, prefiere semisombra y riego frecuente.'
    },
    {
        'api_species_id': 'smartgarden-clavel', 'common_name': 'Clavel',
        'scientific_name': 'Dianthus caryophyllus', 'aliases': ['clavel'],
        'family': 'Caryophyllaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 28,
        'humidity_min': 40, 'watering_ml': 150,
        'description': 'Flor de corte de sol y sustrato drenante, evitando encharcamientos.'
    },
    {
        'api_species_id': 'smartgarden-espuela-galan', 'common_name': 'Espuela de Galán',
        'scientific_name': 'Tropaeolum majus', 'aliases': ['espuela de galan', 'capuchina'],
        'family': 'Tropaeolaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 28,
        'humidity_min': 30, 'watering_ml': 120,
        'description': 'Flor comestible de rápido crecimiento y bajo requerimiento hídrico.'
    },
    {
        'api_species_id': 'smartgarden-reina-luisa', 'common_name': 'Reina Luisa',
        'scientific_name': 'Callistephus chinensis', 'aliases': ['reina luisa', 'aster de china'],
        'family': 'Asteraceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 26,
        'humidity_min': 40, 'watering_ml': 150,
        'description': 'Ornamental de exterior para maceta, con floración estacional.'
    },
    # Arbustos y coberturas
    {
        'api_species_id': 'smartgarden-camelia', 'common_name': 'Camelia',
        'scientific_name': 'Camellia japonica', 'aliases': ['camelia'],
        'family': 'Theaceae', 'watering': 'Moderado', 'sunlight': ['Sombra luminosa'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 24,
        'humidity_min': 55, 'watering_ml': 250,
        'description': 'Arbusto floreciente de suelo ácido, protegido del sol de tarde.'
    },
    {
        'api_species_id': 'smartgarden-corona-inca', 'common_name': 'Corona del Inca',
        'scientific_name': 'Euphorbia pulcherrima', 'aliases': ['flor de pascua', 'nochebuena'],
        'family': 'Euphorbiaceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 12, 'temp_max': 28,
        'humidity_min': 40, 'watering_ml': 160,
        'description': 'Ornamental de invierno que requiere luz abundante y riego controlado.'
    },
    {
        'api_species_id': 'smartgarden-conejito', 'common_name': 'Conejito',
        'scientific_name': 'Antirrhinum majus', 'aliases': ['conejito', 'boca de dragon'],
        'family': 'Plantaginaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 5, 'temp_max': 28,
        'humidity_min': 40, 'watering_ml': 150,
        'description': 'Flor colorida y resistente, muy apropiada para jardines familiares.'
    },
    {
        'api_species_id': 'smartgarden-mio-mio', 'common_name': 'Mio-mio',
        'scientific_name': 'Myoporum laetum', 'aliases': ['mio mio', 'mioporo'],
        'family': 'Scrophulariaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 5, 'temp_max': 32,
        'humidity_min': 25, 'watering_ml': 140,
        'description': 'Arbusto perenne resistente al viento y adecuado para zonas costeras.'
    },
    {
        'api_species_id': 'smartgarden-jade', 'common_name': 'Árbol de Jade',
        'scientific_name': 'Crassula ovata', 'aliases': ['jade', 'planta de jade'],
        'family': 'Crassulaceae', 'watering': 'Bajo', 'sunlight': ['Sol', 'Semisombra'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 8, 'temp_max': 30,
        'humidity_min': 15, 'watering_ml': 70,
        'description': 'Suculenta de interior o terraza, tolerante a sequía y exceso de riego.'
    },
    {
        'api_species_id': 'smartgarden-veronica', 'common_name': 'Verónica',
        'scientific_name': 'Hebe speciosa', 'aliases': ['veronica', 'hebe'],
        'family': 'Plantaginaceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 6, 'temp_max': 28,
        'humidity_min': 40, 'watering_ml': 160,
        'description': 'Arbusto compacto para cerco vivo, con floración prolongada.'
    },
    {
        'api_species_id': 'smartgarden-abutilon', 'common_name': 'Abutilón o Farolito Chino',
        'scientific_name': 'Abutilon', 'aliases': ['abutilon', 'farolito chino'],
        'family': 'Malvaceae', 'watering': 'Moderado', 'sunlight': ['Sol de mañana'],
        'thumbnail': '/plants/lavanda2.jpg', 'temp_min': 8, 'temp_max': 30,
        'humidity_min': 45, 'watering_ml': 180,
        'description': 'Arbusto ornamental que atrae picaflores y prefiere luz filtrada.'
    },
    {
        'api_species_id': 'smartgarden-pitosporo', 'common_name': 'Pitosporo',
        'scientific_name': 'Pittosporum tobira', 'aliases': ['pitosporo'],
        'family': 'Pittosporaceae', 'watering': 'Moderado', 'sunlight': ['Sol', 'Sombra'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 5, 'temp_max': 32,
        'humidity_min': 30, 'watering_ml': 160,
        'description': 'Arbusto muy resistente, utilizado como cerco vivo y ornamental.'
    },
    {
        'api_species_id': 'smartgarden-cotoneaster', 'common_name': 'Cotoneaster',
        'scientific_name': 'Cotoneaster', 'aliases': ['cotoneaster'],
        'family': 'Rosaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 2, 'temp_max': 32,
        'humidity_min': 25, 'watering_ml': 130,
        'description': 'Arbusto resistente con bayas otoñales y buen desempeño como cobertura.'
    },
    # Árboles urbanos y ornamentales
    {
        'api_species_id': 'smartgarden-liquidambar', 'common_name': 'Liquidámbar',
        'scientific_name': 'Liquidambar styraciflua', 'aliases': ['liquidambar'],
        'family': 'Altingiaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': -5, 'temp_max': 32,
        'humidity_min': 40, 'watering_ml': 260,
        'description': 'Árbol caducifolio urbano, apreciado por sus colores de otoño.'
    },
    {
        'api_species_id': 'smartgarden-jacaranda', 'common_name': 'Jacarandá',
        'scientific_name': 'Jacaranda mimosifolia', 'aliases': ['jacaranda', 'jacarandá'],
        'family': 'Bignoniaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 2, 'temp_max': 34,
        'humidity_min': 30, 'watering_ml': 240,
        'description': 'Árbol urbano de floración primaveral, requiere espacio y sol.'
    },
    {
        'api_species_id': 'smartgarden-quillay', 'common_name': 'Quillay',
        'scientific_name': 'Quillaja saponaria', 'aliases': ['quillay'],
        'family': 'Quillajaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 0, 'temp_max': 36,
        'humidity_min': 20, 'watering_ml': 150,
        'description': 'Árbol nativo esclerófilo, resistente a sequía una vez establecido.'
    },
    {
        'api_species_id': 'smartgarden-peumo', 'common_name': 'Peumo',
        'scientific_name': 'Cryptocarya alba', 'aliases': ['peumo'],
        'family': 'Lauraceae', 'watering': 'Bajo', 'sunlight': ['Sol', 'Sombra'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 2, 'temp_max': 34,
        'humidity_min': 25, 'watering_ml': 170,
        'description': 'Árbol nativo perenne, adaptable y de follaje aromático.'
    },
    {
        'api_species_id': 'smartgarden-ciruelo-pissard', 'common_name': 'Ciruelo de Pissard',
        'scientific_name': "Prunus cerasifera 'Pissardii'", 'aliases': ['pissardii', 'ciruelo rojo'],
        'family': 'Rosaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/ciruelo.jpg', 'temp_min': -5, 'temp_max': 32,
        'humidity_min': 35, 'watering_ml': 220,
        'description': 'Árbol urbano de hoja morada, ornamental y de sol directo.'
    },
    {
        'api_species_id': 'smartgarden-maiten', 'common_name': 'Maitén',
        'scientific_name': 'Maytenus boaria', 'aliases': ['maiten', 'maitén'],
        'family': 'Celastraceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 0, 'temp_max': 32,
        'humidity_min': 35, 'watering_ml': 220,
        'description': 'Árbol nativo de copa elegante y ramas péndulas.'
    },
    {
        'api_species_id': 'smartgarden-arrayan', 'common_name': 'Arrayán',
        'scientific_name': 'Luma apiculata',
        'scientific_names': ['Luma apiculata', 'Myrceugenia apiculata', 'Myrtus luma'],
        'aliases': ['arrayan', 'arrayán'],
        'family': 'Myrtaceae', 'watering': 'Moderado', 'sunlight': ['Semisombra'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 2, 'temp_max': 28,
        'humidity_min': 50, 'watering_ml': 240,
        'description': 'Nativo de ambientes húmedos, reconocido por su tronco anaranjado.'
    },
    {
        'api_species_id': 'smartgarden-aromo', 'common_name': 'Aromo del País',
        'scientific_name': 'Acacia dealbata', 'aliases': ['aromo', 'mimosa'],
        'family': 'Fabaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': 0, 'temp_max': 34,
        'humidity_min': 25, 'watering_ml': 160,
        'description': 'Árbol de rápido crecimiento y flores amarillas perfumadas.'
    },
    {
        'api_species_id': 'smartgarden-palma-chilena', 'common_name': 'Palma Chilena',
        'scientific_name': 'Jubaea chilensis',
        'scientific_names': ['Jubaea chilensis', 'Molinaea chilensis'],
        'aliases': ['palma chilena', 'jubaea'],
        'family': 'Arecaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': -3, 'temp_max': 35,
        'humidity_min': 20, 'watering_ml': 150,
        'description': 'Palma nativa vulnerable, de crecimiento lento y muy resistente.'
    },
    # Hierbas aromáticas y medicinales
    {
        'api_species_id': 'smartgarden-cedron', 'common_name': 'Cedrón',
        'scientific_name': 'Aloysia citrodora',
        'scientific_names': ['Aloysia citrodora', 'Aloysia triphylla', 'Lippia citriodora'],
        'aliases': ['cedron', 'cedrón', 'hierba luisa'],
        'family': 'Verbenaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 5, 'temp_max': 32,
        'humidity_min': 35, 'watering_ml': 150,
        'description': 'Aromática de hojas cítricas, usada en infusiones y tolerante al sol.'
    },
    {
        'api_species_id': 'smartgarden-ruda', 'common_name': 'Ruda',
        'scientific_name': 'Ruta graveolens',
        'scientific_names': ['Ruta graveolens', 'Ruta chalepensis'],
        'aliases': ['ruda'],
        'family': 'Rutaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 4, 'temp_max': 35,
        'humidity_min': 25, 'watering_ml': 100,
        'description': 'Aromática tradicional de bajo riego y buena tolerancia al calor.'
    },
    {
        'api_species_id': 'smartgarden-boldo', 'common_name': 'Boldo',
        'scientific_name': 'Peumus boldus',
        'scientific_names': ['Peumus boldus', 'Boldu chilanum'],
        'aliases': ['boldo'],
        'family': 'Monimiaceae', 'watering': 'Bajo', 'sunlight': ['Sol', 'Sombra'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 2, 'temp_max': 32,
        'humidity_min': 25, 'watering_ml': 160,
        'description': 'Árbol nativo medicinal, de follaje aromático y tolerante a sequía.'
    },
    {
        'api_species_id': 'smartgarden-hierbabuena', 'common_name': 'Hierbabuena',
        'scientific_name': 'Mentha spicata', 'aliases': ['hierbabuena', 'menta verde'],
        'family': 'Lamiaceae', 'watering': 'Alto', 'sunlight': ['Semisombra'],
        'thumbnail': '/plants/menta.jpg', 'temp_min': 8, 'temp_max': 30,
        'humidity_min': 55, 'watering_ml': 180,
        'description': 'Aromática culinaria de crecimiento vigoroso, ideal para macetero.'
    },
    {
        'api_species_id': 'smartgarden-melisa', 'common_name': 'Melisa o Toronjil',
        'scientific_name': 'Melissa officinalis', 'aliases': ['melisa', 'toronjil', 'toronjil de la pena'],
        'family': 'Lamiaceae', 'watering': 'Moderado', 'sunlight': ['Semisombra'],
        'thumbnail': '/plants/menta.jpg', 'temp_min': 5, 'temp_max': 30,
        'humidity_min': 45, 'watering_ml': 150,
        'description': 'Hierba aromática relajante, agradece humedad moderada y luz filtrada.'
    },
    {
        'api_species_id': 'smartgarden-poleo', 'common_name': 'Poleo',
        'scientific_name': 'Mentha pulegium', 'aliases': ['poleo'],
        'family': 'Lamiaceae', 'watering': 'Alto', 'sunlight': ['Semisombra'],
        'thumbnail': '/plants/menta.jpg', 'temp_min': 6, 'temp_max': 30,
        'humidity_min': 55, 'watering_ml': 180,
        'description': 'Aromática digestiva que prefiere sustrato fresco y riego frecuente.'
    },
    {
        'api_species_id': 'smartgarden-bailahuen', 'common_name': 'Bailahuén',
        'scientific_name': 'Haplopappus', 'aliases': ['bailahuen', 'bailahuén'],
        'family': 'Asteraceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 0, 'temp_max': 32,
        'humidity_min': 20, 'watering_ml': 90,
        'description': 'Aromática nativa medicinal cordillerana, adaptada a condiciones secas.'
    },
]

ORNAMENTAL_PLANTS = {
    'smartgarden-hortensia', 'smartgarden-cardenal', 'smartgarden-bugambilia',
    'smartgarden-astromelia', 'smartgarden-pensamiento', 'smartgarden-dalia',
    'smartgarden-calendula', 'smartgarden-alheli', 'smartgarden-copihue',
    'smartgarden-chilco', 'smartgarden-clavel', 'smartgarden-espuela-galan',
    'smartgarden-reina-luisa', 'smartgarden-camelia', 'smartgarden-corona-inca',
    'smartgarden-conejito', 'smartgarden-abutilon',
}
SHRUB_PLANTS = {
    'smartgarden-mio-mio', 'smartgarden-jade', 'smartgarden-veronica',
    'smartgarden-pitosporo', 'smartgarden-cotoneaster',
}
TREE_PLANTS = {
    'smartgarden-liquidambar', 'smartgarden-jacaranda', 'smartgarden-quillay',
    'smartgarden-peumo', 'smartgarden-ciruelo-pissard', 'smartgarden-maiten',
    'smartgarden-arrayan', 'smartgarden-aromo', 'smartgarden-palma-chilena',
}
HERB_PLANTS = {
    'smartgarden-cedron', 'smartgarden-ruda', 'smartgarden-boldo',
    'smartgarden-hierbabuena', 'smartgarden-melisa', 'smartgarden-poleo',
    'smartgarden-bailahuen',
}


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


class TelemetryHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rango = request.query_params.get('range', '24h')
        horas = 24 if rango == '24h' else 168
        paso_horas = 1 if rango == '24h' else 6
        latest = self._latest_reading(request)
        base_temp = latest.temperatura if latest else 26.0
        base_hum = latest.humedad if latest else 52.0
        base_luz = latest.luz if latest else 70.0
        now = timezone.now()
        points = []

        for i in range(horas // paso_horas, -1, -1):
            timestamp = now - timedelta(hours=i * paso_horas)
            hour = timestamp.hour
            sunlight_factor = (
                max(0.0, math.sin((hour - 6) * math.pi / 12))
                if 6 <= hour <= 19 else 0.0
            )
            temperature = round(base_temp - 4.0 + sunlight_factor * 9.5 + math.sin(i * 0.8) * 1.5, 1)
            humidity = round(max(15.0, min(95.0, base_hum + 12.0 - sunlight_factor * 22.0 - (i * 0.4 % 18))), 1)
            light = round(max(0.0, min(100.0, sunlight_factor * 90.0 + (10 if sunlight_factor > 0 else 0))), 1)
            points.append({
                'timestamp': timestamp.isoformat(),
                'label': timestamp.strftime('%H:%M') if rango == '24h' else timestamp.strftime('%d/%m %H:00'),
                'temperatura': temperature,
                'humedadSuelo': humidity,
                'luzSolar': light,
                'estresTermico': temperature > 35.0,
                'estresHidrico': humidity < 30.0,
            })

        return Response({
            'rango': rango,
            'umbrales': {
                'temp_max': 35.0,
                'temp_min': 18.0,
                'humedad_optima': 60.0,
                'humedad_min': 30.0,
            },
            'historial': points,
        })

    @staticmethod
    def _latest_reading(request):
        return TelemetryLog.objects.filter(
            module__user=request.user
        ).order_by('-timestamp').first()


class PlantSearchProxy(APIView):
    """
    Endpoint Proxy para consultar la Free Plant API sin exponer la API Key en el cliente React.
    Uso: GET /api/plants/search/?q=monstera
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        normalized_query = self._normalize_search_text(query)

        if not query:
            return Response({
                'query': '',
                'count': len(CHILEAN_PLANT_CATALOG),
                'results': self._normalize_catalog(CHILEAN_PLANT_CATALOG),
            })

        catalog_matches = [
            item for item in CHILEAN_PLANT_CATALOG
            if normalized_query in self._normalize_search_text(item['common_name'])
            or normalized_query in self._normalize_search_text(item['scientific_name'])
            or any(
                normalized_query in self._normalize_search_text(alias)
                for alias in item.get('aliases', [])
            )
        ]
        if catalog_matches:
            return Response({
                'query': query,
                'count': len(catalog_matches),
                'results': self._normalize_catalog(catalog_matches),
            })

        try:
            # Petición segura de servidor a servidor inyectando la API Key desde settings.py
            search_queries = [query]
            normalized_alias = self._normalize_search_text(query)
            search_queries.extend(
                alias
                for alias in SPANISH_PLANT_SEARCH_ALIASES.get(normalized_alias, [])
                if alias.casefold() != normalized_alias
            )

            raw_data = {}
            for search_query in search_queries:
                external_response = requests.get(
                    settings.PLANT_API_BASE_URL,
                    params={
                        'key': settings.PLANT_API_KEY,
                        'q': search_query,
                    },
                    timeout=10
                )
                external_response.raise_for_status()
                candidate_data = external_response.json()
                candidate_items = candidate_data.get(
                    'data',
                    candidate_data if isinstance(candidate_data, list) else [],
                )
                if candidate_items:
                    raw_data = candidate_data
                    break

            # Normalización/limpieza del payload para el frontend
            raw_items = raw_data.get('data', raw_data if isinstance(raw_data, list) else [])
            cleaned_results = []
            for item in raw_items:
                raw_scientific = item.get('scientific_name')
                scientific_names_list = []
                if isinstance(raw_scientific, list):
                    for sn in raw_scientific:
                        cleaned = normalizeScientificName(sn)
                        if cleaned and cleaned not in scientific_names_list:
                            scientific_names_list.append(cleaned)
                elif isinstance(raw_scientific, str) and raw_scientific.strip():
                    cleaned = normalizeScientificName(raw_scientific)
                    if cleaned and cleaned not in scientific_names_list:
                        scientific_names_list.append(cleaned)

                scientific_name = scientific_names_list[0] if scientific_names_list else None

                default_image = item.get('default_image')
                fallback_url = (
                    default_image.get('thumbnail')
                    if isinstance(default_image, dict)
                    else None
                )

                # Sanitizar cualquier texto publicitario de planes de pago de Perenual o enlaces de suscripción
                cleaned_sunlight = []
                raw_sunlight = item.get('sunlight', [])
                banned_terms = ['upgrade', 'premium', 'supreme', 'perenual', 'subscription', 'http', 'api-documentation']
                if isinstance(raw_sunlight, list):
                    for s in raw_sunlight:
                        if isinstance(s, str) and not any(term in s.lower() for term in banned_terms):
                            cleaned_sunlight.append(s)
                elif isinstance(raw_sunlight, str) and not any(term in raw_sunlight.lower() for term in banned_terms):
                    cleaned_sunlight.append(raw_sunlight)

                if not cleaned_sunlight:
                    cleaned_sunlight = ['Luz indirecta o filtrada']

                cleaned_results.append({
                    'api_species_id': str(item.get('id')),
                    'common_name': item.get('common_name'),
                    'scientific_name': scientific_name,
                    'scientific_names': scientific_names_list,
                    'sunlight': cleaned_sunlight,
                    'thumbnail': resolvePlantImage(scientific_name, fallback_url),
                })

            return Response({'query': query, 'count': len(cleaned_results), 'results': cleaned_results})

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

    @staticmethod
    def _normalize_search_text(value):
        normalized = unicodedata.normalize('NFKD', str(value or ''))
        return ''.join(
            character for character in normalized
            if not unicodedata.combining(character)
        ).casefold().strip()

    @staticmethod
    def _normalize_catalog(items):
        results = []
        for item in items:
            raw_s = item.get('scientific_name')
            raw_list = item.get('scientific_names') or []
            names = []
            if isinstance(raw_list, list):
                for s in raw_list:
                    if isinstance(s, str) and s not in names:
                        names.append(s)
            if isinstance(raw_s, str) and raw_s not in names:
                names.insert(0, raw_s)

            for a in item.get('aliases', []):
                if a not in names and ' ' in a:
                    names.append(a)

            results.append({
                'api_species_id': item['api_species_id'],
                'common_name': item['common_name'],
                'scientific_name': names[0] if names else item.get('scientific_name'),
                'scientific_names': names if names else ([item.get('scientific_name')] if item.get('scientific_name') else []),
                'family': item['family'],
                'watering': item['watering'],
                'sunlight': item['sunlight'],
                'thumbnail': resolvePlantImage(item['scientific_name'], None),
                'temp_min': item['temp_min'],
                'temp_max': item['temp_max'],
                'humidity_min': item['humidity_min'],
                'watering_ml': item['watering_ml'],
                'description': item['description'],
                'aliases': item.get('aliases', []),
            })
        return results


FLORABOT_SYSTEM_PROMPT = """Eres FloraBot, el asistente botánico y agrónomo inteligente del ecosistema SmartGarden.
Tu misión es orientar y asesorar a los usuarios en el cuidado óptimo de sus plantas, resolviendo sus dudas de forma directa, práctica y precisa.

Reglas obligatorias de comportamiento y estilo:
1. Responde siempre en español con un tono cálido, empático, profesional y pedagógico.
2. Formato Markdown claro y limpio: negritas para términos importantes, viñetas cortas y párrafos concisos.
3. Resuelve TODO DIRECTAMENTE EN EL CHAT (sin derivaciones):
   - NUNCA inventes tutoriales del sistema ni menciones otras aplicaciones o páginas externas.
   - NUNCA digas frases como "abre la app", "ve al icono de lupa", "la plataforma autocompleta", ni inventes pasos mecánicos.
   - Toda la información y la solución deben entregarse de forma inmediata y autosuficiente dentro de este mismo chat.
4. Traductor botánico de nombres populares (Chile y Latinoamérica):
   - Si el usuario te pregunta de forma general sobre cómo buscar o traducir una planta chilena o común:
     * Respóndele de inmediato en el chat invitándolo a decirte la planta que busca, por ejemplo:
       "¡Con gusto te ayudo! Dime qué planta chilena estás buscando (por ejemplo: **boldo**, **palqui**, **copihue**, **maitén**, **palto**, **limón sutil**, etc.) y te daré al instante su nombre científico exacto y su término en inglés para que lo ingreses en el buscador."
   - Si el usuario te consulta por una planta popular específica (ej: boldo, palqui, maitén, copihue, etc.):
     * Entrega su **Nombre Científico** en cursiva (ej: *Peumus boldus*) y su **Nombre en Inglés** (ej: *Chilean boldo*).
     * Agrega una ficha compacta de 3 viñetas con sus requerimientos básicos: Riego (Bajo/Medio/Alto), Exposición solar y Rango térmico ideal.
     * Dile que con ese nombre científico puede buscarla directamente en el catálogo botánico de SmartGarden.
5. Asesor de condiciones óptimas de cultivo y maceta:
   - Si el usuario te pregunta por las condiciones óptimas, luz, temperatura, humedad del suelo, riego o sustrato para cualquier especie botánica:
     * Entrega una respuesta clara y estructurada con viñetas:
       - ☀️ **Luz solar / Exposición**: Nivel recomendado (sol directo, semisombra, luz indirecta filtrada).
       - 🌡️ **Rango de Temperatura Óptimo**: Mínima y máxima en °C.
       - 💧 **Humedad del Suelo y Riego**: Porcentaje de humedad mínima recomendada (ej: 30%-40%) y pauta de riego (abundante, moderado o escaso).
       - 🌱 **Sustrato y Drenaje**: Recomendación de tierra o mezcla para maceta.
     * Señala que puede ajustar estos parámetros exactos en el panel de su maceta inteligente en SmartGarden.
6. Diagnóstico diferencial de plagas y síntomas:
   - Si consultan por hojas amarillas, manchas o plagas, entrega causas posibles y pasos orgánicos inmediatos.
7. Presentación visual compacta:
   - Sé conciso y utiliza viñetas o tablas de máximo 3 columnas para evitar saturar la lectura en dispositivos móviles.
"""


class ChatbotAPIView(APIView):
    """
    Endpoint para FloraBot: Asistente Botánico Inteligente basado en Groq LLM.
    Permite responder dudas sobre cultivo, riego, diagnósticos de plagas y cuidado vegetal,
    aprovechando opcionalmente la telemetría en vivo de la planta monitoreada.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            from groq import Groq
        except ImportError:
            return Response(
                {'error': 'La biblioteca groq no está instalada en el entorno del servidor.', 'status': 'error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        api_key = os.getenv("GROQ_API_KEY") or getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            return Response(
                {'error': 'GROQ_API_KEY no está configurada en las variables de entorno.', 'status': 'error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response(
                {'error': 'No se proporcionó ningún mensaje.', 'status': 'error'},
                status=status.HTTP_400_BAD_REQUEST
            )

        history = request.data.get('history', [])
        plant_context = request.data.get('plant_context')
        fleet_context = request.data.get('fleet_context')

        # Construir el prompt de sistema enriquecido con telemetría/planta si está disponible
        system_content = FLORABOT_SYSTEM_PROMPT
        if plant_context and isinstance(plant_context, dict):
            context_lines = ["\n[Contexto actual de la maceta activa en SmartGarden]:"]
            if plant_context.get('name'):
                context_lines.append(f"- Planta activa: {plant_context.get('name')}")
            if plant_context.get('scientific_name'):
                context_lines.append(f"- Especie científica: {plant_context.get('scientific_name')}")
            if plant_context.get('soil_moisture') is not None:
                context_lines.append(f"- Humedad de suelo actual: {plant_context.get('soil_moisture')}%")
            if plant_context.get('temperature') is not None:
                context_lines.append(f"- Temperatura ambiental actual: {plant_context.get('temperature')}°C")
            if plant_context.get('humidity') is not None:
                context_lines.append(f"- Humedad ambiental: {plant_context.get('humidity')}%")
            if plant_context.get('light_lux') is not None:
                context_lines.append(f"- Iluminación: {plant_context.get('light_lux')}%")
            if plant_context.get('temp_min') is not None and plant_context.get('temp_max') is not None:
                context_lines.append(f"- Rango térmico seguro: {plant_context.get('temp_min')}°C a {plant_context.get('temp_max')}°C")
            if plant_context.get('humedad_min') is not None:
                context_lines.append(f"- Humedad mínima del sustrato recomendada: {plant_context.get('humedad_min')}%")
            context_lines.append("\nINSTRUCCIÓN CRÍTICA: El usuario tiene en pantalla su maceta y los sensores de telemetría IoT en tiempo real. Cuando consulte '¿cómo está mi planta?', 'estado de mi planta' o dudas sobre la maceta activa, diagnostica DIRECTAMENTE su condición actual usando estos valores reales y compáralos con las necesidades óptimas de la especie, sin pedirle que te vuelva a dar los datos.")
            system_content += "\n".join(context_lines)

        # Inyectar el inventario de TODAS las plantas de la sesión del usuario (Flota Completa)
        if fleet_context and isinstance(fleet_context, list) and len(fleet_context) > 0:
            fleet_lines = [f"\n[Cartelera de la flota completa del usuario ({len(fleet_context)} macetas registradas)]:"]
            for idx, p in enumerate(fleet_context, 1):
                p_name = p.get('name') or f"Planta #{idx}"
                p_spec = p.get('scientific_name') or "Especie botánica"
                p_sel = " (★ Seleccionada actualmente en pantalla)" if p.get('selected') else ""
                p_temp = f"{p.get('temperature')}°C" if p.get('temperature') is not None else "N/A"
                p_soil = f"{p.get('soil_moisture')}%" if p.get('soil_moisture') is not None else "N/A"
                p_light = f"{p.get('light_lux')}%" if p.get('light_lux') is not None else "N/A"
                p_min_h = f"{p.get('humedad_min')}%" if p.get('humedad_min') is not None else "30%"
                p_temp_range = f"{p.get('temp_min', 10)}°C a {p.get('temp_max', 35)}°C"
                p_health = p.get('health_label') or "Estado normal"
                p_issues = p.get('health_issues') or "Condiciones estables"

                fleet_lines.append(
                    f"{idx}. {p_name} ({p_spec}){p_sel}:\n"
                    f"   - Sensores en vivo: Temp: {p_temp} | Humedad Suelo: {p_soil} (Mínimo requerido: {p_min_h}) | Luz: {p_light}\n"
                    f"   - Rango térmico: {p_temp_range} | Diagnóstico de salud: {p_health} ({p_issues})"
                )

            fleet_lines.append(
                "\nINSTRUCCIONES DE ATENCIÓN DE FLOTA COMPLETA:\n"
                "1. Tienes visibilidad de TODAS las plantas registradas por el usuario con su telemetría viva individual.\n"
                "2. Si el usuario pregunta por 'todas mis plantas', 'resumen de mi jardín', 'cuál planta necesita agua o atención', o consultas globales:\n"
                "   - Entrega un informe panorámico claro y comparativo de cada planta de su flota.\n"
                "   - Prioriza las plantas que presenten alertas (humedad bajo el mínimo tolerable o temperatura fuera de rango).\n"
                "   - Indica claramente recomendaciones agronómicas específicas para cada una (por ejemplo: cuántos ml regar a la que lo requiera).\n"
                "3. Si el usuario pregunta por una planta en específico (por ejemplo: su 'limón', su 'olivo', su 'menta' o la seleccionada):\n"
                "   - Localiza esa planta en la lista de la flota, responde con precisión usando sus lecturas de sensores y dale recomendaciones exclusivas para esa especie.\n"
                "4. Utiliza viñetas destacadas o tablas compactas botánicas para que la respuesta sea ágil y ordenada."
            )
            system_content += "\n".join(fleet_lines)


        messages = [{"role": "system", "content": system_content}]

        # Incluir historial previo de conversación para dar memoria a la sesión (máx últimos 6 mensajes)
        if isinstance(history, list):
            for turn in history[-6:]:
                role = turn.get('role')
                content = turn.get('content')
                if role in ('user', 'assistant') and content:
                    messages.append({"role": role, "content": str(content)[:1000]})

        # Mensaje actual del usuario
        messages.append({"role": "user", "content": user_message})

        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.7,
                max_completion_tokens=2048,
                top_p=0.9,
                stream=False
            )
            response_text = completion.choices[0].message.content

            return Response({
                'response': response_text,
                'status': 'success'
            }, status=status.HTTP_200_OK)

        except Exception as groq_err:
            return Response({
                'error': f'Error en el servicio de inferencia: {str(groq_err)}',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

