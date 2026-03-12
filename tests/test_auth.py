"""Tests for auth commands and HTTP client."""
import json
import os
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli
from notion.client import NotionClient, _normalise_id
from notion.errors import AuthError, NotFoundError, ApiError


@pytest.fixture
def runner():
    return CliRunner()


class TestNormaliseId:
    def test_uuid_with_hyphens(self):
        result = _normalise_id("550e8400-e29b-41d4-a716-446655440000")
        assert result == "550e8400e29b41d4a716446655440000"

    def test_plain_32_hex(self):
        result = _normalise_id("550e8400e29b41d4a716446655440000")
        assert result == "550e8400e29b41d4a716446655440000"

    def test_notion_url(self):
        url = "https://www.notion.so/My-Page-550e8400e29b41d4a716446655440000"
        result = _normalise_id(url)
        assert result == "550e8400e29b41d4a716446655440000"


class TestTokenPriority:
    def test_env_takes_priority(self, tmp_path, monkeypatch):
        """NOTION_API_KEY env var takes priority over config file."""
        monkeypatch.setenv("NOTION_API_KEY", "env_token_123")
        from notion.client import _load_token
        token = _load_token()
        assert token == "env_token_123"

    def test_missing_token_raises_auth_error(self, monkeypatch):
        """Missing token raises AuthError."""
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        # Point config to non-existent file
        import notion.client as c
        orig = c.CONFIG_FILE
        c.CONFIG_FILE = c.Path("/nonexistent/config.json")
        from notion.errors import AuthError
        with pytest.raises(AuthError):
            c._load_token()
        c.CONFIG_FILE = orig


class TestHttpClient:
    @respx.mock
    def test_successful_get(self):
        respx.get("https://api.notion.com/v1/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user1", "name": "Bot", "type": "bot"})
        )
        client = NotionClient(token="test_token")
        result = client.get("/users/me")
        assert result["name"] == "Bot"
        client.close()

    @respx.mock
    def test_401_raises_auth_error(self):
        respx.get("https://api.notion.com/v1/users/me").mock(
            return_value=httpx.Response(401, json={"message": "API token is invalid."})
        )
        client = NotionClient(token="bad_token")
        with pytest.raises(AuthError):
            client.get("/users/me")
        client.close()

    @respx.mock
    def test_404_raises_not_found_error(self):
        respx.get("https://api.notion.com/v1/pages/notexist").mock(
            return_value=httpx.Response(404, json={"message": "Could not find page."})
        )
        client = NotionClient(token="test_token")
        with pytest.raises(NotFoundError):
            client.get("/pages/notexist")
        client.close()

    @respx.mock
    def test_429_retries(self):
        """Client retries on 429 rate limit response."""
        call_count = 0

        def rate_limit_then_success(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(429, json={"message": "rate limited"}, headers={"retry-after": "0.01"})
            return httpx.Response(200, json={"id": "user1", "name": "Bot"})

        respx.get("https://api.notion.com/v1/users/me").mock(side_effect=rate_limit_then_success)
        client = NotionClient(token="test_token")
        result = client.get("/users/me")
        assert result["name"] == "Bot"
        assert call_count == 2
        client.close()


class TestAuthCommands:
    def test_auth_test_success(self, runner):
        with respx.mock:
            respx.get("https://api.notion.com/v1/users/me").mock(
                return_value=httpx.Response(200, json={"name": "Test Bot", "type": "bot"})
            )
            result = runner.invoke(cli, ["auth", "test", "--token", "secret_test"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["status"] == "ok"

    def test_auth_test_invalid_token(self, runner):
        with respx.mock:
            respx.get("https://api.notion.com/v1/users/me").mock(
                return_value=httpx.Response(401, json={"message": "API token is invalid."})
            )
            result = runner.invoke(cli, ["auth", "test", "--token", "invalid"])
            assert result.exit_code == 1
