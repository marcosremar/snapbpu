"""
API endpoints
"""
from . import auth
from . import instances
from . import snapshots
from . import settings
from . import metrics
from . import agent

__all__ = ['auth', 'instances', 'snapshots', 'settings', 'metrics', 'agent']

