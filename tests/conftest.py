import pytest
import tempfile
import pathlib


@pytest.fixture
def mock_token():
    return "secret_test_token_abcdef1234567890"


@pytest.fixture
def sample_db_id():
    return "abcdef1234567890abcdef1234567890"


@pytest.fixture
def sample_page_id():
    return "fedcba0987654321fedcba0987654321"


@pytest.fixture(autouse=True)
def isolate_schema_cache(tmp_path, monkeypatch):
    """Redirect schema cache to a temp directory for all tests."""
    import notion.schema as schema_module
    monkeypatch.setattr(schema_module, "CACHE_DIR", tmp_path / "schemas")
