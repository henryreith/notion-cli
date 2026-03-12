"""Tests for notion block commands."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


BLOCK_ID = "b10c0000000000000000000000000000"
PAGE_ID = "fedcba0987654321fedcba0987654321"

SAMPLE_BLOCK = {
    "object": "block",
    "id": BLOCK_ID,
    "type": "paragraph",
    "paragraph": {"rich_text": [{"plain_text": "Hello", "type": "text", "text": {"content": "Hello"}}]},
}

BLOCKS_LIST = {
    "object": "list",
    "results": [SAMPLE_BLOCK],
    "has_more": False,
    "next_cursor": None,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestBlock:
    @respx.mock
    def test_block_list(self, runner):
        respx.get(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children").mock(
            return_value=httpx.Response(200, json=BLOCKS_LIST)
        )
        result = runner.invoke(cli, ["block", "list", PAGE_ID], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1

    @respx.mock
    def test_block_get(self, runner):
        respx.get(f"https://api.notion.com/v1/blocks/{BLOCK_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_BLOCK)
        )
        result = runner.invoke(cli, ["block", "get", BLOCK_ID], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "paragraph"

    @respx.mock
    def test_block_append(self, runner):
        respx.patch(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children").mock(
            return_value=httpx.Response(200, json={"object": "list", "results": [SAMPLE_BLOCK]})
        )
        result = runner.invoke(
            cli, ["block", "append", PAGE_ID, "--text", "Hello world"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_block_delete(self, runner):
        respx.delete(f"https://api.notion.com/v1/blocks/{BLOCK_ID}").mock(
            return_value=httpx.Response(200, json={"id": BLOCK_ID, "archived": True})
        )
        result = runner.invoke(cli, ["block", "delete", BLOCK_ID], env={"NOTION_API_KEY": "test_token"})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "deleted"

    @respx.mock
    def test_block_list_ids_output(self, runner):
        respx.get(f"https://api.notion.com/v1/blocks/{PAGE_ID}/children").mock(
            return_value=httpx.Response(200, json=BLOCKS_LIST)
        )
        result = runner.invoke(
            cli, ["block", "list", PAGE_ID, "--output", "ids"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        assert BLOCK_ID in result.output
