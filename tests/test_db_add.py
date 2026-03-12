"""Tests for notion db add command."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


DB_ID = "abcdef1234567890abcdef1234567890"

SAMPLE_SCHEMA = {
    "object": "database",
    "id": DB_ID,
    "properties": {
        "Name": {"type": "title", "title": {}},
        "Status": {
            "type": "select",
            "select": {"options": [{"name": "Active", "color": "green"}]}
        },
        "Tags": {
            "type": "multi_select",
            "multi_select": {"options": [{"name": "python", "color": "blue"}]}
        },
        "Count": {"type": "number", "number": {}},
    }
}

CREATED_PAGE = {
    "object": "page",
    "id": "newpage00000000000000000000000000",
    "properties": {
        "Name": {"type": "title", "title": [{"plain_text": "My Page"}]},
    }
}


@pytest.fixture
def runner():
    return CliRunner()


class TestDbAdd:
    @respx.mock
    def test_add_key_value_args(self, runner):
        """Add with KEY=VALUE positional args."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "Name=My Page", "Status=Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "newpage00000000000000000000000000"

    @respx.mock
    def test_add_data_json(self, runner):
        """Add with --data inline JSON."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "--data", '{"Name": "My Page"}'],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_add_data_file(self, runner, tmp_path):
        """Add with --data @file."""
        data_file = tmp_path / "data.json"
        data_file.write_text('{"Name": "From File"}')

        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "--data", f"@{data_file}"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0

    @respx.mock
    def test_add_output_id(self, runner):
        """--output id returns just the page ID."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "Name=My Page", "--output", "id"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        assert result.output.strip() == "newpage00000000000000000000000000"

    @respx.mock
    def test_add_unknown_property_exits_3(self, runner):
        """Unknown property name → exit code 3."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "NonExistentProp=value"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 3

    @respx.mock
    def test_add_multi_select_comma_separated(self, runner):
        """Multi-select accepts comma-separated values."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SAMPLE_SCHEMA)
        )

        posted_body = {}
        def capture_post(request):
            nonlocal posted_body
            posted_body = json.loads(request.content)
            return httpx.Response(200, json=CREATED_PAGE)

        respx.post("https://api.notion.com/v1/pages").mock(side_effect=capture_post)

        result = runner.invoke(
            cli, ["db", "add", DB_ID, "Name=Test", "Tags=python,testing"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        tags = posted_body["properties"]["Tags"]["multi_select"]
        assert {"name": "python"} in tags
        assert {"name": "testing"} in tags

    @respx.mock
    def test_add_no_properties_fails(self, runner):
        """No properties → non-zero exit."""
        result = runner.invoke(
            cli, ["db", "add", DB_ID],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code != 0

    @respx.mock
    def test_add_auth_error_exits_1(self, runner):
        """401 → exit code 1."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(401, json={"message": "Invalid token"})
        )
        result = runner.invoke(
            cli, ["db", "add", DB_ID, "Name=Test"],
            env={"NOTION_API_KEY": "bad_token"}
        )
        assert result.exit_code == 1
