"""HTTP Client for Dumont API"""
import os
import json
from typing import Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from .exceptions import (
    DumontError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    APIError,
    ConnectionError,
)


class HTTPClient:
    """Low-level HTTP client for API communication"""

    DEFAULT_API_URL = "http://localhost:8000"
    TOKEN_FILE = os.path.expanduser("~/.dumont_token")

    def __init__(
        self,
        api_url: str = None,
        token: str = None,
        timeout: int = 30,
    ):
        self.api_url = (api_url or os.environ.get("DUMONT_API_URL") or self.DEFAULT_API_URL).rstrip("/")
        self.timeout = timeout
        self._token = token

    @property
    def token(self) -> Optional[str]:
        """Get authentication token"""
        if self._token:
            return self._token

        # Try to load from file
        if os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE) as f:
                    data = json.load(f)
                    return data.get("access_token")
            except (json.JSONDecodeError, IOError):
                pass

        return None

    @token.setter
    def token(self, value: str):
        """Set authentication token"""
        self._token = value

    def save_token(self, token: str):
        """Save token to file for persistence"""
        self._token = token
        try:
            with open(self.TOKEN_FILE, "w") as f:
                json.dump({"access_token": token}, f)
        except IOError:
            pass  # Ignore file errors

    def clear_token(self):
        """Clear saved token"""
        self._token = None
        if os.path.exists(self.TOKEN_FILE):
            try:
                os.remove(self.TOKEN_FILE)
            except IOError:
                pass

    def request(
        self,
        method: str,
        path: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /api/v1/instances)
            data: Request body (will be JSON encoded)
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed JSON response

        Raises:
            DumontError subclasses for various error conditions
        """
        # Build URL
        url = f"{self.api_url}{path}"
        if params:
            url += "?" + urlencode(params)

        # Build headers
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"

        if headers:
            req_headers.update(headers)

        # Build request
        body = json.dumps(data).encode("utf-8") if data else None
        request = Request(url, data=body, headers=req_headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}

        except HTTPError as e:
            # Parse error response
            try:
                error_body = e.read().decode("utf-8")
                error_data = json.loads(error_body) if error_body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_data = {}

            message = error_data.get("detail") or error_data.get("message") or str(e)

            if e.code == 401:
                raise AuthenticationError(message, status_code=401, response=error_data)
            elif e.code == 404:
                raise NotFoundError(message, status_code=404, response=error_data)
            elif e.code == 400 or e.code == 422:
                raise ValidationError(message, status_code=e.code, response=error_data)
            elif e.code == 429:
                retry_after = e.headers.get("Retry-After")
                raise RateLimitError(
                    message,
                    status_code=429,
                    response=error_data,
                    retry_after=int(retry_after) if retry_after else None,
                )
            else:
                raise APIError(message, status_code=e.code, response=error_data)

        except URLError as e:
            raise ConnectionError(f"Failed to connect to API: {e.reason}")

        except Exception as e:
            raise DumontError(f"Unexpected error: {e}")

    def get(self, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """GET request"""
        return self.request("GET", path, params=params)

    def post(self, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """POST request"""
        return self.request("POST", path, data=data)

    def put(self, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """PUT request"""
        return self.request("PUT", path, data=data)

    def delete(self, path: str) -> Dict[str, Any]:
        """DELETE request"""
        return self.request("DELETE", path)
