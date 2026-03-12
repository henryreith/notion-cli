"""Tests for notion comment commands."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


PAGE_ID = "fedcba0987654321fedcba0987654321"
COMMENT_ID = "c0ffee00000000000000000000000000"

SAMPLE_COMMENT = {
    "object": "comment",
    "id": COMMENT_ID,
    "parent": {"type": "page_id", "page_id": PAGE_ID},
    "rich_text": [{"plain_text": "Hello comment", "type": "text"}],
}

COMMENTS_LIST = {
    "object": "list",
    "results": [SAMPLE_COMMENT],
    "has_more": False,
    "next_cursor": None,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestComment:
    @respx.mock
    def test_comment_add(self, runner):
        respx.post("https://api.notion.com/v1/comments").mock(
            return_value=httpx.Response(200, json=SAMPLE_COMMENT)
        )
        result = runner.invoke(
            cli, ["comment", "add", PAGE_ID, "Hello comment"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == COMMENT_ID

    @respx.mock
    def test_comment_list(self, runner):
        respx.get("https://api.notion.com/v1/comments").mock(
            return_value=httpx.Response(200, json=COMMENTS_LIST)
        )
        result = runner.invoke(
            cli, ["comment", "list", PAGE_ID],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
