"""
API endpoints
"""
from . import auth
from . import instances
from . import snapshots
from . import settings
from . import metrics
from . import agent
from . import finetune
from . import warmpool
from . import failover_settings
from . import failover
from . import serverless
from . import machine_history

__all__ = [
    'auth',
    'instances',
    'snapshots',
    'settings',
    'metrics',
    'agent',
    'finetune',
    'warmpool',
    'failover_settings',
    'failover',
    'serverless',
    'machine_history',
]

