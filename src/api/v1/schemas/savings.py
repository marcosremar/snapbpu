"""Schemas para o Dashboard de Economia."""

from pydantic import BaseModel
from typing import List, Optional


class SavingsSummaryResponse(BaseModel):
    period: str
    total_hours: float
    total_cost_dumont: float
    total_cost_aws: float
    total_cost_gcp: float
    total_cost_azure: float
    savings_vs_aws: float
    savings_vs_gcp: float
    savings_vs_azure: float
    savings_percentage_avg: float
    auto_hibernate_savings: float


class SavingsHistoryItem(BaseModel):
    month: str
    dumont: float
    aws: float
    savings: float


class SavingsHistoryResponse(BaseModel):
    history: List[SavingsHistoryItem]


class SavingsBreakdownItem(BaseModel):
    gpu: str
    hours: float
    cost: float
    aws: float
    savings: float


class SavingsBreakdownResponse(BaseModel):
    breakdown: List[SavingsBreakdownItem]


class GPUPriceComparisonResponse(BaseModel):
    gpu_type: str
    dumont: float
    aws: float
    gcp: float
    azure: float
    savings_vs_aws_percent: float

