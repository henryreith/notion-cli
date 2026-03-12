"""Tests for notion db upsert and update-row commands."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


DB_ID = "abcdef1234567890abcdef1234567890"
PAGE_ID = "fedcba0987654321fedcba0987654321"

SCHEMA = {
    "object": "database",
    "id": DB_ID,
    "properties": {
        "Name": {"type": "title", "title": {}},
        "Status": {"type": "select", "select": {"options": [{"name": "Active"}]}},
    }
}

CREATED_PAGE = {
    "object": "page",
    "id": PAGE_ID,
    "parent": {"type": "database_id", "database_id": DB_ID},
    "properties": {
        "Name": {"type": "title", "title": [{"plain_text": "My Page"}]},
    }
}

QUERY_EMPTY = {"object": "list", "results": [], "has_more": False, "next_cursor": None}
QUERY_ONE = {"object": "list", "results": [CREATED_PAGE], "has_more": False, "next_cursor": None}
QUERY_TWO = {"object": "list", "results": [CREATED_PAGE, {**CREATED_PAGE, "id": "other_page_id"}], "has_more": False, "next_cursor": None}


@pytest.fixture
def runner():
    return CliRunner()


class TestUpsert:
    @respx.mock
    def test_upsert_creates_when_no_match(self, runner):
        """0 matches → create."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=QUERY_EMPTY)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "upsert", DB_ID, "--match", "Name:My Page", "Name=My Page"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["action"] == "created"

    @respx.mock
    def test_upsert_updates_when_one_match(self, runner):
        """1 match → update."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=QUERY_ONE)
        )
        respx.patch(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "upsert", DB_ID, "--match", "Name:My Page", "Status=Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["action"] == "updated"

    @respx.mock
    def test_upsert_ambiguous_exits_6(self, runner):
        """2+ matches → exit 6."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=QUERY_TWO)
        )
        result = runner.invoke(
            cli, ["db", "upsert", DB_ID, "--match", "Name:My Page", "Status=Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 6


class TestUpdateRow:
    @respx.mock
    def test_update_row(self, runner):
        """Update existing page properties."""
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.patch(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "update-row", PAGE_ID, "Status=Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
