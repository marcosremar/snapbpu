"""
Application constants
"""

# API Configuration
API_V1_PREFIX = "/api/v1"
API_TITLE = "Dumont Cloud API"
API_VERSION = "3.0.0"
API_DESCRIPTION = """
Dumont Cloud - GPU Instance Management Platform

Manage GPU instances, snapshots, and deployments on vast.ai.
"""

# Vast.ai Configuration
VAST_API_URL = "https://console.vast.ai/api/v0"
VAST_DEFAULT_TIMEOUT = 30

# SSH Configuration
SSH_DEFAULT_TIMEOUT = 120
SSH_CONNECT_TIMEOUT = 30
SSH_DEFAULT_USER = "root"

# Restic Configuration
RESTIC_DEFAULT_CONNECTIONS = 32
RESTIC_VERSION = "0.17.3"
RESTIC_DOWNLOAD_URL = f"https://github.com/restic/restic/releases/download/v{RESTIC_VERSION}/restic_{RESTIC_VERSION}_linux_amd64.bz2"

# Instance States
INSTANCE_STATE_RUNNING = "running"
INSTANCE_STATE_STOPPED = "stopped"
INSTANCE_STATE_PAUSED = "paused"
INSTANCE_STATE_CREATING = "creating"
INSTANCE_STATE_EXITED = "exited"

# Service Ports
CODE_SERVER_PORT = 8080
JUPYTER_PORT = 8888
TENSORBOARD_PORT = 6006
SYNCTHING_PORT = 8384

# Agent Configuration
PRICE_MONITOR_INTERVAL = 30  # minutes
HIBERNATION_CHECK_INTERVAL = 30  # seconds
AGENT_DEFAULT_TIMEOUT = 300  # seconds

# User Session
SESSION_COOKIE_NAME = "dumont_session"
SESSION_MAX_AGE = 86400  # 24 hours

# Rate Limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 60  # seconds
