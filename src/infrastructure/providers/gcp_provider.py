"""
Google Cloud Platform Provider
Gerencia VMs no GCP para CPU Standby/Failover
"""
import os
import json
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GCPInstanceConfig:
    """Configuração para criar uma VM GCP"""
    name: str
    machine_type: str = "e2-medium"  # 1 vCPU, 4GB RAM - bom custo/benefício
    zone: str = "europe-west1-b"  # Próximo das GPUs EU na Vast.ai
    disk_size_gb: int = 100
    disk_type: str = "pd-standard"  # Mais barato que pd-ssd
    image_family: str = "ubuntu-2204-lts"
    image_project: str = "ubuntu-os-cloud"
    spot: bool = True  # Usar Spot VM (até 91% desconto)
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = ["dumont-standby", "allow-ssh"]


class GCPProvider:
    """
    Provider para gerenciar VMs no Google Cloud Platform.
    Usado para CPU Standby que sincroniza com GPU Vast.ai.
    """

    def __init__(self, credentials_json: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Inicializa o provider GCP.

        Args:
            credentials_json: JSON string com credenciais da service account
            credentials_path: Caminho para arquivo de credenciais JSON
        """
        self.credentials = None
        self.project_id = None
        self._compute = None

        # Carregar credenciais
        if credentials_json:
            self.credentials = json.loads(credentials_json)
            self.project_id = self.credentials.get("project_id")
        elif credentials_path and os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                self.credentials = json.load(f)
            self.project_id = self.credentials.get("project_id")
        else:
            # Tentar carregar do ambiente ou arquivo padrão
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if creds_path and os.path.exists(creds_path):
                with open(creds_path, 'r') as f:
                    self.credentials = json.load(f)
                self.project_id = self.credentials.get("project_id")

        if not self.credentials:
            logger.warning("GCP credentials not configured")

    def _get_compute_client(self):
        """Retorna cliente do Compute Engine (lazy loading)"""
        if self._compute is None:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                credentials = service_account.Credentials.from_service_account_info(
                    self.credentials,
                    scopes=['https://www.googleapis.com/auth/compute']
                )
                self._compute = build('compute', 'v1', credentials=credentials)
            except ImportError:
                logger.error("google-cloud libraries not installed. Run: pip install google-api-python-client google-auth")
                raise
        return self._compute

    def create_instance(self, config: GCPInstanceConfig) -> Dict[str, Any]:
        """
        Cria uma nova VM no GCP.

        Args:
            config: Configuração da VM

        Returns:
            Dict com informações da instância criada
        """
        if not self.credentials:
            return {"error": "GCP credentials not configured"}

        try:
            compute = self._get_compute_client()

            # Configuração da VM
            machine_type_url = f"zones/{config.zone}/machineTypes/{config.machine_type}"

            # Imagem do disco
            image_response = compute.images().getFromFamily(
                project=config.image_project,
                family=config.image_family
            ).execute()
            source_image = image_response['selfLink']

            # Configuração do disco
            disk_config = {
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceImage": source_image,
                    "diskSizeGb": str(config.disk_size_gb),
                    "diskType": f"zones/{config.zone}/diskTypes/{config.disk_type}"
                }
            }

            # Configuração de rede
            network_config = {
                "network": "global/networks/default",
                "accessConfigs": [
                    {
                        "type": "ONE_TO_ONE_NAT",
                        "name": "External NAT"
                    }
                ]
            }

            # Carregar chave SSH pública do usuário
            ssh_pub_key = ""
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
            ssh_pub_path = os.path.expanduser("~/.ssh/id_rsa.pub")

            # Se não existir, gerar nova chave SSH
            if not os.path.exists(ssh_key_path):
                import subprocess
                ssh_dir = os.path.expanduser("~/.ssh")
                os.makedirs(ssh_dir, exist_ok=True)

                logger.info("Generating SSH key pair...")
                subprocess.run(
                    ["ssh-keygen", "-t", "rsa", "-f", ssh_key_path, "-N", ""],
                    check=True,
                    capture_output=True
                )
                logger.info(f"✓ SSH key generated at {ssh_key_path}")

            # Carregar chave pública
            if os.path.exists(ssh_pub_path):
                with open(ssh_pub_path, 'r') as f:
                    ssh_pub_key = f.read().strip()
            else:
                raise RuntimeError(f"SSH public key not found at {ssh_pub_path}")

            # Startup script para configurar a VM
            startup_script = f"""#!/bin/bash
set -e

# Atualizar sistema
apt-get update
apt-get install -y rsync rclone htop tmux

# Criar diretório de workspace
mkdir -p /workspace
chmod 777 /workspace

# Configurar SSH para aceitar conexões root
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin no/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd

# Adicionar chave SSH para root
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "{ssh_pub_key}" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Também para usuário ubuntu se existir
if id ubuntu &>/dev/null; then
    mkdir -p /home/ubuntu/.ssh
    echo "{ssh_pub_key}" >> /home/ubuntu/.ssh/authorized_keys
    chown -R ubuntu:ubuntu /home/ubuntu/.ssh
    chmod 700 /home/ubuntu/.ssh
    chmod 600 /home/ubuntu/.ssh/authorized_keys
fi

# Instalar s5cmd para sync com R2
wget -q https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz
tar -xzf s5cmd_2.2.2_Linux-64bit.tar.gz
mv s5cmd /usr/local/bin/
rm s5cmd_2.2.2_Linux-64bit.tar.gz

echo "Dumont CPU Standby ready" > /var/log/dumont-ready
"""

            # Formato de chave SSH para metadados GCP: "username:ssh-rsa AAAA... comment"
            ssh_keys_metadata = f"root:{ssh_pub_key}" if ssh_pub_key else ""

            # Corpo da requisição
            body = {
                "name": config.name,
                "machineType": machine_type_url,
                "disks": [disk_config],
                "networkInterfaces": [network_config],
                "tags": {"items": config.tags},
                "metadata": {
                    "items": [
                        {"key": "startup-script", "value": startup_script},
                        {"key": "ssh-keys", "value": ssh_keys_metadata}
                    ]
                },
                "labels": {
                    "purpose": "dumont-standby",
                    "managed-by": "dumont-cloud"
                }
            }

            # Configurar como Spot VM se solicitado
            if config.spot:
                body["scheduling"] = {
                    "provisioningModel": "SPOT",
                    "instanceTerminationAction": "STOP",  # Para quando preempted
                    "onHostMaintenance": "TERMINATE"
                }

            logger.info(f"Creating GCP instance {config.name} in {config.zone}")

            # Criar a instância com retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    operation = compute.instances().insert(
                        project=self.project_id,
                        zone=config.zone,
                        body=body
                    ).execute()

                    # Aguardar operação completar
                    self._wait_for_operation(operation['name'], config.zone)
                    break  # Sucesso, sair do loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(f"Failed to create instance (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise

            # Obter informações da instância criada
            instance = compute.instances().get(
                project=self.project_id,
                zone=config.zone,
                instance=config.name
            ).execute()

            # Extrair IP externo
            external_ip = None
            for interface in instance.get('networkInterfaces', []):
                for access_config in interface.get('accessConfigs', []):
                    if 'natIP' in access_config:
                        external_ip = access_config['natIP']
                        break

            logger.info(f"GCP instance {config.name} created with IP {external_ip}")

            return {
                "success": True,
                "instance_id": instance['id'],
                "name": config.name,
                "zone": config.zone,
                "machine_type": config.machine_type,
                "external_ip": external_ip,
                "internal_ip": instance['networkInterfaces'][0].get('networkIP'),
                "status": instance['status'],
                "spot": config.spot
            }

        except Exception as e:
            logger.error(f"Failed to create GCP instance: {e}")
            return {"error": str(e)}

    def delete_instance(self, name: str, zone: str) -> bool:
        """
        Deleta uma VM do GCP.

        Args:
            name: Nome da instância
            zone: Zona da instância

        Returns:
            True se deletado com sucesso
        """
        if not self.credentials:
            return False

        try:
            compute = self._get_compute_client()

            logger.info(f"Deleting GCP instance {name} in {zone}")

            # Delete with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    operation = compute.instances().delete(
                        project=self.project_id,
                        zone=zone,
                        instance=name
                    ).execute()

                    self._wait_for_operation(operation['name'], zone)
                    logger.info(f"✓ GCP instance {name} deleted")
                    return True

                except Exception as e:
                    if attempt < max_retries - 1:
                        # Check if it's a "not found" error - don't retry
                        if "notFound" in str(e) or "not found" in str(e).lower():
                            logger.info(f"Instance {name} not found (already deleted)")
                            return True

                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Failed to delete instance (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise

        except Exception as e:
            logger.error(f"✗ Failed to delete GCP instance after retries: {e}")
            return False

    def get_instance(self, name: str, zone: str) -> Dict[str, Any]:
        """
        Obtém informações de uma VM.

        Args:
            name: Nome da instância
            zone: Zona da instância

        Returns:
            Dict com informações da instância
        """
        if not self.credentials:
            return {"error": "GCP credentials not configured"}

        try:
            compute = self._get_compute_client()

            instance = compute.instances().get(
                project=self.project_id,
                zone=zone,
                instance=name
            ).execute()

            # Extrair IP externo
            external_ip = None
            for interface in instance.get('networkInterfaces', []):
                for access_config in interface.get('accessConfigs', []):
                    if 'natIP' in access_config:
                        external_ip = access_config['natIP']
                        break

            return {
                "instance_id": instance['id'],
                "name": instance['name'],
                "zone": zone,
                "status": instance['status'],
                "external_ip": external_ip,
                "internal_ip": instance['networkInterfaces'][0].get('networkIP'),
                "machine_type": instance['machineType'].split('/')[-1],
                "created": instance.get('creationTimestamp')
            }

        except Exception as e:
            logger.error(f"Failed to get GCP instance: {e}")
            return {"error": str(e)}

    def list_instances(self, zone: Optional[str] = None, filter_label: str = "managed-by=dumont-cloud") -> List[Dict[str, Any]]:
        """
        Lista VMs gerenciadas pelo Dumont.

        Args:
            zone: Zona específica (None = todas as zonas)
            filter_label: Filtro por label

        Returns:
            Lista de instâncias
        """
        if not self.credentials:
            return []

        try:
            compute = self._get_compute_client()
            instances = []

            if zone:
                zones = [zone]
            else:
                # Listar todas as zonas
                zones_response = compute.zones().list(project=self.project_id).execute()
                zones = [z['name'] for z in zones_response.get('items', [])]

            for z in zones:
                try:
                    response = compute.instances().list(
                        project=self.project_id,
                        zone=z,
                        filter=f"labels.{filter_label}" if filter_label else None
                    ).execute()

                    for instance in response.get('items', []):
                        # Verificar se tem o label correto
                        labels = instance.get('labels', {})
                        if 'managed-by' in labels and labels['managed-by'] == 'dumont-cloud':
                            external_ip = None
                            for interface in instance.get('networkInterfaces', []):
                                for access_config in interface.get('accessConfigs', []):
                                    if 'natIP' in access_config:
                                        external_ip = access_config['natIP']
                                        break

                            instances.append({
                                "instance_id": instance['id'],
                                "name": instance['name'],
                                "zone": z,
                                "status": instance['status'],
                                "external_ip": external_ip,
                                "machine_type": instance['machineType'].split('/')[-1]
                            })
                except:
                    continue

            return instances

        except Exception as e:
            logger.error(f"Failed to list GCP instances: {e}")
            return []

    def start_instance(self, name: str, zone: str) -> bool:
        """Inicia uma VM parada"""
        if not self.credentials:
            return False

        try:
            compute = self._get_compute_client()

            operation = compute.instances().start(
                project=self.project_id,
                zone=zone,
                instance=name
            ).execute()

            self._wait_for_operation(operation['name'], zone)
            return True

        except Exception as e:
            logger.error(f"Failed to start GCP instance: {e}")
            return False

    def stop_instance(self, name: str, zone: str) -> bool:
        """Para uma VM (não deleta)"""
        if not self.credentials:
            return False

        try:
            compute = self._get_compute_client()

            operation = compute.instances().stop(
                project=self.project_id,
                zone=zone,
                instance=name
            ).execute()

            self._wait_for_operation(operation['name'], zone)
            return True

        except Exception as e:
            logger.error(f"Failed to stop GCP instance: {e}")
            return False

    def _wait_for_operation(self, operation_name: str, zone: str, timeout: int = 300):
        """Aguarda uma operação do GCP completar"""
        compute = self._get_compute_client()
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = compute.zoneOperations().get(
                project=self.project_id,
                zone=zone,
                operation=operation_name
            ).execute()

            if result['status'] == 'DONE':
                if 'error' in result:
                    raise Exception(result['error'])
                return result

            time.sleep(2)

        raise TimeoutError(f"Operation {operation_name} timed out after {timeout}s")

    def get_spot_pricing(self, machine_type: str = "e2-medium", zone: str = "europe-west1-b") -> Dict[str, Any]:
        """
        Obtém preço estimado para Spot VM.
        Nota: GCP não tem API pública para preços Spot em tempo real,
        então retornamos estimativas baseadas em dados históricos.
        """
        # Preços estimados de Spot VMs (baseado em dados de Dez 2025)
        spot_prices = {
            "e2-micro": {"hourly": 0.002, "monthly": 1.50},
            "e2-small": {"hourly": 0.005, "monthly": 3.60},
            "e2-medium": {"hourly": 0.010, "monthly": 7.20},
            "e2-standard-2": {"hourly": 0.020, "monthly": 14.40},
            "e2-standard-4": {"hourly": 0.040, "monthly": 28.80},
        }

        pricing = spot_prices.get(machine_type, {"hourly": 0.01, "monthly": 7.20})

        return {
            "machine_type": machine_type,
            "zone": zone,
            "spot": True,
            "estimated_hourly_usd": pricing["hourly"],
            "estimated_monthly_usd": pricing["monthly"],
            "disk_per_gb_monthly_usd": 0.04,  # pd-standard
            "note": "Spot prices vary. These are estimates."
        }
