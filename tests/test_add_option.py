"""Tests for notion db add-option command."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner

from notion.cli import cli


DB_ID = "abcdef1234567890abcdef1234567890"

SCHEMA_WITH_SELECT = {
    "object": "database",
    "id": DB_ID,
    "properties": {
        "Name": {"type": "title", "title": {}},
        "Status": {
            "type": "select",
            "select": {
                "options": [{"name": "Active", "color": "green", "id": "opt1"}]
            }
        },
    }
}

PATCHED_DB = {
    "object": "database",
    "id": DB_ID,
    "properties": {
        "Name": {"type": "title", "title": {}},
        "Status": {
            "type": "select",
            "select": {
                "options": [
                    {"name": "Active", "color": "green", "id": "opt1"},
                    {"name": "Done", "color": "default"},
                ]
            }
        },
    }
}


@pytest.fixture
def runner():
    return CliRunner()


class TestAddOption:
    @respx.mock
    def test_add_new_option(self, runner):
        """Adding a new option calls PATCH and returns added status."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA_WITH_SELECT)
        )
        respx.patch(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=PATCHED_DB)
        )
        result = runner.invoke(
            cli, ["db", "add-option", DB_ID, "Status", "--option", "Done"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["results"]["Done"] == "added"

    @respx.mock
    def test_already_exists_no_api_call(self, runner):
        """If option already exists, returns already_exists without PATCH."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA_WITH_SELECT)
        )
        # No PATCH mock — if PATCH is called, test will fail
        result = runner.invoke(
            cli, ["db", "add-option", DB_ID, "Status", "--option", "Active"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["results"]["Active"] == "already_exists"

    @respx.mock
    def test_multiple_options(self, runner):
        """Multiple --option flags in one call."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA_WITH_SELECT)
        )
        respx.patch(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=PATCHED_DB)
        )
        result = runner.invoke(
            cli, ["db", "add-option", DB_ID, "Status", "--option", "Done", "--option", "Archived"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["results"]["Done"] == "added"
        assert data["results"]["Archived"] == "added"

    @respx.mock
    def test_mixed_existing_and_new(self, runner):
        """Mix of existing and new options."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA_WITH_SELECT)
        )
        respx.patch(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=PATCHED_DB)
        )
        result = runner.invoke(
            cli, ["db", "add-option", DB_ID, "Status", "--option", "Active", "--option", "Done"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["results"]["Active"] == "already_exists"
        assert data["results"]["Done"] == "added"

    @respx.mock
    def test_wrong_property_type_exits_3(self, runner):
        """Non-select property → exit 3."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA_WITH_SELECT)
        )
        result = runner.invoke(
            cli, ["db", "add-option", DB_ID, "Name", "--option", "value"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == 3
