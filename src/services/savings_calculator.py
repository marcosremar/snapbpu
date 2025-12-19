"""
Serviço para cálculo de economia do usuário.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.usage import UsageRecord, GPUPricingReference
from src.models.instance_status import HibernationEvent, InstanceStatus


class SavingsCalculator:
    def __init__(self, db: Session):
        self.db = db

    def calculate_user_savings(self, user_id: str, period: str = "month") -> Dict:
        """
        Calcula economia do usuário para o período especificado.
        """
        now = datetime.utcnow()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        elif period == "year":
            start_date = now - timedelta(days=365)
        else:  # default month
            start_date = now - timedelta(days=30)

        # 1. Total de uso (UsageRecords)
        usage_query = self.db.query(
            func.sum(UsageRecord.cost_dumont).label("total_dumont"),
            func.sum(UsageRecord.cost_aws_equivalent).label("total_aws"),
            func.sum(UsageRecord.cost_gcp_equivalent).label("total_gcp"),
            func.sum(UsageRecord.cost_azure_equivalent).label("total_azure"),
            func.sum(UsageRecord.duration_minutes).label("total_minutes")
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.started_at >= start_date
        ).first()

        total_dumont = usage_query.total_dumont or 0.0
        total_aws = usage_query.total_aws or 0.0
        total_gcp = usage_query.total_gcp or 0.0
        total_azure = usage_query.total_azure or 0.0
        total_minutes = usage_query.total_minutes or 0.0

        # 2. Economia por auto-hibernação (HibernationEvents)
        hibernation_savings = self.db.query(func.sum(HibernationEvent.savings_usd))\
            .join(InstanceStatus, InstanceStatus.instance_id == HibernationEvent.instance_id)\
            .filter(InstanceStatus.user_id == user_id)\
            .filter(HibernationEvent.timestamp >= start_date)\
            .scalar() or 0.0

        total_aws += hibernation_savings # AWS não tem auto-hibernação agressiva como a nossa
        
        avg_aws_savings = total_aws - total_dumont
        avg_gcp_savings = total_gcp - total_dumont
        avg_azure_savings = total_azure - total_dumont
        
        savings_percentage_avg = 0.0
        if total_aws > 0:
            savings_percentage_avg = (avg_aws_savings / total_aws) * 100

        return {
            "period": period,
            "total_hours": round(total_minutes / 60, 1),
            "total_cost_dumont": round(total_dumont, 2),
            "total_cost_aws": round(total_aws, 2),
            "total_cost_gcp": round(total_gcp, 2),
            "total_cost_azure": round(total_azure, 2),
            "savings_vs_aws": round(avg_aws_savings, 2),
            "savings_vs_gcp": round(avg_gcp_savings, 2),
            "savings_vs_azure": round(avg_azure_savings, 2),
            "savings_percentage_avg": round(savings_percentage_avg, 1),
            "auto_hibernate_savings": round(hibernation_savings, 2)
        }

    def get_realtime_comparison(self, gpu_type: str) -> Dict:
        """Retorna comparação em tempo real para uma GPU específica."""
        ref = self.db.query(GPUPricingReference).filter(GPUPricingReference.gpu_type == gpu_type).first()
        if not ref:
            return {}
        
        return {
            "gpu_type": ref.gpu_type,
            "dumont": ref.dumont_hourly,
            "aws": ref.aws_equivalent_hourly,
            "gcp": ref.gcp_equivalent_hourly,
            "azure": ref.azure_equivalent_hourly,
            "savings_vs_aws_percent": round((1 - ref.dumont_hourly / ref.aws_equivalent_hourly) * 100, 1) if ref.aws_equivalent_hourly > 0 else 0
        }

    def get_savings_history(self, user_id: str, months: int = 6) -> List[Dict]:
        """Retorna histórico de economia dos últimos N meses."""
        history = []
        now = datetime.utcnow()
        
        for i in range(months):
            month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            month_label = month_start.strftime("%b")
            
            usage = self.db.query(
                func.sum(UsageRecord.cost_dumont).label("dumont"),
                func.sum(UsageRecord.cost_aws_equivalent).label("aws")
            ).filter(
                UsageRecord.user_id == user_id,
                UsageRecord.started_at >= month_start,
                UsageRecord.started_at < month_end
            ).first()
            
            dumont = usage.dumont or 0.0
            aws = usage.aws or 0.0
            
            history.append({
                "month": month_label,
                "dumont": round(dumont, 2),
                "aws": round(aws, 2),
                "savings": round(aws - dumont, 2)
            })
            
        return history[::-1] # Retorna do mais antigo para o mais novo

    def get_savings_breakdown(self, user_id: str, period: str = "month") -> List[Dict]:
        """Retorna breakdown por GPU/máquina."""
        now = datetime.utcnow()
        if period == "day":
            start_date = now - timedelta(days=1)
        else:
            start_date = now - timedelta(days=30)
            
        breakdown = self.db.query(
            UsageRecord.gpu_type,
            func.sum(UsageRecord.duration_minutes).label("minutes"),
            func.sum(UsageRecord.cost_dumont).label("cost"),
            func.sum(UsageRecord.cost_aws_equivalent).label("aws")
        ).filter(
            UsageRecord.user_id == user_id,
            UsageRecord.started_at >= start_date
        ).group_by(UsageRecord.gpu_type).all()
        
        return [
            {
                "gpu": item.gpu_type,
                "hours": round(item.minutes / 60, 1),
                "cost": round(item.cost, 2),
                "aws": round(item.aws, 2),
                "savings": round(item.aws - item.cost, 2)
            }
            for item in breakdown
        ]

