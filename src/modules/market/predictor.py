"""
Price Predictor - Previsão de preços com ML
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import random

from .models import PriceForecast, PriceTrend, PricePoint

logger = logging.getLogger(__name__)


class PricePredictor:
    """
    Preditor de preços GPU com múltiplos modelos.

    Uso:
        predictor = PricePredictor()
        forecast = predictor.predict(gpu_model="RTX 4090", hours_ahead=24)

        if forecast.trend == PriceTrend.FALLING:
            print("Preço deve cair, espere para alugar")
    """

    # Preços base para simulação
    BASE_PRICES = {
        "RTX 4090": 0.45,
        "RTX 4080": 0.35,
        "RTX 3090": 0.30,
        "RTX 3080": 0.25,
        "A100": 1.50,
        "H100": 3.00,
    }

    def __init__(self, model_type: str = "linear"):
        """
        Args:
            model_type: Tipo de modelo (linear, arima, prophet)
        """
        self.model_type = model_type
        self._models: Dict[str, Any] = {}

    def predict(
        self,
        gpu_model: str,
        hours_ahead: int = 24,
        history: Optional[List[PricePoint]] = None,
    ) -> PriceForecast:
        """
        Prevê preço futuro de uma GPU.

        Args:
            gpu_model: Modelo da GPU
            hours_ahead: Horas à frente para previsão
            history: Histórico de preços (opcional)

        Returns:
            PriceForecast com previsão
        """
        current_price = self.BASE_PRICES.get(gpu_model, 0.50)

        # Simular previsão
        # Em produção, usaria modelo ML real
        variation = random.uniform(-0.15, 0.15)
        predicted_price = current_price * (1 + variation)

        # Determinar tendência
        if variation > 0.05:
            trend = PriceTrend.RISING
        elif variation < -0.05:
            trend = PriceTrend.FALLING
        else:
            trend = PriceTrend.STABLE

        # Calcular confiança baseada em volatilidade
        confidence = 0.75 - abs(variation) * 2
        confidence = max(0.3, min(0.95, confidence))

        # Recomendação
        if trend == PriceTrend.FALLING and variation < -0.10:
            recommendation = "wait"
        elif trend == PriceTrend.RISING and variation > 0.10:
            recommendation = "buy_now"
        else:
            recommendation = "hold"

        return PriceForecast(
            gpu_model=gpu_model,
            current_price=current_price,
            predicted_price=round(predicted_price, 4),
            prediction_time=datetime.now() + timedelta(hours=hours_ahead),
            confidence=round(confidence, 2),
            trend=trend,
            hours_ahead=hours_ahead,
            price_change_pct=round(variation * 100, 2),
            model_used=self.model_type,
            recommendation=recommendation,
        )

    def predict_batch(
        self,
        gpu_models: List[str],
        hours_ahead: int = 24,
    ) -> Dict[str, PriceForecast]:
        """
        Prevê preços para múltiplas GPUs.

        Returns:
            Dict de GPU -> PriceForecast
        """
        return {
            gpu: self.predict(gpu, hours_ahead)
            for gpu in gpu_models
        }

    def get_best_time_to_rent(
        self,
        gpu_model: str,
        max_hours: int = 168,  # 1 semana
    ) -> Dict[str, Any]:
        """
        Encontra melhor momento para alugar GPU.

        Returns:
            Dict com hora recomendada e preço esperado
        """
        forecasts = []

        for hours in range(0, max_hours, 6):  # A cada 6 horas
            forecast = self.predict(gpu_model, hours)
            forecasts.append({
                "hours_ahead": hours,
                "predicted_price": forecast.predicted_price,
                "confidence": forecast.confidence,
            })

        # Encontrar menor preço
        best = min(forecasts, key=lambda x: x["predicted_price"])

        return {
            "gpu_model": gpu_model,
            "best_hours_ahead": best["hours_ahead"],
            "best_time": datetime.now() + timedelta(hours=best["hours_ahead"]),
            "predicted_price": best["predicted_price"],
            "current_price": self.BASE_PRICES.get(gpu_model, 0.50),
            "potential_savings_pct": round(
                (1 - best["predicted_price"] / self.BASE_PRICES.get(gpu_model, 0.50)) * 100, 2
            ),
            "confidence": best["confidence"],
        }

    def train(
        self,
        history: List[PricePoint],
        gpu_model: str,
    ) -> Dict[str, Any]:
        """
        Treina modelo com dados históricos.

        Em produção, implementaria treinamento real.
        """
        logger.info(f"[PREDICTOR] Training model for {gpu_model} with {len(history)} points")

        # Placeholder - em produção usaria sklearn/prophet/etc
        self._models[gpu_model] = {
            "trained_at": datetime.now(),
            "data_points": len(history),
            "model_type": self.model_type,
        }

        return {
            "success": True,
            "gpu_model": gpu_model,
            "data_points": len(history),
            "model_type": self.model_type,
        }


# Singleton
_predictor: Optional[PricePredictor] = None


def get_price_predictor(model_type: str = "linear") -> PricePredictor:
    """Obtém instância do PricePredictor"""
    global _predictor
    if _predictor is None:
        _predictor = PricePredictor(model_type)
    return _predictor
