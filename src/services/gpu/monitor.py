#!/usr/bin/env python3
"""
GPU Monitor Agent - Roda DENTRO da instância GPU

Este agente monitora o uso da GPU e envia status para o servidor de controle (VPS).
Deve ser instalado e executado em cada instância GPU vast.ai.

Uso:
    python3 gpu_monitor_agent.py --instance-id 12345 --control-url https://dumontcloud.com

Envia status a cada 30 segundos:
    POST /api/agent/status
    {
        "instance_id": "12345",
        "gpu_utilization": 2.5,
        "timestamp": "2025-12-17T10:30:00Z",
        "gpu_count": 1,
        "gpu_names": ["NVIDIA GeForce RTX 3090"]
    }
"""

import subprocess
import time
import requests
import logging
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class GPUMonitorAgent:
    """Agente que monitora uso da GPU e reporta para o servidor de controle."""

    def __init__(
        self,
        instance_id: str,
        control_plane_url: str,
        check_interval: int = 30,
        auth_token: Optional[str] = None
    ):
        """
        Inicializa o agente de monitoramento.

        Args:
            instance_id: ID da instância (ex: "vast_12345" ou "user_gpu_1")
            control_plane_url: URL do servidor de controle (ex: "https://dumontcloud.com")
            check_interval: Intervalo de verificação em segundos (padrão: 30)
            auth_token: Token de autenticação (opcional)
        """
        self.instance_id = instance_id
        self.control_plane_url = control_plane_url.rstrip('/')
        self.check_interval = check_interval
        self.auth_token = auth_token
        self.running = False

        logger.info(f"GPUMonitorAgent inicializado")
        logger.info(f"  Instance ID: {instance_id}")
        logger.info(f"  Control URL: {control_plane_url}")
        logger.info(f"  Check interval: {check_interval}s")

    def get_gpu_utilization(self) -> Dict:
        """
        Obtém utilização da GPU usando nvidia-smi.

        Returns:
            {
                'utilization': 25.5,  # % média de todas as GPUs
                'gpu_count': 1,
                'gpu_names': ['NVIDIA GeForce RTX 3090'],
                'gpu_utilizations': [25.5],  # % de cada GPU individualmente
                'gpu_memory_used': [8192],  # MB de cada GPU
                'gpu_memory_total': [24576],  # MB de cada GPU
            }
        """
        try:
            # Query nvidia-smi para utilização e memória
            cmd = [
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,memory.total,name',
                '--format=csv,noheader,nounits'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"nvidia-smi failed: {result.stderr}")
                return {'utilization': 0, 'gpu_count': 0, 'error': 'nvidia-smi failed'}

            # Parse output
            lines = result.stdout.strip().split('\n')
            gpu_data = []

            for line in lines:
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 4:
                    try:
                        util = float(parts[0])
                        mem_used = float(parts[1])
                        mem_total = float(parts[2])
                        gpu_name = parts[3]

                        gpu_data.append({
                            'utilization': util,
                            'memory_used': mem_used,
                            'memory_total': mem_total,
                            'name': gpu_name
                        })
                    except ValueError as e:
                        logger.warning(f"Failed to parse line: {line} - {e}")
                        continue

            if not gpu_data:
                return {'utilization': 0, 'gpu_count': 0, 'error': 'No GPU data'}

            # Calcular média
            avg_util = sum(g['utilization'] for g in gpu_data) / len(gpu_data)

            return {
                'utilization': round(avg_util, 2),
                'gpu_count': len(gpu_data),
                'gpu_names': [g['name'] for g in gpu_data],
                'gpu_utilizations': [g['utilization'] for g in gpu_data],
                'gpu_memory_used': [g['memory_used'] for g in gpu_data],
                'gpu_memory_total': [g['memory_total'] for g in gpu_data],
            }

        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi timeout")
            return {'utilization': 0, 'gpu_count': 0, 'error': 'timeout'}
        except Exception as e:
            logger.error(f"Error getting GPU utilization: {e}")
            return {'utilization': 0, 'gpu_count': 0, 'error': str(e)}

    def send_status(self, gpu_data: Dict) -> bool:
        """
        Envia status para o servidor de controle.

        Args:
            gpu_data: Dados da GPU retornados por get_gpu_utilization()

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        url = f"{self.control_plane_url}/api/agent/status"

        payload = {
            'instance_id': self.instance_id,
            'gpu_utilization': gpu_data.get('utilization', 0),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'gpu_count': gpu_data.get('gpu_count', 0),
            'gpu_names': gpu_data.get('gpu_names', []),
            'gpu_utilizations': gpu_data.get('gpu_utilizations', []),
            'gpu_memory_used': gpu_data.get('gpu_memory_used', []),
            'gpu_memory_total': gpu_data.get('gpu_memory_total', []),
        }

        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                logger.debug(f"Status sent successfully: {gpu_data.get('utilization')}%")
                return True
            else:
                logger.warning(f"Failed to send status: HTTP {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending status: {e}")
            return False

    def run(self):
        """Loop principal do agente."""
        self.running = True
        logger.info("Starting GPU monitoring loop...")

        consecutive_errors = 0
        max_errors = 10

        while self.running:
            try:
                # Obter utilização da GPU
                gpu_data = self.get_gpu_utilization()

                if 'error' in gpu_data:
                    consecutive_errors += 1
                    logger.warning(f"GPU data error: {gpu_data['error']} (errors: {consecutive_errors}/{max_errors})")

                    if consecutive_errors >= max_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping agent")
                        break
                else:
                    consecutive_errors = 0

                    # Log local
                    logger.info(f"GPU: {gpu_data['utilization']}% ({gpu_data['gpu_count']} GPUs)")

                # Enviar status para servidor
                self.send_status(gpu_data)

                # Aguardar próxima verificação
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping...")
                self.running = False
                break

            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}", exc_info=True)
                consecutive_errors += 1

                if consecutive_errors >= max_errors:
                    logger.error(f"Too many consecutive errors, stopping agent")
                    break

                time.sleep(self.check_interval)

        logger.info("GPU monitoring stopped")

    def stop(self):
        """Para o agente."""
        logger.info("Stopping GPU monitor agent...")
        self.running = False


def main():
    """Entry point quando executado como script."""
    parser = argparse.ArgumentParser(description='GPU Monitor Agent for Dumont Cloud')

    parser.add_argument(
        '--instance-id',
        required=True,
        help='Instance ID (ex: vast_12345)'
    )

    parser.add_argument(
        '--control-url',
        default='http://localhost:5000',
        help='Control plane URL (ex: https://dumontcloud.com)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Check interval in seconds (default: 30)'
    )

    parser.add_argument(
        '--auth-token',
        help='Authentication token (optional)'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: run once and exit'
    )

    args = parser.parse_args()

    # Criar agente
    agent = GPUMonitorAgent(
        instance_id=args.instance_id,
        control_plane_url=args.control_url,
        check_interval=args.interval,
        auth_token=args.auth_token
    )

    if args.test:
        # Modo teste: executar uma vez e mostrar resultado
        logger.info("Running in TEST mode (single check)")
        gpu_data = agent.get_gpu_utilization()
        print("\nGPU Data:")
        print(json.dumps(gpu_data, indent=2))

        success = agent.send_status(gpu_data)
        print(f"\nStatus sent: {'✓ Success' if success else '✗ Failed'}")
        return

    # Modo normal: loop contínuo
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        agent.stop()


if __name__ == '__main__':
    main()
