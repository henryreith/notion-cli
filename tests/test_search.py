"""Tests for notion search command."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


SEARCH_RESPONSE = {
    "object": "list",
    "results": [
        {"object": "page", "id": "page1000000000000000000000000001"},
        {"object": "database", "id": "db10000000000000000000000000001"},
    ],
    "has_more": False,
    "next_cursor": None,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestSearch:
    @respx.mock
    def test_search_basic(self, runner):
        respx.post("https://api.notion.com/v1/search").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        result = runner.invoke(
            cli, ["search", "my query"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    @respx.mock
    def test_search_with_type_filter(self, runner):
        respx.post("https://api.notion.com/v1/search").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        result = runner.invoke(
            cli, ["search", "my query", "--type", "page"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_search_ids_output(self, runner):
        respx.post("https://api.notion.com/v1/search").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        result = runner.invoke(
            cli, ["search", "--output", "ids"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        assert "page1000" in result.output

    @respx.mock
    def test_search_empty_query(self, runner):
        respx.post("https://api.notion.com/v1/search").mock(
            return_value=httpx.Response(200, json=SEARCH_RESPONSE)
        )
        result = runner.invoke(cli, ["search"], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
