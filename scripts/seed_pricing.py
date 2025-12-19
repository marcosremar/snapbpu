"""
Script para inicializar as tabelas de uso e popular preços de referência.
"""
import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import SessionLocal, engine, Base
from src.models.usage import GPUPricingReference, UsageRecord

def seed():
    # Cria as tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Dados iniciais de pricing baseados no markdown do plano
        pricing_data = [
            {
                "gpu_type": "RTX 3060",
                "vram_gb": 12,
                "dumont_hourly": 0.20,
                "aws_equivalent_hourly": 2.10,
                "gcp_equivalent_hourly": 1.89,
                "azure_equivalent_hourly": 2.05
            },
            {
                "gpu_type": "RTX 3090",
                "vram_gb": 24,
                "dumont_hourly": 0.25,
                "aws_equivalent_hourly": 2.10,
                "gcp_equivalent_hourly": 1.89,
                "azure_equivalent_hourly": 2.05
            },
            {
                "gpu_type": "RTX 4070",
                "vram_gb": 12,
                "dumont_hourly": 0.40,
                "aws_equivalent_hourly": 2.50,
                "gcp_equivalent_hourly": 2.20,
                "azure_equivalent_hourly": 2.40
            },
            {
                "gpu_type": "RTX 4090",
                "vram_gb": 24,
                "dumont_hourly": 0.44,
                "aws_equivalent_hourly": 4.10,
                "gcp_equivalent_hourly": 3.67,
                "azure_equivalent_hourly": 3.95
            },
            {
                "gpu_type": "A100 80GB",
                "vram_gb": 80,
                "dumont_hourly": 1.89,
                "aws_equivalent_hourly": 32.77,
                "gcp_equivalent_hourly": 29.13,
                "azure_equivalent_hourly": 27.20
            },
            {
                "gpu_type": "H100",
                "vram_gb": 80,
                "dumont_hourly": 2.49,
                "aws_equivalent_hourly": 65.00,
                "gcp_equivalent_hourly": 52.00,
                "azure_equivalent_hourly": 48.00
            }
        ]
        
        for data in pricing_data:
            # Verifica se já existe
            existing = db.query(GPUPricingReference).filter(GPUPricingReference.gpu_type == data["gpu_type"]).first()
            if existing:
                print(f"Atualizando {data['gpu_type']}...")
                existing.vram_gb = data["vram_gb"]
                existing.dumont_hourly = data["dumont_hourly"]
                existing.aws_equivalent_hourly = data["aws_equivalent_hourly"]
                existing.gcp_equivalent_hourly = data["gcp_equivalent_hourly"]
                existing.azure_equivalent_hourly = data["azure_equivalent_hourly"]
                existing.last_updated = datetime.utcnow()
            else:
                print(f"Criando {data['gpu_type']}...")
                new_ref = GPUPricingReference(**data)
                db.add(new_ref)
        
        db.commit()
        print("✅ Dados de pricing semeados com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao semear dados: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()

