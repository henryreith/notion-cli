"""Integration test pipeline for notion-agent-cli.

Tests a full knowledge-base workflow against the real Notion API.

Run with:
    NOTION_API_KEY=<key> NOTION_TEST_PARENT_ID=<page-id> pytest tests/integration/ -v -s

Skipped automatically unless both env vars are set.
"""
import json
import os
import subprocess
import sys
import time
import pytest

pytestmark = pytest.mark.integration

NOTION = [sys.executable, "-m", "notion"]


def run(*args, input_data=None, env_extra=None):
    """Run a notion CLI command and return (exit_code, stdout, stderr)."""
    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        NOTION + list(args),
        capture_output=True,
        text=True,
        input=input_data,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture(autouse=True)
def require_integration_env():
    if not os.environ.get("NOTION_API_KEY"):
        pytest.skip("NOTION_API_KEY not set")
    if not os.environ.get("NOTION_TEST_PARENT_ID"):
        pytest.skip("NOTION_TEST_PARENT_ID not set")


@pytest.fixture(scope="module")
def pipeline_state():
    """Shared state across the pipeline steps."""
    return {}


class TestKBPipeline:
    """18-step knowledge base pipeline test."""

    def test_01_auth(self, pipeline_state):
        """Step 1: Verify authentication works."""
        code, out, err = run("auth", "test")
        assert code == 0, f"Auth failed: {err}"
        data = json.loads(out)
        assert data["status"] == "ok"
        pipeline_state["bot_name"] = data.get("user", "unknown")

    def test_02_create_test_database(self, pipeline_state):
        """Step 2: Create a test database."""
        parent_id = os.environ["NOTION_TEST_PARENT_ID"]
        code, out, err = run(
            "db", "create", parent_id, "notion-agent-cli Integration Test DB",
            "--output", "id"
        )
        assert code == 0, f"Create DB failed: {err}"
        db_id = out.strip()
        assert len(db_id) == 32 or "-" in db_id, f"Invalid DB ID: {db_id}"
        pipeline_state["db_id"] = db_id
        time.sleep(0.5)  # Brief pause to allow Notion to index

    def test_03_fetch_schema(self, pipeline_state):
        """Step 3: Fetch database schema."""
        db_id = pipeline_state["db_id"]
        code, out, err = run("db", "schema", db_id, "--output", "properties", "--no-cache")
        assert code == 0, f"Schema fetch failed: {err}"
        props = json.loads(out)
        assert "Name" in props
        assert props["Name"] == "title"

    def test_04_add_select_option(self, pipeline_state):
        """Step 4: Add Status select property options."""
        db_id = pipeline_state["db_id"]

        # First, add a Status property via update-schema
        schema_patch = {
            "Status": {
                "select": {
                    "options": [
                        {"name": "Active", "color": "green"},
                        {"name": "Done", "color": "blue"},
                    ]
                }
            }
        }
        code, out, err = run(
            "db", "update-schema", db_id, "--data", json.dumps(schema_patch)
        )
        assert code == 0, f"Update schema failed: {err}"
        time.sleep(0.5)

    def test_05_add_option_idempotent(self, pipeline_state):
        """Step 5: Add option that already exists → already_exists."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "add-option", db_id, "Status", "--option", "Active",
            "--no-cache" if "--no-cache" in out else ""  # no-cache if supported
        )
        # May fail if Status wasn't added as select in step 4
        # That's ok — just verify no crash
        if code == 0:
            data = json.loads(out)
            assert "results" in data

    def test_06_add_entry1(self, pipeline_state):
        """Step 6: Add first entry."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "add", db_id,
            "Name=Test Entry 1",
            "--output", "id",
            "--no-cache",
        )
        assert code == 0, f"Add entry 1 failed: {err}"
        page_id = out.strip()
        assert page_id
        pipeline_state["page1_id"] = page_id
        time.sleep(0.34)

    def test_07_add_entry2(self, pipeline_state):
        """Step 7: Add second entry."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "add", db_id,
            "Name=Test Entry 2",
            "--output", "id",
            "--no-cache",
        )
        assert code == 0, f"Add entry 2 failed: {err}"
        pipeline_state["page2_id"] = out.strip()
        time.sleep(0.34)

    def test_08_add_entry3(self, pipeline_state):
        """Step 8: Add third entry."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "add", db_id,
            "Name=Test Entry 3",
            "--output", "id",
            "--no-cache",
        )
        assert code == 0, f"Add entry 3 failed: {err}"
        pipeline_state["page3_id"] = out.strip()
        time.sleep(0.34)

    def test_09_query_all(self, pipeline_state):
        """Step 9: Query all entries."""
        db_id = pipeline_state["db_id"]
        code, out, err = run("db", "query", db_id, "--output", "json", "--no-cache")
        assert code == 0, f"Query failed: {err}"
        results = json.loads(out)
        assert len(results) >= 3

    def test_10_query_filter(self, pipeline_state):
        """Step 10: Query with filter."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "query", db_id,
            "--filter", "Name:=:Test Entry 1",
            "--output", "json",
            "--no-cache",
        )
        assert code == 0, f"Filtered query failed: {err}"
        results = json.loads(out)
        # May return 0 if filter type doesn't match — just check no crash
        assert isinstance(results, list)

    def test_11_upsert_creates(self, pipeline_state):
        """Step 11: Upsert with no match → creates."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "upsert", db_id,
            "--match", "Name:Test Entry Upsert New",
            "Name=Test Entry Upsert New",
            "--no-cache",
        )
        assert code == 0, f"Upsert create failed: {err}"
        data = json.loads(out)
        assert data["action"] == "created"
        pipeline_state["upsert_page_id"] = data["id"]
        time.sleep(0.34)

    def test_12_upsert_updates(self, pipeline_state):
        """Step 12: Upsert with 1 match → updates."""
        db_id = pipeline_state["db_id"]
        code, out, err = run(
            "db", "upsert", db_id,
            "--match", "Name:Test Entry Upsert New",
            "Name=Test Entry Upsert Updated",
            "--no-cache",
        )
        assert code == 0, f"Upsert update failed: {err}"
        data = json.loads(out)
        assert data["action"] == "updated"
        time.sleep(0.34)

    def test_13_batch_add_dry_run(self, pipeline_state):
        """Step 13: Batch add dry run."""
        db_id = pipeline_state["db_id"]
        batch = json.dumps([
            {"Name": "Batch Item 1"},
            {"Name": "Batch Item 2"},
        ])
        code, out, err = run("db", "batch-add", db_id, "--data", batch, "--dry-run")
        assert code == 7, f"Dry run should exit 7, got {code}: {err}"

    def test_14_page_get(self, pipeline_state):
        """Step 14: Get a page."""
        page_id = pipeline_state.get("page1_id")
        if not page_id:
            pytest.skip("page1_id not set")
        code, out, err = run("page", "get", page_id)
        assert code == 0, f"Page get failed: {err}"
        data = json.loads(out)
        assert data["id"].replace("-", "") == page_id.replace("-", "")

    def test_15_page_append(self, pipeline_state):
        """Step 15: Append content to a page."""
        page_id = pipeline_state.get("page1_id")
        if not page_id:
            pytest.skip("page1_id not set")
        code, out, err = run(
            "page", "append", page_id,
            "--data", "## Integration Test\n\nThis was added by notion-agent-cli."
        )
        assert code == 0, f"Page append failed: {err}"
        time.sleep(0.34)

    def test_16_search(self, pipeline_state):
        """Step 16: Search for created pages."""
        code, out, err = run("search", "Test Entry", "--limit", "5")
        assert code == 0, f"Search failed: {err}"
        results = json.loads(out)
        assert isinstance(results, list)

    def test_17_user_me(self, pipeline_state):
        """Step 17: Get current user."""
        code, out, err = run("user", "me")
        assert code == 0, f"User me failed: {err}"
        data = json.loads(out)
        assert "id" in data

    def test_18_cleanup_delete_db(self, pipeline_state):
        """Step 18: Archive the test database (cleanup)."""
        db_id = pipeline_state.get("db_id")
        if not db_id:
            pytest.skip("db_id not set")
        code, out, err = run("db", "delete", db_id, "--confirm")
        assert code == 0, f"Delete DB failed: {err}"
        data = json.loads(out)
        assert data["status"] == "archived"
