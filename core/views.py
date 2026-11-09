import requests
import math
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
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


CHILEAN_PLANT_CATALOG = [
    {
        'api_species_id': 'smartgarden-limonero',
        'common_name': 'Limonero en maceta',
        'scientific_name': 'Citrus limon',
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
        'thumbnail': '/plants/olivo.jpg', 'temp_min': -5, 'temp_max': 32,
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
        'scientific_name': 'Luma apiculata', 'aliases': ['arrayan', 'arrayán'],
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
        'scientific_name': 'Jubaea chilensis', 'aliases': ['palma chilena', 'jubaea'],
        'family': 'Arecaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/olivo.jpg', 'temp_min': -3, 'temp_max': 35,
        'humidity_min': 20, 'watering_ml': 150,
        'description': 'Palma nativa vulnerable, de crecimiento lento y muy resistente.'
    },
    # Hierbas aromáticas y medicinales
    {
        'api_species_id': 'smartgarden-cedron', 'common_name': 'Cedrón',
        'scientific_name': 'Aloysia citrodora', 'aliases': ['cedron', 'cedrón', 'hierba luisa'],
        'family': 'Verbenaceae', 'watering': 'Moderado', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 5, 'temp_max': 32,
        'humidity_min': 35, 'watering_ml': 150,
        'description': 'Aromática de hojas cítricas, usada en infusiones y tolerante al sol.'
    },
    {
        'api_species_id': 'smartgarden-ruda', 'common_name': 'Ruda',
        'scientific_name': 'Ruta graveolens', 'aliases': ['ruda'],
        'family': 'Rutaceae', 'watering': 'Bajo', 'sunlight': ['Sol pleno'],
        'thumbnail': '/plants/romero.jpg', 'temp_min': 4, 'temp_max': 35,
        'humidity_min': 25, 'watering_ml': 100,
        'description': 'Aromática tradicional de bajo riego y buena tolerancia al calor.'
    },
    {
        'api_species_id': 'smartgarden-boldo', 'common_name': 'Boldo',
        'scientific_name': 'Peumus boldus', 'aliases': ['boldo'],
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

        if not query:
            return Response({
                'query': '',
                'count': len(CHILEAN_PLANT_CATALOG),
                'results': self._normalize_catalog(CHILEAN_PLANT_CATALOG),
            })

        catalog_matches = [
            item for item in CHILEAN_PLANT_CATALOG
            if query.casefold() in item['common_name'].casefold()
            or query.casefold() in item['scientific_name'].casefold()
            or any(query.casefold() in alias.casefold() for alias in item.get('aliases', []))
        ]
        if catalog_matches:
            return Response({
                'query': query,
                'count': len(catalog_matches),
                'results': self._normalize_catalog(catalog_matches),
            })

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
    def _normalize_catalog(items):
        return [
            {
                'api_species_id': item['api_species_id'],
                'common_name': item['common_name'],
                'scientific_name': item['scientific_name'],
                'family': item['family'],
                'watering': item['watering'],
                'sunlight': item['sunlight'],
                'thumbnail': (
                    '/plants/ornamental.svg' if item['api_species_id'] in ORNAMENTAL_PLANTS
                    else '/plants/shrub.svg' if item['api_species_id'] in SHRUB_PLANTS
                    else '/plants/tree.svg' if item['api_species_id'] in TREE_PLANTS
                    else '/plants/herb.svg' if item['api_species_id'] in HERB_PLANTS
                    else item['thumbnail']
                ),
                'temp_min': item['temp_min'],
                'temp_max': item['temp_max'],
                'humidity_min': item['humidity_min'],
                'watering_ml': item['watering_ml'],
                'description': item['description'],
                'aliases': item.get('aliases', []),
            }
            for item in items
        ]
