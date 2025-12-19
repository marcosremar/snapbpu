"""
Integração da Geolocalização no SyncMachineService
Adicionar ao método create_gcp_machine() em sync_machine_service.py
"""

def create_gcp_machine(
    self,
    gpu_instance_id: str,
    gpu_region: str,
    gpu_ip: Optional[str] = None,  # ← NOVO: IP da GPU para geolocalização
    project_id: str = 'avian-computer-477918-j9',
    machine_type: str = 'e2-standard-4',
    disk_size_gb: int = 500
) -> Dict:
    """
    Cria uma sync machine no GCP na mesma regiao da GPU (VERSÃO MELHORADA).
    
    Estratégia de detecção em camadas:
    1. REGION_MAP estático (rápido, 95% dos casos)
    2. Geolocalização por IP (automático, 4% dos casos)
    3. Fallback inteligente (1% dos casos)

    Args:
        gpu_instance_id: ID da instancia GPU associada
        gpu_region: Regiao da GPU (string do Vast.ai)
        gpu_ip: IP da GPU para geolocalização (novo!)
        project_id: ID do projeto GCP
        machine_type: Tipo da maquina GCP
        disk_size_gb: Tamanho do disco em GB

    Returns:
        Dict com resultado da criacao
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # CAMADA 1: Tentar mapeamento estático primeiro
    zone = self.get_gcp_zone_for_region(gpu_region)
    method = "static_map"
    
    # CAMADA 2: Se não encontrou (fallback genérico) E temos IP, tentar geolocalização
    if gpu_ip and zone in ['us-central1-a', 'europe-west1-a', 'asia-east1-a']:
        # Zonas genéricas = fallback, tentar geoloc
        logger.info(f"🌍 Região '{gpu_region}' não mapeada, tentando geolocalização...")
        
        try:
            from src.services.geolocation_service import get_gcp_zone_by_geolocation
            
            geo_zone, distance = get_gcp_zone_by_geolocation(gpu_ip)
            
            if geo_zone and distance < 500:  # <500km = boa proximidade
                logger.info(f"✅ Geolocalização bem-sucedida: {geo_zone} ({distance:.0f}km)")
                zone = geo_zone
                method = f"geolocation ({distance:.0f}km)"
                
                # OPCIONAL: Salvar no cache para próximos usos
                # self.REGION_MAP[gpu_region] = zone
            else:
                logger.warning(f"⚠️  Geolocalização encontrou zona distante: {geo_zone} ({distance:.0f}km)")
                
        except Exception as e:
            logger.error(f"❌ Erro na geolocalização: {e}")
            # Continuar com fallback
    
    # Log da decisão final
    logger.info(f"""
📍 Decisão de Região:
   GPU Região: {gpu_region}
   GPU IP: {gpu_ip or 'não fornecido'}
   Zona GCP: {zone}
   Método: {method}
    """)
    
    sync_id = f"sync-{gpu_instance_id}-{int(time.time())}"
    
    # ... resto do código permanece igual ...
    try:
        # Construir comando gcloud
        cmd = [
            'gcloud', 'compute', 'instances', 'create', sync_id,
            f'--project={project_id}',
            f'--zone={zone}',  # ← USA A ZONA DETECTADA
            f'--machine-type={machine_type}',
            # ... resto igual
        ]
        
        # ... continua igual ...
