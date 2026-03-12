"""Tests for notion page commands."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


PAGE_ID = "fedcba0987654321fedcba0987654321"
DB_ID = "abcdef1234567890abcdef1234567890"

SAMPLE_PAGE = {
    "object": "page",
    "id": PAGE_ID,
    "archived": False,
    "parent": {"type": "page_id", "page_id": "parent000000000000000000000000000"},
    "properties": {
        "title": {
            "type": "title",
            "title": [{"plain_text": "My Page", "type": "text", "text": {"content": "My Page"}}]
        }
    }
}

DB_PAGE = {
    "object": "page",
    "id": PAGE_ID,
    "archived": False,
    "parent": {"type": "database_id", "database_id": DB_ID},
    "properties": {
        "Name": {
            "type": "title",
            "title": [{"plain_text": "My Entry", "type": "text", "text": {"content": "My Entry"}}]
        },
        "Status": {
            "type": "select",
            "select": {"name": "Active"}
        }
    }
}

SCHEMA = {
    "object": "database",
    "id": DB_ID,
    "properties": {
        "Name": {"type": "title", "title": {}},
        "Status": {"type": "select", "select": {"options": [{"name": "Active"}]}},
    }
}


@pytest.fixture
def runner():
    return CliRunner()


class TestPageCreate:
    @respx.mock
    def test_create_page(self, runner):
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "create", "parent000000000000000000000000000", "--title", "My Page"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == PAGE_ID

    @respx.mock
    def test_create_page_output_id(self, runner):
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "create", "parent000000000000000000000000000", "--title", "My Page", "--output", "id"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        assert result.output.strip() == PAGE_ID


class TestPageGet:
    @respx.mock
    def test_get_page_json(self, runner):
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "get", PAGE_ID],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == PAGE_ID

    @respx.mock
    def test_get_page_properties(self, runner):
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "get", PAGE_ID, "--output", "properties"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "id" in data

    @respx.mock
    def test_get_page_not_found(self, runner):
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(404, json={"message": "Page not found"})
        )
        result = runner.invoke(
            cli, ["page", "get", PAGE_ID],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 2


class TestPageGetProperty:
    @respx.mock
    def test_get_property(self, runner):
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=DB_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "get-property", PAGE_ID, "Status"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "select"

    @respx.mock
    def test_get_property_not_found(self, runner):
        respx.get(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json=DB_PAGE)
        )
        result = runner.invoke(
            cli, ["page", "get-property", PAGE_ID, "NonExistent"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 2


class TestPageDelete:
    @respx.mock
    def test_delete_page_with_confirm_flag(self, runner):
        respx.patch(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json={**SAMPLE_PAGE, "archived": True})
        )
        result = runner.invoke(
            cli, ["page", "delete", PAGE_ID, "--confirm"],
            env={"NOTION_API_KEY": "test_token", "NOTION_MODE": "ci"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "archived"


class TestPageRestore:
    @respx.mock
    def test_restore_page(self, runner):
        respx.patch(f"https://api.notion.com/v1/pages/{PAGE_ID}").mock(
            return_value=httpx.Response(200, json={**SAMPLE_PAGE, "archived": False})
        )
        result = runner.invoke(
            cli, ["page", "restore", PAGE_ID],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "restored"


class TestPageAppend:
    @respx.mock
    def test_append_markdown(self, runner):
        respx.patch(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children").mock(
            return_value=httpx.Response(200, json={"object": "list", "results": []})
        )
        result = runner.invoke(
            cli, ["page", "append", PAGE_ID, "--data", "## Hello\n- Item 1"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_append_json_blocks(self, runner):
        blocks = json.dumps([{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Hello"}}]}}])
        respx.patch(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children").mock(
            return_value=httpx.Response(200, json={"object": "list", "results": []})
        )
        result = runner.invoke(
            cli, ["page", "append", PAGE_ID, "--data", blocks],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
