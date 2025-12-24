"""API client for Dumont Cloud"""
import json
import os
import sys
from typing import Dict, Any, Optional
import requests

from .token_manager import TokenManager

# Default API URL - can be overridden by environment variable
DEFAULT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8001")


class APIClient:
    """HTTP client for Dumont Cloud API"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or DEFAULT_API_URL
        self.session = requests.Session()
        self.token_manager = TokenManager()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication if available"""
        headers = {"Content-Type": "application/json"}
        token = self.token_manager.get()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def call(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        silent: bool = False,
    ) -> Optional[Dict]:
        """Make API call and handle response"""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, params=params)
            else:
                if not silent:
                    print(f"❌ Unsupported method: {method}")
                return None

            # Handle auth responses
            if "login" in path and response.ok:
                try:
                    result = response.json()
                    if "access_token" in result or "token" in result:
                        token = result.get("access_token") or result.get("token")
                        self.token_manager.save(token)
                        if not silent:
                            print(f"✅ Login successful! Token saved.")
                        return result
                except (json.JSONDecodeError, KeyError):
                    pass

            if "logout" in path and response.ok:
                self.token_manager.clear()
                if not silent:
                    print("✅ Logged out successfully.")
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"status": "success"}

            # Handle errors
            if response.status_code == 401:
                if not silent:
                    print("❌ Unauthorized. Please login first: dumont auth login <email> <password>")
                return None

            if response.status_code == 404:
                if not silent:
                    print(f"❌ Not found: {path}")
                return None

            # Parse response
            try:
                result = response.json()
                if not silent:
                    if response.ok:
                        print(f"✅ Success ({response.status_code})")
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    else:
                        print(f"❌ Error ({response.status_code})")
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                return result if response.ok else None
            except json.JSONDecodeError:
                if not silent:
                    if response.ok:
                        print(f"✅ Success ({response.status_code})")
                        print(response.text)
                    else:
                        print(f"❌ Error ({response.status_code}): {response.text}")
                return {"raw": response.text} if response.ok else None

        except requests.exceptions.ConnectionError:
            if not silent:
                print(f"❌ Could not connect to {self.base_url}")
                print("   Make sure the backend is running.")
            return None
        except Exception as e:
            if not silent:
                print(f"❌ Error: {e}")
            return None

    def load_openapi_schema(self) -> Optional[Dict[str, Any]]:
        """Load OpenAPI schema from FastAPI"""
        try:
            endpoints = ["/api/v1/openapi.json", "/openapi.json"]
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError:
                    continue
            print(f"❌ Could not find OpenAPI schema")
            return None
        except Exception as e:
            print(f"❌ Error loading API schema: {e}")
            return None
