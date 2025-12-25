"""
Savings Calculator - Cálculo de economia em GPU cloud
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from .models import SavingsReport

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Registro de uso de GPU"""
    gpu_model: str
    hours_used: float
    price_paid: float
    timestamp: datetime
    provider: str = "vast"
    spot: bool = True


class SavingsCalculator:
    """
    Calculador de economia em GPU cloud.

    Compara custos spot vs on-demand e calcula economia.

    Uso:
        calculator = SavingsCalculator()

        # Adicionar uso
        calculator.add_usage("RTX 4090", hours=10, price_paid=4.50)

        # Gerar relatório
        report = calculator.generate_report()
        print(f"Economia: ${report.savings_amount:.2f} ({report.savings_percentage:.1f}%)")
    """

    # Preços on-demand de referência (cloud providers tradicionais)
    ON_DEMAND_PRICES = {
        "RTX 4090": 2.00,   # ~$2/hr em cloud tradicional
        "RTX 4080": 1.50,
        "RTX 3090": 1.20,
        "RTX 3080": 1.00,
        "A100": 4.00,       # GCP ~$4/hr
        "H100": 8.00,       # ~$8/hr
    }

    # Preços spot médios
    SPOT_PRICES = {
        "RTX 4090": 0.45,
        "RTX 4080": 0.35,
        "RTX 3090": 0.30,
        "RTX 3080": 0.25,
        "A100": 1.50,
        "H100": 3.00,
    }

    def __init__(self):
        self._usage_records: List[UsageRecord] = []

    def add_usage(
        self,
        gpu_model: str,
        hours: float,
        price_paid: float,
        timestamp: Optional[datetime] = None,
        provider: str = "vast",
        spot: bool = True,
    ) -> None:
        """
        Registra uso de GPU.

        Args:
            gpu_model: Modelo da GPU
            hours: Horas de uso
            price_paid: Valor pago total
            timestamp: Momento do uso
            provider: Provedor usado
            spot: Se foi instância spot
        """
        self._usage_records.append(UsageRecord(
            gpu_model=gpu_model,
            hours_used=hours,
            price_paid=price_paid,
            timestamp=timestamp or datetime.now(),
            provider=provider,
            spot=spot,
        ))

    def generate_report(
        self,
        period_days: int = 30,
    ) -> SavingsReport:
        """
        Gera relatório de economia.

        Args:
            period_days: Período em dias para análise

        Returns:
            SavingsReport com detalhes de economia
        """
        cutoff = datetime.now() - timedelta(days=period_days)
        records = [r for r in self._usage_records if r.timestamp >= cutoff]

        if not records:
            return SavingsReport(
                period_start=cutoff,
                period_end=datetime.now(),
            )

        # Calcular custos
        actual_cost = sum(r.price_paid for r in records)

        # Calcular custo on-demand equivalente
        on_demand_cost = 0.0
        spot_cost = 0.0
        gpu_breakdown: Dict[str, Dict[str, float]] = {}

        for record in records:
            gpu = record.gpu_model
            on_demand_rate = self.ON_DEMAND_PRICES.get(gpu, 2.0)
            spot_rate = self.SPOT_PRICES.get(gpu, 0.50)

            gpu_on_demand = on_demand_rate * record.hours_used
            gpu_spot = spot_rate * record.hours_used

            on_demand_cost += gpu_on_demand
            spot_cost += gpu_spot

            if gpu not in gpu_breakdown:
                gpu_breakdown[gpu] = {
                    "hours": 0,
                    "actual_cost": 0,
                    "on_demand_cost": 0,
                    "spot_cost": 0,
                    "savings": 0,
                }

            gpu_breakdown[gpu]["hours"] += record.hours_used
            gpu_breakdown[gpu]["actual_cost"] += record.price_paid
            gpu_breakdown[gpu]["on_demand_cost"] += gpu_on_demand
            gpu_breakdown[gpu]["spot_cost"] += gpu_spot
            gpu_breakdown[gpu]["savings"] += gpu_on_demand - record.price_paid

        # Calcular economia
        savings_amount = on_demand_cost - actual_cost
        savings_percentage = (savings_amount / on_demand_cost * 100) if on_demand_cost > 0 else 0

        # Gerar dicas de otimização
        optimization_tips = self._generate_tips(records, gpu_breakdown)

        # Calcular economia potencial adicional
        potential_savings = self._calculate_potential_savings(records)

        return SavingsReport(
            period_start=cutoff,
            period_end=datetime.now(),
            on_demand_cost=round(on_demand_cost, 2),
            spot_cost=round(spot_cost, 2),
            actual_cost=round(actual_cost, 2),
            savings_amount=round(savings_amount, 2),
            savings_percentage=round(savings_percentage, 1),
            gpu_breakdown=gpu_breakdown,
            optimization_tips=optimization_tips,
            potential_savings=round(potential_savings, 2),
        )

    def _generate_tips(
        self,
        records: List[UsageRecord],
        breakdown: Dict[str, Dict[str, float]],
    ) -> List[str]:
        """Gera dicas de otimização"""
        tips = []

        # Verificar uso de GPUs caras
        for gpu, stats in breakdown.items():
            if gpu in ["H100", "A100"] and stats["hours"] > 10:
                tips.append(
                    f"Considere usar RTX 4090 para tarefas não-críticas em vez de {gpu} "
                    f"(economia potencial: ${stats['hours'] * 1.0:.2f})"
                )

        # Verificar padrões de uso
        total_hours = sum(r.hours_used for r in records)
        if total_hours > 100:
            tips.append(
                "Com alto volume de uso, considere reservar instâncias "
                "para desconto adicional de 20-30%"
            )

        # Verificar horários
        night_usage = sum(
            r.hours_used for r in records
            if r.timestamp.hour >= 22 or r.timestamp.hour < 6
        )
        if night_usage < total_hours * 0.2:
            tips.append(
                "Agende workloads para horários noturnos quando preços "
                "são tipicamente 15-20% mais baixos"
            )

        if not tips:
            tips.append("Seu uso está otimizado! Continue monitorando preços.")

        return tips

    def _calculate_potential_savings(self, records: List[UsageRecord]) -> float:
        """Calcula economia potencial adicional"""
        potential = 0.0

        for record in records:
            # Se pagou mais que spot médio, há potencial
            spot_rate = self.SPOT_PRICES.get(record.gpu_model, 0.50)
            optimal_cost = spot_rate * record.hours_used
            if record.price_paid > optimal_cost:
                potential += record.price_paid - optimal_cost

        return potential

    def compare_providers(
        self,
        gpu_model: str,
        hours: float,
    ) -> Dict[str, Any]:
        """
        Compara custos entre provedores.

        Returns:
            Dict com comparação de custos
        """
        on_demand = self.ON_DEMAND_PRICES.get(gpu_model, 2.0)
        spot = self.SPOT_PRICES.get(gpu_model, 0.50)

        return {
            "gpu_model": gpu_model,
            "hours": hours,
            "providers": {
                "vast_spot": {
                    "price_per_hour": spot,
                    "total_cost": round(spot * hours, 2),
                    "type": "spot",
                },
                "gcp_on_demand": {
                    "price_per_hour": on_demand,
                    "total_cost": round(on_demand * hours, 2),
                    "type": "on_demand",
                },
                "aws_on_demand": {
                    "price_per_hour": on_demand * 1.1,  # AWS tipicamente 10% mais caro
                    "total_cost": round(on_demand * 1.1 * hours, 2),
                    "type": "on_demand",
                },
            },
            "best_option": "vast_spot",
            "max_savings": round((on_demand * 1.1 - spot) * hours, 2),
            "savings_percentage": round((1 - spot / (on_demand * 1.1)) * 100, 1),
        }

    def get_monthly_summary(self) -> Dict[str, Any]:
        """Obtém resumo mensal de gastos"""
        report = self.generate_report(period_days=30)

        return {
            "period": "last_30_days",
            "total_spent": report.actual_cost,
            "would_have_spent": report.on_demand_cost,
            "savings": report.savings_amount,
            "savings_pct": report.savings_percentage,
            "top_gpus": sorted(
                report.gpu_breakdown.items(),
                key=lambda x: x[1]["hours"],
                reverse=True
            )[:3],
            "tips": report.optimization_tips,
        }


# Singleton
_calculator: Optional[SavingsCalculator] = None


def get_savings_calculator() -> SavingsCalculator:
    """Obtém instância do SavingsCalculator"""
    global _calculator
    if _calculator is None:
        _calculator = SavingsCalculator()
    return _calculator


def calculate_savings(
    gpu_model: str,
    hours: float,
    price_paid: float,
) -> Dict[str, Any]:
    """
    Calcula economia para um uso específico.

    Returns:
        Dict com economia calculada
    """
    on_demand = SavingsCalculator.ON_DEMAND_PRICES.get(gpu_model, 2.0)
    on_demand_cost = on_demand * hours
    savings = on_demand_cost - price_paid

    return {
        "gpu_model": gpu_model,
        "hours": hours,
        "price_paid": price_paid,
        "on_demand_cost": round(on_demand_cost, 2),
        "savings": round(savings, 2),
        "savings_pct": round(savings / on_demand_cost * 100, 1) if on_demand_cost > 0 else 0,
    }
