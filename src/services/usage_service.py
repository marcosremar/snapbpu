"""
Serviço para gerenciar registros de uso.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from src.models.usage import UsageRecord, GPUPricingReference

class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def start_usage(self, user_id: str, instance_id: str, gpu_type: str):
        """Inicia um novo registro de uso."""
        # Fecha registros abertos anteriores para a mesma instância (segurança)
        self.stop_usage(instance_id)
        
        record = UsageRecord(
            user_id=user_id,
            instance_id=instance_id,
            gpu_type=gpu_type,
            started_at=datetime.utcnow(),
            status="running"
        )
        self.db.add(record)
        self.db.commit()
        return record

    def stop_usage(self, instance_id: str):
        """Finaliza um registro de uso e calcula custos."""
        record = self.db.query(UsageRecord).filter(
            UsageRecord.instance_id == instance_id,
            UsageRecord.status == "running"
        ).first()
        
        if not record:
            return
        
        now = datetime.utcnow()
        record.ended_at = now
        record.status = "completed"
        
        duration = now - record.started_at
        duration_minutes = int(duration.total_seconds() / 60)
        record.duration_minutes = max(1, duration_minutes) # Mínimo 1 minuto
        
        # Buscar preços de referência
        ref = self.db.query(GPUPricingReference).filter(
            GPUPricingReference.gpu_type == record.gpu_type
        ).first()
        
        if ref:
            hours = record.duration_minutes / 60
            record.cost_dumont = hours * ref.dumont_hourly
            record.cost_aws_equivalent = hours * ref.aws_equivalent_hourly
            record.cost_gcp_equivalent = hours * ref.gcp_equivalent_hourly
            record.cost_azure_equivalent = hours * ref.azure_equivalent_hourly
        else:
            # Fallback se não encontrar a GPU na tabela de referência
            hours = record.duration_minutes / 60
            record.cost_dumont = hours * 0.40
            record.cost_aws_equivalent = hours * 4.0
            
        self.db.commit()

