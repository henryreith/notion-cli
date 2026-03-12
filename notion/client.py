"""HTTP client for Notion API."""
import json
import os
import time
from pathlib import Path
from typing import Any, Generator

import httpx

from notion.errors import AuthError, NotFoundError, ValidationError, ApiError

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"
CONFIG_FILE = Path.home() / ".config" / "notion-agent" / "config.json"


def _load_token() -> str:
    """Load token from env or config file."""
    token = os.environ.get("NOTION_API_KEY")
    if token:
        return token
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            token = data.get("token")
            if token:
                return token
        except (json.JSONDecodeError, KeyError):
            pass
    raise AuthError("No API token found. Set NOTION_API_KEY or run: notion auth set-token <token>")


def _save_token(token: str) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"token": token}))


def _normalise_id(id_or_url: str) -> str:
    """Extract and normalise a Notion ID to 32-char hex (no hyphens)."""
    # Handle Notion URLs
    if "notion.so" in id_or_url or "notion.com" in id_or_url:
        # Extract last path segment, strip query params
        path = id_or_url.split("?")[0].rstrip("/")
        segment = path.split("/")[-1]
        # ID is the last 32 hex chars (may be after a slug with a dash)
        hex_part = segment.replace("-", "")
        # Find 32-char hex suffix
        if len(hex_part) >= 32:
            return hex_part[-32:]
    # Strip hyphens from UUID format
    clean = id_or_url.replace("-", "").replace(" ", "")
    if len(clean) == 32 and all(c in "0123456789abcdefABCDEF" for c in clean):
        return clean.lower()
    # Return as-is if we can't normalise (let API return error)
    return id_or_url.replace("-", "")


def _handle_response(response: httpx.Response) -> dict:
    """Raise appropriate error based on HTTP status."""
    if response.status_code == 200:
        return response.json()

    try:
        body = response.json()
        message = body.get("message", response.text)
    except Exception:
        message = response.text

    if response.status_code == 401:
        raise AuthError(message)
    elif response.status_code == 404:
        raise NotFoundError(message)
    elif response.status_code == 400:
        raise ValidationError(message)
    elif response.status_code == 429:
        # Handled by retry logic
        raise ApiError(f"Rate limited: {message}", {"status": 429})
    elif response.status_code == 409:
        raise ApiError(f"Conflict: {message}", {"status": 409})
    elif response.status_code >= 500:
        raise ApiError(f"Server error {response.status_code}: {message}", {"status": response.status_code})
    else:
        raise ApiError(f"HTTP {response.status_code}: {message}", {"status": response.status_code})


class NotionClient:
    """Authenticated HTTP client for the Notion API."""

    def __init__(self, token: str | None = None):
        if token is None:
            token = _load_token()
        self.token = token
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make a request with retry logic for 429 and 409."""
        last_error = None
        for attempt in range(4):  # 1 attempt + 3 retries
            try:
                response = self._client.request(method, path, **kwargs)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", 1.0))
                    if attempt < 3:
                        time.sleep(retry_after)
                        continue

                if response.status_code == 409 and attempt == 0:
                    time.sleep(1.0)
                    continue

                return _handle_response(response)

            except (AuthError, NotFoundError, ValidationError):
                raise
            except ApiError as e:
                last_error = e
                if attempt < 3 and "429" not in str(e):
                    break  # Don't retry non-rate-limit API errors
                continue
            except httpx.RequestError as e:
                last_error = ApiError(f"Request failed: {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue

        if last_error:
            raise last_error
        raise ApiError("Request failed after retries")

    def get(self, path: str, **params) -> dict:
        return self._request("GET", path, params=params if params else None)

    def post(self, path: str, body: dict | None = None) -> dict:
        return self._request("POST", path, json=body or {})

    def patch(self, path: str, body: dict) -> dict:
        return self._request("PATCH", path, json=body)

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def paginate(self, method: str, path: str, body: dict | None = None, params: dict | None = None) -> Generator[dict, None, None]:
        """Paginate through all results. Yields individual result items."""
        cursor = None
        while True:
            if method.upper() == "POST":
                request_body = dict(body or {})
                if cursor:
                    request_body["start_cursor"] = cursor
                response = self.post(path, request_body)
            else:
                request_params = dict(params or {})
                if cursor:
                    request_params["start_cursor"] = cursor
                response = self.get(path, **request_params)

            for item in response.get("results", []):
                yield item

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
