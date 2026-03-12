"""Tests for notion db query command."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


DB_ID = "abcdef1234567890abcdef1234567890"

SAMPLE_QUERY_RESPONSE = {
    "object": "list",
    "results": [
        {
            "id": "page1id00000000000000000000000000",
            "object": "page",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Test Page", "type": "text", "text": {"content": "Test Page"}}]
                },
                "Status": {
                    "type": "select",
                    "select": {"name": "Active"}
                },
            }
        }
    ],
    "has_more": False,
    "next_cursor": None,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestDbQuery:
    @respx.mock
    def test_query_json_output(self, runner):
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUERY_RESPONSE)
        )
        result = runner.invoke(cli, ["db", "query", DB_ID], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1

    @respx.mock
    def test_query_ids_output(self, runner):
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUERY_RESPONSE)
        )
        result = runner.invoke(
            cli, ["db", "query", DB_ID, "--output", "ids"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        assert "page1id" in result.output

    @respx.mock
    def test_query_with_limit(self, runner):
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUERY_RESPONSE)
        )
        result = runner.invoke(
            cli, ["db", "query", DB_ID, "--limit", "1"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) <= 1

    @respx.mock
    def test_query_with_filter(self, runner):
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUERY_RESPONSE)
        )
        result = runner.invoke(
            cli, ["db", "query", DB_ID, "--filter", "Status:=:Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_query_pagination(self, runner):
        """Test --page-all paginates through all results."""
        page1 = {
            "object": "list",
            "results": [{"id": "page1", "object": "page", "properties": {}}],
            "has_more": True,
            "next_cursor": "cursor_abc",
        }
        page2 = {
            "object": "list",
            "results": [{"id": "page2", "object": "page", "properties": {}}],
            "has_more": False,
            "next_cursor": None,
        }
        responses = iter([
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ])
        respx.post(f"https://api.notion.com/v1/databases/{DB_ID}/query").mock(
            side_effect=lambda req: next(responses)
        )
        result = runner.invoke(
            cli, ["db", "query", DB_ID, "--page-all"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
