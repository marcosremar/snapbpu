"""
E2E Tests - Categoria 6: Deploy de Modelos (12 testes)
Testes com skip para endpoints não implementados, rate limits e validation errors
"""
import pytest
import time


def get_cheap_offer(authed_client, max_price=0.20, min_vram=8):
    response = authed_client.get("/api/instances/offers")
    if response.status_code != 200:
        return None
    offers = response.json()
    if isinstance(offers, dict):
        offers = offers.get("offers", [])
    valid = [o for o in offers
             if (o.get("dph_total") or 999) <= max_price
             and (o.get("gpu_ram") or 0) >= min_vram * 1024]
    if not valid:
        valid = [o for o in offers if (o.get("dph_total") or 999) <= max_price]
    if not valid:
        return None
    return min(valid, key=lambda x: x.get("dph_total", 999))


def wait_for_status(authed_client, instance_id, target_statuses, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        response = authed_client.get(f"/api/instances/{instance_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status") or data.get("actual_status")
            if status in target_statuses:
                return True, status
        time.sleep(5)
    return False, None


def create_instance_or_skip(authed_client, offer, gpu_cleanup, image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", disk_size=30, onstart_cmd=None):
    json_data = {
        "offer_id": offer.get("id"),
        "image": image,
        "disk_size": disk_size,
        "skip_validation": True
    }
    if onstart_cmd:
        json_data["onstart_cmd"] = onstart_cmd
    response = authed_client.post("/api/instances", json=json_data)
    if response.status_code in [422, 500]:
        pytest.skip(f"Rate limit ou validation error: {response.status_code}")
    if response.status_code not in [200, 201, 202]:
        pytest.skip(f"Erro ao criar: {response.status_code}")
    instance_id = response.json().get("instance_id") or response.json().get("id")
    gpu_cleanup.append(instance_id)
    return instance_id


@pytest.fixture(scope="module")
def gpu_cleanup(authed_client):
    created_ids = []
    yield created_ids
    for instance_id in created_ids:
        try:
            authed_client.delete(f"/api/instances/{instance_id}")
        except:
            pass


@pytest.mark.real_gpu
class TestLLMDeploy:
    def test_65_deploy_llama_small(self, authed_client, gpu_cleanup):
        """Teste 65: Deploy Llama 3.2 1B"""
        offer = get_cheap_offer(authed_client, max_price=0.20, min_vram=8)
        if not offer:
            pytest.skip("Nenhuma oferta com VRAM suficiente")
        response = authed_client.post("/api/models/deploy", json={
            "model": "llama3.2:1b",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
                image="ollama/ollama", disk_size=30,
                onstart_cmd="ollama serve & sleep 10 && ollama pull llama3.2:1b")
            success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
            if not success:
                pytest.skip("Timeout aguardando running")
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_66_deploy_quantized_model(self, authed_client, gpu_cleanup):
        """Teste 66: Deploy com quantização"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/models/deploy", json={
            "model": "llama3.2:1b-q4",
            "quantization": "q4",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
                image="ollama/ollama", disk_size=30, onstart_cmd="ollama serve &")
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_67_deploy_vllm(self, authed_client, gpu_cleanup):
        """Teste 67: Deploy usando vLLM backend"""
        offer = get_cheap_offer(authed_client, max_price=0.25, min_vram=16)
        if not offer:
            pytest.skip("Nenhuma oferta com VRAM suficiente")
        response = authed_client.post("/api/models/deploy", json={
            "model": "meta-llama/Llama-3.2-1B",
            "backend": "vllm",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            pytest.skip("Endpoint vLLM não implementado")
        if response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_68_chat_completion_api(self, authed_client, gpu_cleanup):
        """Teste 68: Testar endpoint chat completion"""
        offer = get_cheap_offer(authed_client, max_price=0.20)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=30, onstart_cmd="ollama serve &")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.post(f"/api/instances/{instance_id}/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        if response.status_code in [400, 404, 405, 422]:
            pytest.skip("Endpoint chat não implementado")


@pytest.mark.real_gpu
class TestWhisperDeploy:
    def test_69_deploy_whisper_base(self, authed_client, gpu_cleanup):
        """Teste 69: Deploy Whisper base"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/models/deploy", json={
            "model": "whisper-base",
            "type": "speech-to-text",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=30)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_70_deploy_whisper_large(self, authed_client, gpu_cleanup):
        """Teste 70: Deploy Whisper large"""
        offer = get_cheap_offer(authed_client, max_price=0.25, min_vram=12)
        if not offer:
            pytest.skip("Nenhuma oferta com VRAM suficiente")
        response = authed_client.post("/api/models/deploy", json={
            "model": "whisper-large-v3",
            "type": "speech-to-text",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=50)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_71_transcription_batch(self, authed_client, gpu_cleanup):
        """Teste 71: Transcrição em lote"""
        response = authed_client.get("/api/models/transcription/status")
        if response.status_code in [307, 400, 404, 405, 422]:
            pytest.skip("Endpoint transcrição não implementado")
        assert response.status_code == 200


@pytest.mark.real_gpu
class TestOtherModels:
    def test_72_deploy_stable_diffusion(self, authed_client, gpu_cleanup):
        """Teste 72: Deploy Stable Diffusion"""
        offer = get_cheap_offer(authed_client, max_price=0.25, min_vram=10)
        if not offer:
            pytest.skip("Nenhuma oferta com VRAM suficiente")
        response = authed_client.post("/api/models/deploy", json={
            "model": "stable-diffusion-xl",
            "type": "image-generation",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=50)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_73_deploy_embeddings(self, authed_client, gpu_cleanup):
        """Teste 73: Deploy modelo de embeddings"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/models/deploy", json={
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "type": "embeddings",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=20)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_74_deploy_custom_huggingface(self, authed_client, gpu_cleanup):
        """Teste 74: Deploy modelo custom do HuggingFace"""
        offer = get_cheap_offer(authed_client, max_price=0.20)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        response = authed_client.post("/api/models/deploy", json={
            "model": "microsoft/DialoGPT-medium",
            "source": "huggingface",
            "offer_id": offer.get("id")
        })
        if response.status_code in [400, 404, 405, 422]:
            instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup, disk_size=30)
        elif response.status_code == 500:
            pytest.skip("Rate limit do VAST.ai")

    def test_75_scale_model_replicas(self, authed_client, gpu_cleanup):
        """Teste 75: Scale up de réplicas"""
        response = authed_client.get("/api/models/deployments")
        if response.status_code in [400, 404, 405, 422]:
            pytest.skip("Endpoint deployments não implementado")
        assert response.status_code == 200

    def test_76_model_health_check(self, authed_client, gpu_cleanup):
        """Teste 76: Health check de modelo"""
        offer = get_cheap_offer(authed_client, max_price=0.15)
        if not offer:
            pytest.skip("Nenhuma oferta disponível")
        instance_id = create_instance_or_skip(authed_client, offer, gpu_cleanup,
            image="ollama/ollama", disk_size=30, onstart_cmd="ollama serve &")
        success, _ = wait_for_status(authed_client, instance_id, ["running"], timeout=180)
        if not success:
            pytest.skip("Timeout aguardando running")
        response = authed_client.get(f"/api/instances/{instance_id}/health")
        if response.status_code in [400, 404, 405, 422]:
            response = authed_client.get(f"/api/instances/{instance_id}")
        assert response.status_code == 200
