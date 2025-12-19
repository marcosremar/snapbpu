"""
Versão melhorada do get_gcp_zone_for_region
Para substituir em sync_machine_service.py linha 225-237
"""

def get_gcp_zone_for_region(self, vast_region: str) -> str:
    """
    Mapeia regiao vast.ai para zona GCP (VERSÃO MELHORADA).
    
    Estratégia de matching em camadas:
    1. Match exato (case-sensitive)
    2. Match exato (case-insensitive)
    3. Match parcial por substring
    4. Match por partes (ex: "Montreal, QC, CA" → tenta cada parte)
    5. Fallback inteligente com warning
    
    Args:
        vast_region: Região reportada pelo Vast.ai
        
    Returns:
        Zona GCP mais apropriada
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not vast_region:
        logger.warning("⚠️  Região vazia! Usando fallback: us-central1-a")
        return 'us-central1-a'
    
    # Limpar espaços extras
    vast_region = vast_region.strip()
    
    # CAMADA 1: Match exato (case-sensitive)
    if vast_region in self.REGION_MAP:
        zone = self.REGION_MAP[vast_region]
        logger.info(f"✅ Match exato: '{vast_region}' → {zone}")
        return zone
    
    # CAMADA 2: Match exato (case-insensitive)  
    vast_lower = vast_region.lower()
    for key, zone in self.REGION_MAP.items():
        if key.lower() == vast_lower:
            logger.info(f"✅ Match case-insensitive: '{vast_region}' → {zone} (via '{key}')")
            return zone
    
    # CAMADA 3: Match parcial por substring (mais específico primeiro)
    # Ordena por tamanho decrescente para pegar match mais específico
    sorted_keys = sorted(self.REGION_MAP.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        key_lower = key.lower()
        # Verifica se a chave está contida na região ou vice-versa
        if (key_lower in vast_lower or vast_lower in key_lower) and len(key) > 2:
            zone = self.REGION_MAP[key]
            logger.info(f"✅ Match parcial: '{vast_region}' → {zone} (via '{key}')")
            return zone
    
    # CAMADA 4: Match por partes (ex: "Montreal, QC, CA" → ["Montreal", "QC", "CA"])
    if ',' in vast_region:
        parts = [p.strip() for p in vast_region.split(',')]
        # Tentar cada parte, da mais específica para menos
        for part in parts:
            part_lower = part.lower()
            for key, zone in self.REGION_MAP.items():
                if key.lower() == part_lower or (part_lower in key.lower() and len(part) > 2):
                    logger.info(f"✅ Match por parte: '{vast_region}' (parte '{part}') → {zone} (via '{key}')")
                    return zone
    
    # CAMADA 5: Fallback inteligente com warning
    # Tentar detectar continente pelo menos
    fallback_zone = 'us-central1-a'  # Default global
    
    if any(x in vast_lower for x in ['eu', 'europe', 'uk', 'gb', 'de', 'fr', 'nl', 'be', 'pl', 'fi']):
        fallback_zone = 'europe-west1-a'
        logger.warning(f"⚠️  Região desconhecida '{vast_region}', detectado Europa → {fallback_zone}")
    elif any(x in vast_lower for x in ['asia', 'jp', 'cn', 'sg', 'tw', 'hk', 'kr', 'in']):
        fallback_zone = 'asia-east1-a'
        logger.warning(f"⚠️  Região desconhecida '{vast_region}', detectado Ásia → {fallback_zone}")
    elif any(x in vast_lower for x in ['au', 'australia', 'nz', 'oceania']):
        fallback_zone = 'australia-southeast1-a'
        logger.warning(f"⚠️  Região desconhecida '{vast_region}', detectado Oceania → {fallback_zone}")
    elif any(x in vast_lower for x in ['ca', 'canada', 'canadian']):
        fallback_zone = 'northamerica-northeast1-a'
        logger.warning(f"⚠️  Região desconhecida '{vast_region}', detectado Canadá → {fallback_zone}")
    elif any(x in vast_lower for x in ['br', 'brazil', 'latam', 'south america']):
        fallback_zone = 'southamerica-east1-a'
        logger.warning(f"⚠️  Região desconhecida '{vast_region}', detectado América do Sul → {fallback_zone}")
    else:
        logger.warning(f"⚠️  REGIÃO NÃO MAPEADA: '{vast_region}' → Usando {fallback_zone}")
    
    return fallback_zone
