"""Tests for notion user commands."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


USER_ID = "abcdef1234567890abcdef1234560000"

SAMPLE_USER = {
    "object": "user",
    "id": USER_ID,
    "name": "Test User",
    "type": "person",
}

USERS_LIST = {
    "object": "list",
    "results": [SAMPLE_USER],
    "has_more": False,
    "next_cursor": None,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestUser:
    @respx.mock
    def test_user_list(self, runner):
        respx.get("https://api.notion.com/v1/users").mock(
            return_value=httpx.Response(200, json=USERS_LIST)
        )
        result = runner.invoke(cli, ["user", "list"], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1

    @respx.mock
    def test_user_get(self, runner):
        respx.get(f"https://api.notion.com/v1/users/{USER_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_USER)
        )
        result = runner.invoke(cli, ["user", "get", USER_ID], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "Test User"

    @respx.mock
    def test_user_me(self, runner):
        respx.get("https://api.notion.com/v1/users/me").mock(
            return_value=httpx.Response(200, json=SAMPLE_USER)
        )
        result = runner.invoke(cli, ["user", "me"], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "person"
