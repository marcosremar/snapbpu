from .snapshots import snapshots_bp
from .instances import instances_bp

# cpu_standby_bp foi movido para v1/endpoints/standby.py (FastAPI)
# A implementação Flask foi descontinuada

__all__ = ['snapshots_bp', 'instances_bp']
