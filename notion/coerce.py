"""Property value coercion functions for Notion API payloads."""
from __future__ import annotations
import re


def coerce_title(value: str) -> dict:
    """Coerce a string to Notion title property format."""
    return {"title": [{"type": "text", "text": {"content": str(value)}}]}


def coerce_rich_text(value: str) -> dict:
    """Coerce a string to Notion rich_text property format."""
    return {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}


def coerce_select(value: str) -> dict:
    """Coerce a string to Notion select property format."""
    return {"select": {"name": str(value)}}


def coerce_multi_select(value: str | list) -> dict:
    """Coerce a comma-separated string or list to multi_select format.

    Case-sensitive: never lowercase option values.
    Accepts: "a,b,c" or ["a", "b", "c"]
    """
    if isinstance(value, list):
        names = value
    else:
        # Split on comma, strip whitespace but preserve case
        names = [v.strip() for v in str(value).split(",") if v.strip()]
    return {"multi_select": [{"name": name} for name in names]}


def coerce_date(value: str) -> dict:
    """Coerce a date string to Notion date property format.

    Accepts: "2024-01-15" or "2024-01-15/2024-01-20" (range)
    """
    if "/" in value:
        parts = value.split("/", 1)
        return {"date": {"start": parts[0].strip(), "end": parts[1].strip()}}
    return {"date": {"start": str(value), "end": None}}


def coerce_number(value: str | int | float) -> dict:
    """Coerce to Notion number property format."""
    return {"number": float(str(value)) if "." in str(value) else int(str(value))}


def coerce_url(value: str) -> dict:
    """Coerce to Notion url property format."""
    return {"url": str(value)}


def coerce_checkbox(value: str | bool) -> dict:
    """Coerce to Notion checkbox property format.

    Accepts: True/False, "true"/"false", "yes"/"no", "1"/"0"
    """
    if isinstance(value, bool):
        return {"checkbox": value}
    v = str(value).lower().strip()
    return {"checkbox": v in ("true", "yes", "1", "on")}


def coerce_relation(value: str | list) -> dict:
    """Coerce ID(s) to Notion relation property format."""
    from notion.client import _normalise_id
    if isinstance(value, list):
        ids = value
    else:
        ids = [v.strip() for v in str(value).split(",") if v.strip()]
    return {"relation": [{"id": _normalise_id(id_)} for id_ in ids]}


def coerce_people(value: str | list) -> dict:
    """Coerce user ID(s) to Notion people property format."""
    from notion.client import _normalise_id
    if isinstance(value, list):
        ids = value
    else:
        ids = [v.strip() for v in str(value).split(",") if v.strip()]
    return {"people": [{"object": "user", "id": _normalise_id(id_)} for id_ in ids]}


def coerce_email(value: str) -> dict:
    return {"email": str(value)}


def coerce_phone_number(value: str) -> dict:
    return {"phone_number": str(value)}


def coerce_status(value: str) -> dict:
    """Coerce a string to Notion status property format."""
    return {"status": {"name": str(value)}}


# Map from Notion property type to coerce function
COERCE_MAP = {
    "title": coerce_title,
    "rich_text": coerce_rich_text,
    "select": coerce_select,
    "multi_select": coerce_multi_select,
    "date": coerce_date,
    "number": coerce_number,
    "url": coerce_url,
    "checkbox": coerce_checkbox,
    "relation": coerce_relation,
    "people": coerce_people,
    "email": coerce_email,
    "phone_number": coerce_phone_number,
    "status": coerce_status,
}


def coerce_value(prop_type: str, value) -> dict:
    """Coerce a value based on the Notion property type."""
    fn = COERCE_MAP.get(prop_type)
    if fn is None:
        raise ValueError(f"Unsupported property type: {prop_type!r}")
    return fn(value)


def markdown_to_blocks(text: str) -> list[dict]:
    """Convert markdown text to Notion block objects.

    Supported:
    - ## heading → heading_2
    - ### heading → heading_3
    - - item → bulleted_list_item
    - 1. item → numbered_list_item
    - > quote → quote
    - ```code``` → code block
    - --- → divider
    - plain text → paragraph
    """
    blocks = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.strip().startswith("```"):
            code_lines = []
            lang = line.strip()[3:].strip() or "plain text"
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang,
                }
            })
            i += 1
            continue

        # Divider
        if line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Heading 3
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}
            })
            i += 1
            continue

        # Heading 2
        if line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}
            })
            i += 1
            continue

        # Bulleted list
        if line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
            i += 1
            continue

        # Numbered list
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": m.group(1)}}]}
            })
            i += 1
            continue

        # Quote
        if line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
            i += 1
            continue

        # Paragraph (including empty lines as empty paragraphs)
        if line.strip():
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
            })

        i += 1

    return blocks
