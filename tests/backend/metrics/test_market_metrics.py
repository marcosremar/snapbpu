#!/usr/bin/env python3
"""
Testes Backend - Métricas de Mercado (Market Metrics)

Testa os endpoints reais de métricas de mercado do sistema Dumont Cloud:
- GET /api/v1/metrics/market - Lista snapshots do mercado
- GET /api/v1/metrics/market/summary - Resumo do mercado
- GET /api/v1/metrics/providers - Rankings de provedores
- GET /api/v1/metrics/efficiency - Rankings de eficiência
- GET /api/v1/metrics/predictions/{gpu_name} - Previsões de preço
- GET /api/v1/metrics/compare - Comparação de GPUs
- GET /api/v1/metrics/gpus - Lista de GPUs disponíveis
- GET /api/v1/metrics/types - Tipos de métricas

Uso:
    pytest tests/backend/metrics/test_market_metrics.py -v
    pytest tests/backend/metrics/test_market_metrics.py -v -k "test_market"
"""

import pytest
import time
from tests.backend.conftest import BaseTestCase, Colors


class TestMarketSnapshots(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/market - Market Snapshots"""

    def test_market_snapshots_basic(self, api_client):
        """GET /api/v1/metrics/market - Snapshots básicos"""
        resp = api_client.get("/api/v1/metrics/market")

        self.assert_success_response(resp, "Market snapshots básico")
        data = resp.json()

        # Deve retornar uma lista de snapshots
        assert isinstance(data, list), "Response deve ser uma lista"

        if data:
            snapshot = data[0]

            # Validar estrutura do snapshot
            required_keys = [
                "timestamp", "gpu_name", "machine_type",
                "min_price", "max_price", "avg_price", "median_price",
                "total_offers", "available_gpus", "verified_offers"
            ]

            for key in required_keys:
                assert key in snapshot, f"Chave '{key}' faltando no snapshot"

            # Validar tipos e valores
            assert isinstance(snapshot["gpu_name"], str)
            assert isinstance(snapshot["machine_type"], str)
            assert isinstance(snapshot["total_offers"], int)
            assert isinstance(snapshot["available_gpus"], int)

            # Preços devem ser positivos e lógicos
            assert snapshot["min_price"] >= 0, "Preço mínimo deve ser >= 0"
            assert snapshot["max_price"] >= snapshot["min_price"], "Preço máximo >= mínimo"
            assert snapshot["avg_price"] >= snapshot["min_price"], "Preço médio >= mínimo"
            assert snapshot["avg_price"] <= snapshot["max_price"], "Preço médio <= máximo"

            self.log_success(
                f"Snapshots: {len(data)} registros, GPU: {snapshot['gpu_name']}, "
                f"Avg: ${snapshot['avg_price']:.3f}/h"
            )
        else:
            self.log_info("Nenhum snapshot de mercado encontrado (banco vazio)")

    def test_market_snapshots_with_gpu_filter(self, api_client):
        """GET /api/v1/metrics/market - Filtro por GPU"""
        # Primeiro, pegar lista de GPUs disponíveis
        resp_gpus = api_client.get("/api/v1/metrics/gpus")

        if resp_gpus.status_code == 200 and resp_gpus.json():
            gpu_list = resp_gpus.json()
            test_gpu = gpu_list[0]

            # Testar filtro
            resp = api_client.get("/api/v1/metrics/market", params={"gpu_name": test_gpu})

            self.assert_success_response(resp, f"Snapshots filtrados por GPU: {test_gpu}")
            data = resp.json()

            assert isinstance(data, list)

            # Todos os resultados devem ser da GPU filtrada
            for snapshot in data:
                assert snapshot["gpu_name"] == test_gpu, f"GPU inválida: {snapshot['gpu_name']}"

            self.log_success(f"Filtro GPU '{test_gpu}': {len(data)} snapshots")
        else:
            self.log_info("Nenhuma GPU disponível para testar filtro")

    def test_market_snapshots_with_machine_type_filter(self, api_client):
        """GET /api/v1/metrics/market - Filtro por tipo de máquina"""
        machine_types = ["on-demand", "interruptible", "bid"]

        for machine_type in machine_types:
            resp = api_client.get("/api/v1/metrics/market", params={"machine_type": machine_type})

            self.assert_success_response(resp, f"Snapshots filtrados por tipo: {machine_type}")
            data = resp.json()

            assert isinstance(data, list)

            # Todos os resultados devem ser do tipo filtrado
            for snapshot in data:
                assert snapshot["machine_type"] == machine_type, \
                    f"Tipo inválido: {snapshot['machine_type']}"

            self.log_success(f"Filtro tipo '{machine_type}': {len(data)} snapshots")

    def test_market_snapshots_with_hours_limit(self, api_client):
        """GET /api/v1/metrics/market - Filtro por período (horas)"""
        hours_params = [1, 24, 72, 168]

        for hours in hours_params:
            resp = api_client.get("/api/v1/metrics/market", params={"hours": hours})

            self.assert_success_response(resp, f"Snapshots com período de {hours}h")
            data = resp.json()

            assert isinstance(data, list)
            self.log_success(f"Período {hours}h: {len(data)} snapshots")

    def test_market_snapshots_pagination(self, api_client):
        """GET /api/v1/metrics/market - Paginação com limit"""
        limits = [10, 50, 100]

        for limit in limits:
            resp = api_client.get("/api/v1/metrics/market", params={"limit": limit})

            self.assert_success_response(resp, f"Snapshots com limit={limit}")
            data = resp.json()

            assert isinstance(data, list)
            assert len(data) <= limit, f"Resultado excedeu limit: {len(data)} > {limit}"

            self.log_success(f"Limit {limit}: {len(data)} snapshots retornados")


class TestMarketSummary(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/market/summary - Market Summary"""

    def test_market_summary_all_gpus(self, api_client):
        """GET /api/v1/metrics/market/summary - Resumo de todas GPUs"""
        resp = api_client.get("/api/v1/metrics/market/summary")

        self.assert_success_response(resp, "Market summary (todas GPUs)")
        data = resp.json()

        # Validar estrutura
        assert "data" in data, "Chave 'data' faltando"
        assert "generated_at" in data, "Chave 'generated_at' faltando"
        assert isinstance(data["data"], dict), "'data' deve ser um dicionário"

        if data["data"]:
            # Pegar primeira GPU do resumo
            gpu_name = list(data["data"].keys())[0]
            gpu_data = data["data"][gpu_name]

            assert isinstance(gpu_data, dict), f"Dados da GPU '{gpu_name}' devem ser dict"

            # Validar tipos de máquina
            for machine_type, type_data in gpu_data.items():
                assert machine_type in ["on-demand", "interruptible", "bid"], \
                    f"Tipo de máquina inválido: {machine_type}"

                # Validar campos do resumo
                summary_keys = ["min_price", "max_price", "avg_price", "median_price",
                               "total_offers", "available_gpus", "last_update"]
                for key in summary_keys:
                    assert key in type_data, f"Chave '{key}' faltando no resumo"

            self.log_success(f"Summary: {len(data['data'])} GPUs, primeira: {gpu_name}")
        else:
            self.log_info("Nenhum dado de resumo encontrado (banco vazio)")

    def test_market_summary_specific_gpu(self, api_client):
        """GET /api/v1/metrics/market/summary - Resumo de GPU específica"""
        # Primeiro, pegar lista de GPUs
        resp_gpus = api_client.get("/api/v1/metrics/gpus")

        if resp_gpus.status_code == 200 and resp_gpus.json():
            gpu_list = resp_gpus.json()
            test_gpu = gpu_list[0]

            # Testar resumo da GPU específica
            resp = api_client.get("/api/v1/metrics/market/summary", params={"gpu_name": test_gpu})

            self.assert_success_response(resp, f"Market summary para GPU: {test_gpu}")
            data = resp.json()

            assert "data" in data

            if data["data"]:
                # Deve retornar apenas a GPU solicitada
                assert test_gpu in data["data"], f"GPU '{test_gpu}' não encontrada no resumo"
                assert len(data["data"]) == 1, "Deve retornar apenas 1 GPU"

                self.log_success(f"Summary específico para '{test_gpu}' OK")
            else:
                self.log_info(f"Nenhum dado para GPU '{test_gpu}'")
        else:
            self.log_info("Nenhuma GPU disponível para testar")

    def test_market_summary_with_machine_type_filter(self, api_client):
        """GET /api/v1/metrics/market/summary - Resumo filtrado por tipo de máquina"""
        machine_type = "on-demand"

        resp = api_client.get("/api/v1/metrics/market/summary", params={"machine_type": machine_type})

        self.assert_success_response(resp, f"Market summary tipo: {machine_type}")
        data = resp.json()

        if data.get("data"):
            # Verificar que apenas o tipo especificado está presente
            for gpu_name, gpu_data in data["data"].items():
                for mt in gpu_data.keys():
                    assert mt == machine_type, f"Tipo inesperado: {mt}"

            self.log_success(f"Summary filtrado por '{machine_type}' OK")
        else:
            self.log_info(f"Nenhum dado para tipo '{machine_type}'")


class TestProviderRankings(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/providers - Provider Rankings"""

    def test_provider_rankings_basic(self, api_client):
        """GET /api/v1/metrics/providers - Rankings básicos"""
        resp = api_client.get("/api/v1/metrics/providers")

        self.assert_success_response(resp, "Provider rankings básico")
        data = resp.json()

        assert isinstance(data, list), "Response deve ser uma lista"

        if data:
            provider = data[0]

            # Validar estrutura
            required_keys = [
                "machine_id", "reliability_score", "availability_score",
                "price_stability_score", "total_observations", "verified"
            ]

            for key in required_keys:
                assert key in provider, f"Chave '{key}' faltando no provider"

            # Validar scores (0 a 1)
            assert 0 <= provider["reliability_score"] <= 1, "Reliability score fora de faixa"
            assert 0 <= provider["availability_score"] <= 1, "Availability score fora de faixa"
            assert 0 <= provider["price_stability_score"] <= 1, "Price stability score fora de faixa"

            # Validar tipos
            assert isinstance(provider["machine_id"], int)
            assert isinstance(provider["verified"], bool)
            assert isinstance(provider["total_observations"], int)

            self.log_success(
                f"Provider rankings: {len(data)} providers, "
                f"Top reliability: {provider['reliability_score']:.3f}"
            )
        else:
            self.log_info("Nenhum provider encontrado (banco vazio)")

    def test_provider_rankings_with_filters(self, api_client):
        """GET /api/v1/metrics/providers - Rankings com filtros"""
        filters = [
            {"verified_only": True},
            {"min_observations": 10},
            {"min_reliability": 0.5},
            {"limit": 20},
        ]

        for filter_params in filters:
            resp = api_client.get("/api/v1/metrics/providers", params=filter_params)

            self.assert_success_response(resp, f"Providers com filtro: {filter_params}")
            data = resp.json()

            assert isinstance(data, list)

            # Validar filtros aplicados
            if data:
                for provider in data:
                    if "verified_only" in filter_params and filter_params["verified_only"]:
                        assert provider["verified"] == True, "Provider não verificado retornado"

                    if "min_observations" in filter_params:
                        assert provider["total_observations"] >= filter_params["min_observations"], \
                            f"Observations {provider['total_observations']} < {filter_params['min_observations']}"

                    if "min_reliability" in filter_params:
                        assert provider["reliability_score"] >= filter_params["min_reliability"], \
                            f"Reliability {provider['reliability_score']} < {filter_params['min_reliability']}"

                if "limit" in filter_params:
                    assert len(data) <= filter_params["limit"], \
                        f"Resultado excedeu limit: {len(data)} > {filter_params['limit']}"

            self.log_success(f"Filtro {filter_params}: {len(data)} providers")

    def test_provider_rankings_ordering(self, api_client):
        """GET /api/v1/metrics/providers - Ordenação"""
        order_by_options = ["reliability_score", "availability_score", "price_stability_score"]

        for order_by in order_by_options:
            resp = api_client.get("/api/v1/metrics/providers", params={"order_by": order_by, "limit": 10})

            self.assert_success_response(resp, f"Providers ordenados por: {order_by}")
            data = resp.json()

            if len(data) >= 2:
                # Verificar se está ordenado (descrescente)
                for i in range(len(data) - 1):
                    current = data[i].get(order_by, 0)
                    next_val = data[i + 1].get(order_by, 0)
                    assert current >= next_val, \
                        f"Ordenação incorreta: {current} < {next_val} em índice {i}"

                self.log_success(f"Ordenação por '{order_by}' verificada OK")
            else:
                self.log_info(f"Poucos dados para validar ordenação por '{order_by}'")


class TestEfficiencyRankings(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/efficiency - Efficiency Rankings"""

    def test_efficiency_rankings_basic(self, api_client):
        """GET /api/v1/metrics/efficiency - Rankings básicos"""
        resp = api_client.get("/api/v1/metrics/efficiency")

        self.assert_success_response(resp, "Efficiency rankings básico")
        data = resp.json()

        assert isinstance(data, list), "Response deve ser uma lista"

        if data:
            ranking = data[0]

            # Validar estrutura
            required_keys = [
                "rank", "offer_id", "gpu_name", "machine_type",
                "dph_total", "efficiency_score", "verified"
            ]

            for key in required_keys:
                assert key in ranking, f"Chave '{key}' faltando no ranking"

            # Validar valores
            assert ranking["rank"] >= 0, "Rank deve ser >= 0"
            assert 0 <= ranking["efficiency_score"] <= 100, "Efficiency score deve estar entre 0 e 100"
            assert ranking["dph_total"] >= 0, "Preço por hora deve ser >= 0"

            # Validar tipos
            assert isinstance(ranking["offer_id"], int)
            assert isinstance(ranking["gpu_name"], str)
            assert isinstance(ranking["verified"], bool)

            self.log_success(
                f"Efficiency rankings: {len(data)} ofertas, "
                f"Top: {ranking['gpu_name']} (score: {ranking['efficiency_score']:.1f})"
            )
        else:
            self.log_info("Nenhum ranking de eficiência encontrado (banco vazio)")

    def test_efficiency_rankings_with_filters(self, api_client):
        """GET /api/v1/metrics/efficiency - Rankings com filtros"""
        # Primeiro, pegar uma GPU disponível
        resp_gpus = api_client.get("/api/v1/metrics/gpus")

        if resp_gpus.status_code == 200 and resp_gpus.json():
            test_gpu = resp_gpus.json()[0]

            filters = [
                {"gpu_name": test_gpu},
                {"machine_type": "on-demand"},
                {"verified_only": True},
                {"max_price": 5.0},
                {"min_reliability": 0.5},
                {"limit": 20},
            ]

            for filter_params in filters:
                resp = api_client.get("/api/v1/metrics/efficiency", params=filter_params)

                self.assert_success_response(resp, f"Efficiency com filtro: {filter_params}")
                data = resp.json()

                assert isinstance(data, list)

                # Validar filtros
                if data:
                    for ranking in data:
                        if "gpu_name" in filter_params:
                            assert ranking["gpu_name"] == filter_params["gpu_name"]

                        if "machine_type" in filter_params:
                            assert ranking["machine_type"] == filter_params["machine_type"]

                        if "verified_only" in filter_params and filter_params["verified_only"]:
                            assert ranking["verified"] == True

                        if "max_price" in filter_params:
                            assert ranking["dph_total"] <= filter_params["max_price"]

                    if "limit" in filter_params:
                        assert len(data) <= filter_params["limit"]

                self.log_success(f"Filtro {filter_params}: {len(data)} resultados")
        else:
            self.log_info("Nenhuma GPU disponível para testar filtros")


class TestPricePredictions(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/predictions/{gpu_name} - Price Predictions"""

    def test_price_prediction_basic(self, api_client):
        """GET /api/v1/metrics/predictions/{gpu_name} - Previsão básica"""
        # Tentar com uma GPU comum
        test_gpus = ["RTX 4090", "RTX 3090", "A100"]

        found_prediction = False
        for gpu_name in test_gpus:
            resp = api_client.get(f"/api/v1/metrics/predictions/{gpu_name}")

            if resp.status_code == 200:
                data = resp.json()

                # Validar estrutura
                required_keys = [
                    "gpu_name", "machine_type", "hourly_predictions",
                    "daily_predictions", "best_hour_utc", "best_day",
                    "predicted_min_price", "model_confidence", "model_version"
                ]

                for key in required_keys:
                    assert key in data, f"Chave '{key}' faltando na prediction"

                # Validar tipos
                assert isinstance(data["hourly_predictions"], dict)
                assert isinstance(data["daily_predictions"], dict)
                assert 0 <= data["best_hour_utc"] <= 23, "best_hour_utc fora de faixa"
                assert 0 <= data["model_confidence"] <= 1, "model_confidence fora de faixa"

                self.log_success(
                    f"Previsão para '{gpu_name}': "
                    f"Melhor hora: {data['best_hour_utc']}h UTC, "
                    f"Confiança: {data['model_confidence']:.1%}"
                )
                found_prediction = True
                break
            elif resp.status_code == 404:
                self.log_info(f"Previsão não disponível para '{gpu_name}'")
            else:
                self.log_fail(f"Erro inesperado ao buscar previsão para '{gpu_name}': {resp.status_code}")

        if not found_prediction:
            self.log_info("Nenhuma previsão disponível (serviço ML não executado)")

    def test_price_prediction_with_machine_type(self, api_client):
        """GET /api/v1/metrics/predictions/{gpu_name} - Previsão por tipo de máquina"""
        test_gpu = "RTX 4090"
        machine_types = ["on-demand", "interruptible"]

        for machine_type in machine_types:
            resp = api_client.get(
                f"/api/v1/metrics/predictions/{test_gpu}",
                params={"machine_type": machine_type}
            )

            if resp.status_code == 200:
                data = resp.json()
                assert data["machine_type"] == machine_type
                self.log_success(f"Previsão '{test_gpu}' tipo '{machine_type}' OK")
            elif resp.status_code == 404:
                self.log_info(f"Previsão não disponível para '{test_gpu}' tipo '{machine_type}'")
            else:
                self.log_fail(f"Erro ao buscar previsão: {resp.status_code}")


class TestGpuComparison(BaseTestCase):
    """Testes para endpoint GET /api/v1/metrics/compare - GPU Comparison"""

    def test_gpu_comparison_basic(self, api_client):
        """GET /api/v1/metrics/compare - Comparação básica"""
        # Pegar GPUs disponíveis
        resp_gpus = api_client.get("/api/v1/metrics/gpus")

        if resp_gpus.status_code == 200 and len(resp_gpus.json()) >= 2:
            gpu_list = resp_gpus.json()[:3]  # Pegar até 3 GPUs
            gpus_param = ",".join(gpu_list)

            resp = api_client.get("/api/v1/metrics/compare", params={"gpus": gpus_param})

            self.assert_success_response(resp, "GPU comparison básico")
            data = resp.json()

            # Validar estrutura
            required_keys = ["machine_type", "gpus", "cheapest", "best_value", "generated_at"]
            for key in required_keys:
                assert key in data, f"Chave '{key}' faltando na comparison"

            # Validar lista de GPUs
            assert isinstance(data["gpus"], list)

            if data["gpus"]:
                for gpu in data["gpus"]:
                    gpu_keys = ["gpu_name", "avg_price", "min_price", "total_offers"]
                    for key in gpu_keys:
                        assert key in gpu, f"Chave '{key}' faltando no item da GPU"

                # Cheapest deve ser a GPU com menor avg_price
                if data["cheapest"]:
                    cheapest = data["cheapest"]
                    for gpu in data["gpus"]:
                        assert cheapest["avg_price"] <= gpu["avg_price"], \
                            f"Cheapest não é a mais barata: {cheapest['avg_price']} > {gpu['avg_price']}"

                self.log_success(
                    f"Comparação: {len(data['gpus'])} GPUs, "
                    f"Mais barata: {data['cheapest']['gpu_name'] if data['cheapest'] else 'N/A'}"
                )
            else:
                self.log_info("Nenhum dado de comparação disponível")
        else:
            self.log_info("Poucas GPUs disponíveis para comparação")

    def test_gpu_comparison_with_machine_type(self, api_client):
        """GET /api/v1/metrics/compare - Comparação por tipo de máquina"""
        resp_gpus = api_client.get("/api/v1/metrics/gpus")

        if resp_gpus.status_code == 200 and len(resp_gpus.json()) >= 2:
            gpu_list = resp_gpus.json()[:2]
            gpus_param = ",".join(gpu_list)

            for machine_type in ["on-demand", "interruptible"]:
                resp = api_client.get(
                    "/api/v1/metrics/compare",
                    params={"gpus": gpus_param, "machine_type": machine_type}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    assert data["machine_type"] == machine_type
                    self.log_success(f"Comparação tipo '{machine_type}': {len(data['gpus'])} GPUs")
                else:
                    self.log_info(f"Sem dados para comparação tipo '{machine_type}'")
        else:
            self.log_info("Poucas GPUs disponíveis para comparação")


class TestMetadataEndpoints(BaseTestCase):
    """Testes para endpoints de metadata - GPUs e Tipos"""

    def test_list_available_gpus(self, api_client):
        """GET /api/v1/metrics/gpus - Lista GPUs disponíveis"""
        resp = api_client.get("/api/v1/metrics/gpus")

        self.assert_success_response(resp, "Lista de GPUs")
        data = resp.json()

        assert isinstance(data, list), "Response deve ser uma lista"

        if data:
            # Todas devem ser strings
            for gpu in data:
                assert isinstance(gpu, str), f"GPU deve ser string: {type(gpu)}"

            # Lista deve estar ordenada
            assert data == sorted(data), "Lista de GPUs deve estar ordenada"

            self.log_success(f"GPUs disponíveis: {len(data)} ({', '.join(data[:5])}...)")
        else:
            self.log_info("Nenhuma GPU disponível (banco vazio)")

    def test_list_machine_types(self, api_client):
        """GET /api/v1/metrics/types - Lista tipos de máquina"""
        resp = api_client.get("/api/v1/metrics/types")

        self.assert_success_response(resp, "Lista de tipos de máquina")
        data = resp.json()

        assert isinstance(data, list), "Response deve ser uma lista"

        # Deve retornar os tipos padrão
        expected_types = ["on-demand", "interruptible", "bid"]
        for expected in expected_types:
            assert expected in data, f"Tipo '{expected}' faltando na lista"

        self.log_success(f"Tipos de máquina: {', '.join(data)}")


class TestSecurityAndValidation(BaseTestCase):
    """Testes de segurança e validação de entrada"""

    def test_metrics_unauthorized_access(self, unauth_client):
        """Testa acesso não autorizado aos endpoints de métricas"""
        endpoints = [
            "/api/v1/metrics/market",
            "/api/v1/metrics/market/summary",
            "/api/v1/metrics/providers",
            "/api/v1/metrics/efficiency",
            "/api/v1/metrics/gpus",
            "/api/v1/metrics/types",
        ]

        for endpoint in endpoints:
            resp = unauth_client.get(endpoint)

            # Deve retornar 401 (requer autenticação)
            assert resp.status_code == 401, \
                f"Endpoint {endpoint} deveria retornar 401, retornou {resp.status_code}"

        self.log_success("Todos os endpoints requerem autenticação corretamente")

    def test_market_snapshots_invalid_parameters(self, api_client):
        """Testa validação de parâmetros inválidos - Market Snapshots"""
        invalid_params = [
            {"hours": -1},           # Horas negativas
            {"hours": 200},          # Excede máximo (168)
            {"limit": 2000},         # Excede máximo (1000)
            {"limit": 0},            # Limite zero
        ]

        for params in invalid_params:
            resp = api_client.get("/api/v1/metrics/market", params=params)

            # Deve retornar erro de validação (422) ou usar valor padrão (200)
            assert resp.status_code in [200, 422], \
                f"Parâmetro inválido {params} retornou status inesperado: {resp.status_code}"

            if resp.status_code == 200:
                self.log_info(f"API usou valor padrão para parâmetro inválido: {params}")
            else:
                self.log_success(f"API rejeitou parâmetro inválido: {params}")

    def test_provider_rankings_invalid_filters(self, api_client):
        """Testa validação de filtros inválidos - Provider Rankings"""
        invalid_params = [
            {"min_reliability": 2.0},    # Maior que 1.0
            {"min_reliability": -0.5},   # Negativo
            {"limit": 500},              # Excede máximo (200)
        ]

        for params in invalid_params:
            resp = api_client.get("/api/v1/metrics/providers", params=params)

            assert resp.status_code in [200, 422], \
                f"Filtro inválido {params} retornou status inesperado: {resp.status_code}"

    def test_efficiency_rankings_invalid_filters(self, api_client):
        """Testa validação de filtros inválidos - Efficiency Rankings"""
        invalid_params = [
            {"max_price": -10.0},        # Preço negativo
            {"min_reliability": 1.5},    # Maior que 1.0
            {"limit": 300},              # Excede máximo (200)
        ]

        for params in invalid_params:
            resp = api_client.get("/api/v1/metrics/efficiency", params=params)

            assert resp.status_code in [200, 422], \
                f"Filtro inválido {params} retornou status inesperado: {resp.status_code}"

    def test_compare_missing_gpus_parameter(self, api_client):
        """Testa endpoint de comparação sem parâmetro obrigatório"""
        resp = api_client.get("/api/v1/metrics/compare")

        # Deve retornar erro 422 (parâmetro obrigatório faltando)
        assert resp.status_code == 422, \
            f"Deveria retornar 422 para parâmetro faltando, retornou {resp.status_code}"

        self.log_success("API rejeita comparação sem parâmetro 'gpus'")

    def test_prediction_invalid_gpu_name(self, api_client):
        """Testa previsão para GPU inexistente"""
        invalid_gpu = "GPU_INEXISTENTE_12345"

        resp = api_client.get(f"/api/v1/metrics/predictions/{invalid_gpu}")

        # Deve retornar 404 (não encontrado)
        assert resp.status_code == 404, \
            f"Deveria retornar 404 para GPU inexistente, retornou {resp.status_code}"

        self.log_success("API retorna 404 para GPU inexistente")


class TestPerformance(BaseTestCase):
    """Testes de performance básica"""

    def test_metrics_response_time(self, api_client):
        """Testa tempo de resposta dos endpoints principais"""
        endpoints = [
            "/api/v1/metrics/market",
            "/api/v1/metrics/market/summary",
            "/api/v1/metrics/providers",
            "/api/v1/metrics/efficiency",
            "/api/v1/metrics/gpus",
            "/api/v1/metrics/types",
        ]

        max_response_time = 3.0  # 3 segundos

        for endpoint in endpoints:
            start_time = time.time()
            resp = api_client.get(endpoint)
            response_time = time.time() - start_time

            self.assert_success_response(resp, f"Performance check: {endpoint}")

            # Verificar tempo de resposta
            if response_time > max_response_time:
                self.log_warning(
                    f"{endpoint} lento: {response_time:.2f}s (limite: {max_response_time}s)"
                )
            else:
                self.log_success(f"{endpoint}: {response_time:.3f}s")

    def test_market_snapshots_with_large_limit(self, api_client):
        """Testa performance com limite alto de resultados"""
        start_time = time.time()
        resp = api_client.get("/api/v1/metrics/market", params={"limit": 1000})
        response_time = time.time() - start_time

        self.assert_success_response(resp, "Market snapshots com limit=1000")

        data = resp.json()
        self.log_success(
            f"Large limit test: {len(data)} registros em {response_time:.2f}s"
        )

    def test_concurrent_requests_different_endpoints(self, api_client):
        """Testa requisições concorrentes em endpoints diferentes"""
        import threading
        import queue

        results = queue.Queue()

        def request_worker(endpoint):
            try:
                start = time.time()
                resp = api_client.get(endpoint)
                end = time.time()
                results.put({
                    "endpoint": endpoint,
                    "status": resp.status_code,
                    "time": end - start,
                    "success": resp.status_code == 200
                })
            except Exception as e:
                results.put({"endpoint": endpoint, "error": str(e), "success": False})

        endpoints = [
            "/api/v1/metrics/market",
            "/api/v1/metrics/providers",
            "/api/v1/metrics/efficiency",
            "/api/v1/metrics/gpus",
        ]

        # Criar e iniciar threads
        threads = []
        for endpoint in endpoints:
            t = threading.Thread(target=request_worker, args=(endpoint,))
            threads.append(t)
            t.start()

        # Aguardar conclusão
        for t in threads:
            t.join()

        # Analisar resultados
        success_count = 0
        total_time = 0

        while not results.empty():
            result = results.get()
            if result.get("success"):
                success_count += 1
                total_time += result["time"]

        assert success_count >= 3, \
            f"Muitas requisições concorrentes falharam: {success_count}/{len(endpoints)}"

        avg_time = total_time / success_count if success_count > 0 else 0
        self.log_success(
            f"Requisições concorrentes: {success_count}/{len(endpoints)} OK, "
            f"tempo médio: {avg_time:.2f}s"
        )


# Marcar resultados dos testes
TestMarketSnapshots._test_result = {
    "test_class": "TestMarketSnapshots",
    "timestamp": time.time(),
    "status": "completed"
}

TestMarketSummary._test_result = {
    "test_class": "TestMarketSummary",
    "timestamp": time.time(),
    "status": "completed"
}

TestProviderRankings._test_result = {
    "test_class": "TestProviderRankings",
    "timestamp": time.time(),
    "status": "completed"
}

TestEfficiencyRankings._test_result = {
    "test_class": "TestEfficiencyRankings",
    "timestamp": time.time(),
    "status": "completed"
}

TestPricePredictions._test_result = {
    "test_class": "TestPricePredictions",
    "timestamp": time.time(),
    "status": "completed"
}

TestGpuComparison._test_result = {
    "test_class": "TestGpuComparison",
    "timestamp": time.time(),
    "status": "completed"
}

TestMetadataEndpoints._test_result = {
    "test_class": "TestMetadataEndpoints",
    "timestamp": time.time(),
    "status": "completed"
}

TestSecurityAndValidation._test_result = {
    "test_class": "TestSecurityAndValidation",
    "timestamp": time.time(),
    "status": "completed"
}

TestPerformance._test_result = {
    "test_class": "TestPerformance",
    "timestamp": time.time(),
    "status": "completed"
}
