"""Tests for Dumont CLI"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os
import json

# Add CLI path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import APIClient
from commands.base import CommandBuilder
from utils.token_manager import TokenManager


class TestAPIClient:
    """Tests for APIClient"""

    @pytest.fixture
    def api(self):
        """Create API client instance"""
        return APIClient(base_url="http://localhost:8766")

    def test_init(self, api):
        """Test API client initialization"""
        assert api.base_url == "http://localhost:8766"
        assert api.session is not None
        assert api.token_manager is not None

    def test_get_headers_no_token(self, api):
        """Test headers without token"""
        with patch.object(api.token_manager, 'get', return_value=None):
            headers = api._get_headers()
            assert headers["Content-Type"] == "application/json"
            assert "Authorization" not in headers

    def test_get_headers_with_token(self, api):
        """Test headers with token"""
        with patch.object(api.token_manager, 'get', return_value="test_token"):
            headers = api._get_headers()
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test_token"

    @patch('requests.Session.get')
    def test_call_get_success(self, mock_get, api):
        """Test GET request success"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"instances": []}
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result == {"instances": []}
        mock_get.assert_called_once()

    @patch('requests.Session.post')
    def test_call_post_success(self, mock_post, api):
        """Test POST request success"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "12345"}
        mock_post.return_value = mock_response

        result = api.call("POST", "/api/v1/instances", data={"gpu_name": "RTX 4090"}, silent=True)
        assert result == {"id": "12345"}
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_call_login_saves_token(self, mock_post, api):
        """Test login saves token"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response

        with patch.object(api.token_manager, 'save') as mock_save:
            result = api.call("POST", "/api/auth/login", data={"username": "test", "password": "pass"}, silent=True)
            assert result["access_token"] == "new_token"
            mock_save.assert_called_once_with("new_token")

    @patch('requests.Session.post')
    def test_call_logout_clears_token(self, mock_post, api):
        """Test logout clears token"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        with patch.object(api.token_manager, 'clear') as mock_clear:
            result = api.call("POST", "/api/auth/logout", silent=True)
            mock_clear.assert_called_once()

    @patch('requests.Session.get')
    def test_call_401_unauthorized(self, mock_get, api):
        """Test 401 unauthorized response"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result is None

    @patch('requests.Session.get')
    def test_call_404_not_found(self, mock_get, api):
        """Test 404 not found response"""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances/999", silent=True)
        assert result is None

    @patch('requests.Session.get')
    def test_call_connection_error(self, mock_get, api):
        """Test connection error"""
        mock_get.side_effect = Exception("Connection refused")

        result = api.call("GET", "/api/v1/instances", silent=True)
        assert result is None

    def test_call_unsupported_method(self, api):
        """Test unsupported HTTP method"""
        result = api.call("PATCH", "/api/v1/instances", silent=True)
        assert result is None


class TestCommandBuilder:
    """Tests for CommandBuilder"""

    @pytest.fixture
    def api(self):
        """Create mock API client"""
        api = MagicMock()
        api.call = MagicMock()
        return api

    @pytest.fixture
    def builder(self, api):
        """Create CommandBuilder instance"""
        return CommandBuilder(api)

    def test_init(self, builder, api):
        """Test CommandBuilder initialization"""
        assert builder.api == api
        assert builder.commands_cache is None

    def test_build_command_tree_with_schema(self, builder, api):
        """Test building command tree from OpenAPI schema"""
        mock_schema = {
            "paths": {
                "/api/v1/instances": {
                    "get": {
                        "summary": "List instances",
                        "parameters": []
                    },
                    "post": {
                        "summary": "Create instance",
                        "requestBody": {}
                    }
                },
                "/api/v1/snapshots": {
                    "get": {
                        "summary": "List snapshots",
                        "parameters": []
                    }
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        commands = builder.build_command_tree()

        # Check auth commands (from overrides)
        assert "auth" in commands
        assert "login" in commands["auth"]
        assert "logout" in commands["auth"]
        assert "me" in commands["auth"]

        # Check instance commands
        assert "instance" in commands
        assert "list" in commands["instance"]
        assert "create" in commands["instance"]
        assert "pause" in commands["instance"]
        assert "resume" in commands["instance"]

        # Check snapshot commands
        assert "snapshot" in commands
        assert "list" in commands["snapshot"]

    def test_build_command_tree_no_schema(self, builder, api):
        """Test building command tree when schema is None"""
        api.load_openapi_schema.return_value = None

        commands = builder.build_command_tree()
        assert commands == {}

    def test_execute_help_command(self, builder, api, capsys):
        """Test help command"""
        api.load_openapi_schema.return_value = {"paths": {}}

        builder.execute("help", None, [])

        captured = capsys.readouterr()
        assert "Dumont Cloud - Command Reference" in captured.out

    def test_execute_unknown_resource(self, builder, api):
        """Test unknown resource"""
        api.load_openapi_schema.return_value = {"paths": {}}

        with pytest.raises(SystemExit):
            builder.execute("unknown", "action", [])

    def test_execute_unknown_action(self, builder, api):
        """Test unknown action"""
        mock_schema = {
            "paths": {
                "/api/v1/instances": {
                    "get": {"summary": "List", "parameters": []}
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        with pytest.raises(SystemExit):
            builder.execute("instance", "unknown", [])

    def test_execute_simple_get(self, builder, api):
        """Test executing simple GET command"""
        mock_schema = {
            "paths": {
                "/api/v1/instances": {
                    "get": {"summary": "List instances", "parameters": []}
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        builder.execute("instance", "list", [])

        api.call.assert_called_once_with("GET", "/api/v1/instances", None, None)

    def test_execute_with_path_param(self, builder, api):
        """Test executing command with path parameter"""
        mock_schema = {
            "paths": {
                "/api/v1/instances/{instance_id}": {
                    "get": {"summary": "Get instance", "parameters": []}
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        builder.execute("instance", "get", ["12345"])

        api.call.assert_called_once_with("GET", "/api/v1/instances/12345", None, None)

    def test_execute_with_missing_path_param(self, builder, api):
        """Test executing command with missing path parameter"""
        mock_schema = {
            "paths": {
                "/api/v1/instances/{instance_id}": {
                    "delete": {"summary": "Delete instance", "parameters": []}
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        with pytest.raises(SystemExit):
            builder.execute("instance", "delete", [])

    def test_execute_login_with_credentials(self, builder, api):
        """Test login command with username and password"""
        mock_schema = {
            "paths": {
                "/api/auth/login": {
                    "post": {
                        "summary": "Login",
                        "requestBody": {}
                    }
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        builder.execute("auth", "login", ["user@test.com", "password123"])

        api.call.assert_called_once()
        args = api.call.call_args
        assert args[0][0] == "POST"
        assert args[0][1] == "/api/auth/login"
        assert args[0][2] == {"username": "user@test.com", "password": "password123"}

    def test_execute_with_key_value_data(self, builder, api):
        """Test command with key=value data"""
        mock_schema = {
            "paths": {
                "/api/v1/snapshots": {
                    "post": {
                        "summary": "Create snapshot",
                        "requestBody": {}
                    }
                }
            }
        }
        api.load_openapi_schema.return_value = mock_schema

        builder.execute("snapshot", "create", ["name=backup1", "instance_id=12345"])

        api.call.assert_called_once()
        args = api.call.call_args
        # Note: numeric values are auto-converted to int
        assert args[0][2] == {"name": "backup1", "instance_id": 12345}


class TestTokenManager:
    """Tests for TokenManager"""

    @pytest.fixture
    def token_manager(self, tmp_path):
        """Create TokenManager with temp file"""
        import tempfile
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path
            tm = TokenManager()
            yield tm

    def test_init(self, token_manager):
        """Test TokenManager initialization"""
        assert token_manager.token is None

    def test_save_and_get_token(self, token_manager):
        """Test saving and getting token"""
        token_manager.save("test_token_123")
        assert token_manager.get() == "test_token_123"

    def test_clear_token(self, token_manager):
        """Test clearing token"""
        token_manager.save("test_token")
        assert token_manager.get() == "test_token"

        token_manager.clear()
        assert token_manager.get() is None

    def test_get_nonexistent_token(self, token_manager):
        """Test getting token when file doesn't exist"""
        assert token_manager.get() is None


class TestCoverageCommands:
    """Tests to verify API endpoint coverage"""

    @pytest.fixture
    def builder(self):
        """Create CommandBuilder with mock API"""
        api = MagicMock()
        api.load_openapi_schema.return_value = {"paths": {}}
        return CommandBuilder(api)

    def test_auth_commands_available(self, builder):
        """Test all auth commands are available"""
        commands = builder.build_command_tree()
        assert "auth" in commands
        assert "login" in commands["auth"]
        assert "logout" in commands["auth"]
        assert "me" in commands["auth"]
        assert "register" in commands["auth"]

    def test_instance_commands_available(self, builder):
        """Test all instance commands are available"""
        commands = builder.build_command_tree()
        assert "instance" in commands
        required_commands = [
            "list", "create", "get", "delete", "pause", "resume",
            "wake", "migrate", "migrate-estimate", "sync", "sync-status", "offers"
        ]
        for cmd in required_commands:
            assert cmd in commands["instance"], f"Missing instance command: {cmd}"

    def test_snapshot_commands_available(self, builder):
        """Test all snapshot commands are available"""
        commands = builder.build_command_tree()
        assert "snapshot" in commands
        assert "list" in commands["snapshot"]
        assert "create" in commands["snapshot"]
        assert "restore" in commands["snapshot"]
        assert "delete" in commands["snapshot"]

    def test_finetune_commands_available(self, builder):
        """Test all finetune commands are available"""
        commands = builder.build_command_tree()
        assert "finetune" in commands
        required_commands = [
            "list", "create", "get", "logs", "cancel", "refresh", "models", "upload-dataset"
        ]
        for cmd in required_commands:
            assert cmd in commands["finetune"], f"Missing finetune command: {cmd}"

    def test_savings_commands_available(self, builder):
        """Test all savings commands are available"""
        commands = builder.build_command_tree()
        assert "savings" in commands
        assert "summary" in commands["savings"]
        assert "history" in commands["savings"]
        assert "breakdown" in commands["savings"]
        assert "comparison" in commands["savings"]

    def test_metrics_commands_available(self, builder):
        """Test all metrics commands are available"""
        commands = builder.build_command_tree()
        assert "metrics" in commands
        required_commands = [
            "market", "market-summary", "providers", "efficiency",
            "predictions", "compare", "gpus", "types",
            "savings-real", "savings-history", "hibernation-events"
        ]
        for cmd in required_commands:
            assert cmd in commands["metrics"], f"Missing metrics command: {cmd}"

    def test_settings_commands_available(self, builder):
        """Test all settings commands are available"""
        commands = builder.build_command_tree()
        assert "settings" in commands
        assert "get" in commands["settings"]
        assert "update" in commands["settings"]


class TestIntegrationScenarios:
    """Integration-style tests for common workflows"""

    @pytest.fixture
    def api(self):
        """Create API client with mock session"""
        return APIClient(base_url="http://localhost:8766")

    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_full_auth_workflow(self, mock_get, mock_post, api):
        """Test full authentication workflow: login -> me -> logout"""
        # Login
        login_response = Mock()
        login_response.ok = True
        login_response.status_code = 200
        login_response.json.return_value = {"access_token": "token123"}
        mock_post.return_value = login_response

        with patch.object(api.token_manager, 'save') as mock_save:
            result = api.call("POST", "/api/auth/login",
                            data={"username": "test", "password": "pass"},
                            silent=True)
            assert result["access_token"] == "token123"
            mock_save.assert_called_once_with("token123")

        # Get current user
        me_response = Mock()
        me_response.ok = True
        me_response.status_code = 200
        me_response.json.return_value = {"email": "test@test.com", "id": 1}
        mock_get.return_value = me_response

        with patch.object(api.token_manager, 'get', return_value="token123"):
            result = api.call("GET", "/api/auth/me", silent=True)
            assert result["email"] == "test@test.com"

        # Logout
        logout_response = Mock()
        logout_response.ok = True
        logout_response.status_code = 200
        logout_response.json.return_value = {"status": "success"}
        mock_post.return_value = logout_response

        with patch.object(api.token_manager, 'clear') as mock_clear:
            result = api.call("POST", "/api/auth/logout", silent=True)
            mock_clear.assert_called_once()

    @patch('requests.Session.get')
    def test_instance_list_workflow(self, mock_get, api):
        """Test listing instances"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "instances": [
                {"id": "1", "gpu_name": "RTX 4090", "status": "running"},
                {"id": "2", "gpu_name": "RTX 3090", "status": "paused"}
            ]
        }
        mock_get.return_value = mock_response

        result = api.call("GET", "/api/v1/instances", silent=True)

        assert len(result["instances"]) == 2
        assert result["instances"][0]["gpu_name"] == "RTX 4090"

    @patch('requests.Session.post')
    def test_snapshot_create_workflow(self, mock_post, api):
        """Test creating snapshot"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "snapshot_id": "snap_123",
            "name": "backup1",
            "instance_id": "12345"
        }
        mock_post.return_value = mock_response

        result = api.call("POST", "/api/v1/snapshots",
                         data={"name": "backup1", "instance_id": "12345"},
                         silent=True)

        assert result["snapshot_id"] == "snap_123"
        assert result["name"] == "backup1"
