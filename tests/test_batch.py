"""Tests for notion db batch-add command."""
import json
import pytest
import respx
import httpx
from click.testing import CliRunner
from unittest.mock import patch

from notion.cli import cli
from notion.errors import ExitCode


DB_ID = "abcdef1234567890abcdef1234567890"

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
    "id": "newpage00000000000000000000000001",
    "properties": {}
}


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def batch_data():
    return [
        {"Name": "Item 1", "Status": "Active"},
        {"Name": "Item 2", "Status": "Active"},
        {"Name": "Item 3", "Status": "Active"},
    ]


class TestBatchAdd:
    @respx.mock
    def test_batch_add_from_json_array(self, runner, batch_data):
        """Batch add from inline JSON array."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )

        with patch("time.sleep"):  # Skip rate limit delay in tests
            result = runner.invoke(
                cli, ["db", "batch-add", DB_ID, "--data", json.dumps(batch_data)],
                env={"NOTION_API_KEY": "test_token"}
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["total"] == 3
        assert len(data["created"]) == 3

    @respx.mock
    def test_batch_add_from_file(self, runner, batch_data, tmp_path):
        """Batch add from @file."""
        data_file = tmp_path / "batch.json"
        data_file.write_text(json.dumps(batch_data))

        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )

        with patch("time.sleep"):
            result = runner.invoke(
                cli, ["db", "batch-add", DB_ID, "--data", f"@{data_file}"],
                env={"NOTION_API_KEY": "test_token"}
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["total"] == 3

    @respx.mock
    def test_dry_run_exits_7(self, runner, batch_data):
        """--dry-run validates only and exits 7."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        result = runner.invoke(
            cli, ["db", "batch-add", DB_ID, "--data", json.dumps(batch_data), "--dry-run"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == ExitCode.DRY_RUN

    @respx.mock
    def test_dry_run_with_invalid_row_exits_7(self, runner):
        """--dry-run with invalid row still exits 7 (reports errors)."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        bad_data = [{"Name": "Valid"}, {"NonExistentProp": "bad"}]
        result = runner.invoke(
            cli, ["db", "batch-add", DB_ID, "--data", json.dumps(bad_data), "--dry-run"],
            env={"NOTION_API_KEY": "test_token"}
        )
        assert result.exit_code == ExitCode.DRY_RUN
        # Output goes to stdout before the DryRunError causes handle_error to print to stderr
        # The dry_run result is printed before the error
        assert "dry_run" in result.stdout

    @respx.mock
    def test_continue_on_error(self, runner):
        """--continue-on-error skips failed rows and continues."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )

        call_count = 0
        def handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return httpx.Response(400, json={"message": "Bad request"})
            return httpx.Response(200, json=CREATED_PAGE)

        respx.post("https://api.notion.com/v1/pages").mock(side_effect=handler)

        data = [{"Name": "Good 1"}, {"Name": "Bad Item"}, {"Name": "Good 2"}]

        # Pre-validate: "Bad Item" would fail API but pass validation
        # We need a real validation failure - use unknown property
        data_with_bad = [{"Name": "Good 1"}, {"NonExistent": "bad"}, {"Name": "Good 2"}]

        with patch("time.sleep"):
            result = runner.invoke(
                cli, ["db", "batch-add", DB_ID, "--data", json.dumps(data_with_bad), "--continue-on-error"],
                env={"NOTION_API_KEY": "test_token"}
            )

        assert result.exit_code == 0
        data_out = json.loads(result.stdout)
        assert len(data_out["errors"]) >= 1

    @respx.mock
    def test_rate_limiting_sleep(self, runner, batch_data):
        """Verify time.sleep is called between requests."""
        respx.get(f"https://api.notion.com/v1/databases/{DB_ID}").mock(
            return_value=httpx.Response(200, json=SCHEMA)
        )
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(200, json=CREATED_PAGE)
        )

        sleep_calls = []
        with patch("time.sleep", side_effect=lambda d: sleep_calls.append(d)):
            result = runner.invoke(
                cli, ["db", "batch-add", DB_ID, "--data", json.dumps(batch_data)],
                env={"NOTION_API_KEY": "test_token"}
            )

        assert result.exit_code == 0
        # Should sleep between each request (N-1 times for N items)
        assert len(sleep_calls) == len(batch_data) - 1
        assert all(abs(s - 0.34) < 0.01 for s in sleep_calls)
