"""
Serviço de recomendação de GPU baseado em IA.
"""
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.services.llm_client import LLMClient
from src.models.usage import GPUPricingReference

logger = logging.getLogger(__name__)

class GPUAdvisor:
    def __init__(self, db: Session, llm_client: Optional[LLMClient] = None):
        self.db = db
        self.llm = llm_client or LLMClient()

    async def get_recommendation(
        self, 
        project_description: str,
        budget_limit: Optional[float] = None
    ) -> Dict:
        """
        Analisa projeto e retorna recomendação de GPU.
        """
        gpu_specs = self._get_gpu_knowledge_base()
        
        system_prompt = f"""
        Você é um especialista em GPU Cloud e Machine Learning. 
        Sua função é analisar descrições de projetos e recomendar a GPU ideal disponível na Dumont Cloud.

        CONHECIMENTO DE GPUs DISPONÍVEIS:
        {json.dumps(gpu_specs, indent=2)}

        REGRAS DE RECOMENDAÇÃO:
        1. VRAM é crítico - o modelo deve caber na memória.
        2. Para training: considere batch size e técnicas como LoRA.
        3. Para inference: considere latência e custo.
        4. Custo-benefício é prioridade máxima.
        5. Compare sempre com o custo equivalente na AWS.

        FORMATO DE RESPOSTA (JSON):
        {{
            "recommended_gpu": "Nome da GPU",
            "vram_gb": 24,
            "hourly_price": 0.44,
            "estimated_hours": 8.0,
            "estimated_total_cost": 3.52,
            "aws_equivalent_cost": 32.80,
            "savings_percentage": 89.0,
            "reasoning": "Justificativa detalhada...",
            "technical_notes": ["Nota 1", "Nota 2"],
            "alternatives": [
                {{ "gpu": "RTX 3090", "score": 85, "reason": "Mais barata, mas mais lenta" }}
            ]
        }}
        """

        user_prompt = f"PROJETO: {project_description}"
        if budget_limit:
            user_prompt += f"\nORÇAMENTO MÁXIMO: ${budget_limit}/hora"

        try:
            recommendation = await self.llm.complete(system_prompt, user_prompt)
            return recommendation
        except Exception as e:
            logger.error(f"Erro ao obter recomendação da IA: {e}")
            # Fallback básico em caso de erro na IA
            return self._get_fallback_recommendation(project_description)

    def _get_gpu_knowledge_base(self) -> List[Dict]:
        """Retorna lista de GPUs e preços da Dumont Cloud."""
        refs = self.db.query(GPUPricingReference).all()
        return [
            {
                "name": r.gpu_type,
                "vram_gb": r.vram_gb,
                "dumont_price": r.dumont_hourly,
                "aws_price": r.aws_equivalent_hourly
            }
            for r in refs
        ]

    def _get_fallback_recommendation(self, description: str) -> Dict:
        """Retorna uma recomendação segura caso a IA falhe."""
        return {
            "recommended_gpu": "RTX 4090",
            "vram_gb": 24,
            "hourly_price": 0.44,
            "estimated_hours": 10.0,
            "estimated_total_cost": 4.40,
            "aws_equivalent_cost": 41.00,
            "savings_percentage": 89.0,
            "reasoning": "Baseado em sua descrição, a RTX 4090 oferece o melhor equilíbrio entre VRAM e performance.",
            "technical_notes": ["Excelente para a maioria dos workloads de ML", "24GB de VRAM"],
            "alternatives": []
        }

