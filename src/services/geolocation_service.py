"""
FASE 2: Geolocalização Automática para Mapeamento de Regiões
Detecta a zona GCP mais próxima via coordenadas geográficas
"""

import requests
import math
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Coordenadas de todas as zonas GCP
GCP_ZONES_COORDINATES = {
    # AMERICAS
    'northamerica-northeast1-a': (45.5017, -73.5673),  # Montreal, Canada
    'northamerica-northeast2-a': (43.6532, -79.3832),  # Toronto, Canada
    'us-central1-a': (41.2619, -95.8608),  # Iowa, US
    'us-east1-a': (33.1960, -80.0131),  # South Carolina, US
    'us-east4-a': (37.4316, -78.6569),  # Virginia, US
    'us-east5-a': (39.0469, -77.4903),  # Ohio, US
    'us-south1-a': (32.7767, -96.7970),  # Dallas, Texas, US
    'us-west1-a': (45.6387, -121.1807),  # Oregon, US
    'us-west2-a': (34.0522, -118.2437),  # Los Angeles, US
    'us-west3-a': (43.8041, -111.7798),  # Utah, US
    'us-west4-a': (36.1699, -115.1398),  # Nevada, US
    'southamerica-east1-a': (-23.5505, -46.6333),  # São Paulo, Brazil
    'southamerica-west1-a': (-33.4489, -70.6693),  # Chile
    
    # EUROPE
    'europe-central2-a': (52.2297, 21.0122),  # Warsaw, Poland
    'europe-north1-a': (60.5693, 27.1878),  # Finland
    'europe-southwest1-a': (40.4168, -3.7038),  # Madrid, Spain
    'europe-west1-a': (50.4501, 3.8196),  # Belgium
    'europe-west2-a': (51.5074, -0.1278),  # London, UK
    'europe-west3-a': (50.1109, 8.6821),  # Frankfurt, Germany
    'europe-west4-a': (52.3676, 4.9041),  # Netherlands
    'europe-west6-a': (47.3769, 8.5417),  # Zurich, Switzerland
    'europe-west8-a': (45.4642, 9.1900),  # Milan, Italy
    'europe-west9-a': (48.8566, 2.3522),  # Paris, France
    'europe-west10-a': (52.5200, 13.4050),  # Berlin, Germany
    'europe-west12-a': (45.0781, 7.6761),  # Turin, Italy
    
    # ASIA
    'asia-east1-a': (24.0518, 120.5161),  # Taiwan
    'asia-east2-a': (22.3193, 114.1694),  # Hong Kong
    'asia-northeast1-a': (35.6762, 139.6503),  # Tokyo, Japan
    'asia-northeast2-a': (34.6937, 135.5023),  # Osaka, Japan
    'asia-northeast3-a': (37.5665, 126.9780),  # Seoul, South Korea
    'asia-south1-a': (19.0760, 72.8777),  # Mumbai, India
    'asia-south2-a': (28.7041, 77.1025),  # Delhi, India
    'asia-southeast1-a': (1.3521, 103.8198),  # Singapore
    'asia-southeast2-a': (-6.2088, 106.8456),  # Jakarta, Indonesia
    
    # OCEANIA
    'australia-southeast1-a': (-33.8688, 151.2093),  # Sydney, Australia
    'australia-southeast2-a': (-37.8136, 144.9631),  # Melbourne, Australia
    
    # MIDDLE EAST
    'me-central1-a': (25.2048, 55.2708),  # Dubai, UAE
    'me-west1-a': (32.0853, 34.7818),  # Tel Aviv, Israel
}


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calcula distância em km entre dois pontos usando fórmula de Haversine.
    
    Args:
        lat1, lng1: Coordenadas do ponto 1
        lat2, lng2: Coordenadas do ponto 2
        
    Returns:
        Distância em quilômetros
    """
    R = 6371  # Raio da Terra em km
    
    # Converter para radianos
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Diferenças
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    # Fórmula de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def get_coordinates_from_ip(ip_address: str) -> Optional[Tuple[float, float]]:
    """
    Obtém coordenadas geográficas a partir de IP.
    
    Args:
        ip_address: Endereço IP da GPU
        
    Returns:
        Tupla (latitude, longitude) ou None se falhar
    """
    try:
        # Usar ipinfo.io (grátis até 50k requests/mês)
        response = requests.get(
            f'https://ipinfo.io/{ip_address}/json',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'loc' in data:
                # loc format: "latitude,longitude"
                lat, lng = map(float, data['loc'].split(','))
                
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                country = data.get('country', 'Unknown')
                
                logger.info(f"📍 IP {ip_address} → {city}, {region}, {country} ({lat}, {lng})")
                
                return (lat, lng)
        
        logger.warning(f"⚠️  Falha ao obter localização do IP {ip_address}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao consultar geolocalização: {e}")
        return None


def find_closest_gcp_zone(lat: float, lng: float, max_distance_km: int = 10000) -> Tuple[Optional[str], float]:
    """
    Encontra a zona GCP mais próxima das coordenadas dadas.
    
    Args:
        lat: Latitude
        lng: Longitude
        max_distance_km: Distância máxima aceitável (default: 10000km)
        
    Returns:
        Tupla (zona, distância_km) ou (None, inf) se não encontrar
    """
    closest_zone = None
    min_distance = float('inf')
    
    for zone, (zone_lat, zone_lng) in GCP_ZONES_COORDINATES.items():
        distance = haversine_distance(lat, lng, zone_lat, zone_lng)
        
        if distance < min_distance:
            min_distance = distance
            closest_zone = zone
    
    if min_distance > max_distance_km:
        logger.warning(f"⚠️  Zona mais próxima está a {min_distance:.0f}km (limite: {max_distance_km}km)")
        return (None, min_distance)
    
    logger.info(f"✅ Zona mais próxima: {closest_zone} ({min_distance:.0f}km)")
    
    return (closest_zone, min_distance)


def get_gcp_zone_by_geolocation(ip_address: str) -> Tuple[Optional[str], float]:
    """
    Detecta zona GCP mais próxima usando geolocalização por IP.
    
    Esta é a CAMADA 2 do sistema de mapeamento.
    Usa quando REGION_MAP não tem a região.
    
    Args:
        ip_address: IP da GPU
        
    Returns:
        Tupla (zona, distância_km) ou (None, inf) se falhar
    """
    logger.info(f"🌍 Iniciando geolocalização para IP {ip_address}")
    
    # 1. Obter coordenadas do IP
    coords = get_coordinates_from_ip(ip_address)
    
    if not coords:
        logger.error("❌ Falha ao obter coordenadas")
        return (None, float('inf'))
    
    lat, lng = coords
    
    # 2. Encontrar zona GCP mais próxima
    zone, distance = find_closest_gcp_zone(lat, lng)
    
    if zone:
        logger.info(f"✅ Geolocalização: IP {ip_address} → {zone} ({distance:.0f}km)")
    else:
        logger.error(f"❌ Nenhuma zona GCP encontrada próxima")
    
    return (zone, distance)


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Testar com IP de Montreal
    test_ip = "142.44.215.177"  # Exemplo: IP do Quebec
    
    zone, distance = get_gcp_zone_by_geolocation(test_ip)
    
    if zone:
        print(f"\n✅ Resultado:")
        print(f"   IP: {test_ip}")
        print(f"   Zona GCP: {zone}")
        print(f"   Distância: {distance:.0f}km")
    else:
        print(f"\n❌ Falha ao detectar zona")
