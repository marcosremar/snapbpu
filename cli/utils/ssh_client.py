"""SSH client for remote execution"""
import subprocess
from typing import Optional, Tuple


class SSHClient:
    """Execute commands on remote instances via SSH"""

    def __init__(self, host: str, port: int, user: str = "root"):
        self.host = host
        self.port = port
        self.user = user

    def execute(
        self,
        script: str,
        timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """
        Execute a script on remote host via SSH

        Returns:
            (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                [
                    'ssh',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=30',
                    '-p', str(self.port),
                    f'{self.user}@{self.host}',
                    script
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def get_connection_string(self) -> str:
        """Get SSH connection string"""
        return f"ssh -p {self.port} {self.user}@{self.host}"
