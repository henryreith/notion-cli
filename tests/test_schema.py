"""Tests for SchemaCache and PropertyResolver."""
import json
import time
from pathlib import Path
import pytest

from notion.schema import SchemaCache, PropertyResolver, CACHE_TTL
from notion.errors import ValidationError


SAMPLE_SCHEMA = {
    "Name": {"type": "title", "title": {}},
    "Status": {"type": "select", "select": {"options": [
        {"name": "Active", "color": "green"},
        {"name": "Done", "color": "blue"},
    ]}},
    "Tags": {"type": "multi_select", "multi_select": {"options": []}},
    "Priority": {"type": "select", "select": {"options": []}},
    "Count": {"type": "number", "number": {"format": "number"}},
    "Done": {"type": "checkbox", "checkbox": {}},
    "URL": {"type": "url", "url": {}},
    "Notes": {"type": "rich_text", "rich_text": {}},
    "Due": {"type": "date", "date": {}},
}


class TestSchemaCache:
    def test_miss_on_empty(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        assert cache.get("abc123") is None

    def test_set_and_get(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        cache.set("abc123", SAMPLE_SCHEMA)
        retrieved = cache.get("abc123")
        assert retrieved == SAMPLE_SCHEMA

    def test_ttl_expiry(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        db_id = "abc123"
        # Write with old timestamp
        path = cache._path(db_id)
        tmp_path.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "cached_at": time.time() - CACHE_TTL - 1,
            "schema": SAMPLE_SCHEMA,
        }))
        assert cache.get(db_id) is None  # expired

    def test_invalidate(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        cache.set("abc123", SAMPLE_SCHEMA)
        cache.invalidate("abc123")
        assert cache.get("abc123") is None

    def test_normalises_id_with_hyphens(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        cache.set("abc-def-1234", SAMPLE_SCHEMA)
        # Should retrieve by same ID regardless of hyphen format
        assert cache.get("abcdef1234") is not None or cache.get("abc-def-1234") is not None

    def test_invalid_json_returns_none(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        db_id = "abc123"
        path = cache._path(db_id)
        tmp_path.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json{{{")
        assert cache.get(db_id) is None

    def test_set_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        cache = SchemaCache(cache_dir=nested)
        cache.set("abc123", SAMPLE_SCHEMA)
        assert cache.get("abc123") == SAMPLE_SCHEMA

    def test_invalidate_nonexistent_is_noop(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        # Should not raise
        cache.invalidate("doesnotexist")

    def test_fresh_cache_not_expired(self, tmp_path):
        cache = SchemaCache(cache_dir=tmp_path)
        cache.set("abc123", SAMPLE_SCHEMA)
        result = cache.get("abc123")
        assert result is not None


class TestPropertyResolver:
    def setup_method(self):
        self.resolver = PropertyResolver()

    def test_resolve_title(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Name": "My Page"})
        assert result["Name"] == {"title": [{"type": "text", "text": {"content": "My Page"}}]}

    def test_resolve_select(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Status": "Active"})
        assert result["Status"] == {"select": {"name": "Active"}}

    def test_resolve_multi_select_string(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Tags": "python,testing"})
        assert result["Tags"] == {"multi_select": [{"name": "python"}, {"name": "testing"}]}

    def test_resolve_multi_select_list(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Tags": ["python", "testing"]})
        assert result["Tags"] == {"multi_select": [{"name": "python"}, {"name": "testing"}]}

    def test_resolve_number(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Count": "42"})
        assert result["Count"] == {"number": 42}

    def test_resolve_checkbox_true(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Done": "true"})
        assert result["Done"] == {"checkbox": True}

    def test_resolve_checkbox_false(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Done": "false"})
        assert result["Done"] == {"checkbox": False}

    def test_resolve_url(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"URL": "https://example.com"})
        assert result["URL"] == {"url": "https://example.com"}

    def test_resolve_rich_text(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Notes": "Some notes"})
        assert result["Notes"] == {"rich_text": [{"type": "text", "text": {"content": "Some notes"}}]}

    def test_resolve_date(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"Due": "2024-01-15"})
        assert result["Due"] == {"date": {"start": "2024-01-15", "end": None}}

    def test_unknown_property_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            self.resolver.resolve_all(SAMPLE_SCHEMA, {"NonExistent": "value"})
        assert "NonExistent" in str(exc_info.value)

    def test_case_insensitive_property_matching(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {"name": "My Page"})
        assert "Name" in result

    def test_multiple_properties(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {
            "Name": "Test",
            "Status": "Active",
            "Count": "5",
        })
        assert len(result) == 3
        assert result["Name"]["title"][0]["text"]["content"] == "Test"

    def test_validation_error_includes_available_props(self):
        with pytest.raises(ValidationError) as exc_info:
            self.resolver.resolve_all(SAMPLE_SCHEMA, {"Bogus": "value"})
        assert exc_info.value.data.get("available") is not None

    def test_resolve_empty_data_returns_empty_dict(self):
        result = self.resolver.resolve_all(SAMPLE_SCHEMA, {})
        assert result == {}


class TestCoerceFunctions:
    """Test individual coerce functions."""

    def test_coerce_multi_select_preserves_case(self):
        from notion.coerce import coerce_multi_select
        result = coerce_multi_select("Python,JavaScript,TypeScript")
        names = [item["name"] for item in result["multi_select"]]
        assert names == ["Python", "JavaScript", "TypeScript"]

    def test_coerce_multi_select_strips_whitespace(self):
        from notion.coerce import coerce_multi_select
        result = coerce_multi_select("a, b, c")
        names = [item["name"] for item in result["multi_select"]]
        assert names == ["a", "b", "c"]

    def test_coerce_relation_single(self):
        from notion.coerce import coerce_relation
        result = coerce_relation("550e8400e29b41d4a716446655440000")
        assert result == {"relation": [{"id": "550e8400e29b41d4a716446655440000"}]}

    def test_coerce_relation_multiple(self):
        from notion.coerce import coerce_relation
        result = coerce_relation(["550e8400e29b41d4a716446655440000", "abcdef1234567890abcdef1234567890"])
        assert len(result["relation"]) == 2

    def test_coerce_people_single(self):
        from notion.coerce import coerce_people
        result = coerce_people("550e8400e29b41d4a716446655440000")
        assert result == {"people": [{"object": "user", "id": "550e8400e29b41d4a716446655440000"}]}

    def test_coerce_date_range(self):
        from notion.coerce import coerce_date
        result = coerce_date("2024-01-15/2024-01-20")
        assert result == {"date": {"start": "2024-01-15", "end": "2024-01-20"}}

    def test_coerce_checkbox_variants(self):
        from notion.coerce import coerce_checkbox
        assert coerce_checkbox("yes") == {"checkbox": True}
        assert coerce_checkbox("no") == {"checkbox": False}
        assert coerce_checkbox("1") == {"checkbox": True}
        assert coerce_checkbox("0") == {"checkbox": False}
        assert coerce_checkbox(True) == {"checkbox": True}
        assert coerce_checkbox(False) == {"checkbox": False}

    def test_coerce_number_int(self):
        from notion.coerce import coerce_number
        assert coerce_number("42") == {"number": 42}

    def test_coerce_number_float(self):
        from notion.coerce import coerce_number
        assert coerce_number("3.14") == {"number": 3.14}

    def test_markdown_to_blocks_heading2(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("## My Heading")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"
        assert blocks[0]["heading_2"]["rich_text"][0]["text"]["content"] == "My Heading"

    def test_markdown_to_blocks_heading3(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("### Sub Heading")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"

    def test_markdown_to_blocks_bullet(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("- Item one\n- Item two")
        assert len(blocks) == 2
        assert all(b["type"] == "bulleted_list_item" for b in blocks)

    def test_markdown_to_blocks_numbered_list(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("1. First\n2. Second")
        assert len(blocks) == 2
        assert all(b["type"] == "numbered_list_item" for b in blocks)

    def test_markdown_to_blocks_quote(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("> A quote")
        assert blocks[0]["type"] == "quote"

    def test_markdown_to_blocks_divider(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("---")
        assert blocks[0]["type"] == "divider"

    def test_markdown_to_blocks_code(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("```python\nprint('hello')\n```")
        assert blocks[0]["type"] == "code"
        assert "print" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_markdown_to_blocks_paragraph(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("Just a plain paragraph.")
        assert blocks[0]["type"] == "paragraph"

    def test_coerce_email(self):
        from notion.coerce import coerce_email
        assert coerce_email("user@example.com") == {"email": "user@example.com"}

    def test_coerce_phone_number(self):
        from notion.coerce import coerce_phone_number
        assert coerce_phone_number("+1-555-867-5309") == {"phone_number": "+1-555-867-5309"}

    def test_coerce_status(self):
        from notion.coerce import coerce_status
        assert coerce_status("In Progress") == {"status": {"name": "In Progress"}}

    def test_coerce_url(self):
        from notion.coerce import coerce_url
        assert coerce_url("https://example.com") == {"url": "https://example.com"}

    def test_coerce_value_unknown_type_raises(self):
        from notion.coerce import coerce_value
        with pytest.raises(ValueError, match="Unsupported property type"):
            coerce_value("unknown_type", "value")

    def test_coerce_select(self):
        from notion.coerce import coerce_select
        assert coerce_select("Active") == {"select": {"name": "Active"}}

    def test_coerce_title(self):
        from notion.coerce import coerce_title
        result = coerce_title("My Title")
        assert result == {"title": [{"type": "text", "text": {"content": "My Title"}}]}

    def test_coerce_rich_text(self):
        from notion.coerce import coerce_rich_text
        result = coerce_rich_text("Some text")
        assert result == {"rich_text": [{"type": "text", "text": {"content": "Some text"}}]}

    def test_coerce_checkbox_on_variant(self):
        from notion.coerce import coerce_checkbox
        assert coerce_checkbox("on") == {"checkbox": True}

    def test_coerce_multi_select_list_input(self):
        from notion.coerce import coerce_multi_select
        result = coerce_multi_select(["Alpha", "Beta"])
        assert result == {"multi_select": [{"name": "Alpha"}, {"name": "Beta"}]}

    def test_coerce_date_no_end(self):
        from notion.coerce import coerce_date
        result = coerce_date("2024-06-01")
        assert result == {"date": {"start": "2024-06-01", "end": None}}

    def test_markdown_to_blocks_empty_string(self):
        from notion.coerce import markdown_to_blocks
        blocks = markdown_to_blocks("")
        assert blocks == []

    def test_markdown_to_blocks_mixed(self):
        from notion.coerce import markdown_to_blocks
        text = "## Title\n- item\n> quote\n---\nParagraph"
        blocks = markdown_to_blocks(text)
        types = [b["type"] for b in blocks]
        assert types == ["heading_2", "bulleted_list_item", "quote", "divider", "paragraph"]
