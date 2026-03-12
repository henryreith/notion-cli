"""Output formatters."""
import json
import sys
from typing import Any


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2))


def print_table(rows: list[dict], columns: list[str] | None = None) -> None:
    """Print rows as a simple table using Rich."""
    from rich.table import Table
    from rich.console import Console

    if not rows:
        print("(no results)")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")

    cols = columns or list(rows[0].keys())
    for col in cols:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in cols])

    console.print(table)


def print_ids(items: list[dict]) -> None:
    for item in items:
        print(item.get("id", ""))


def extract_page_properties(page: dict) -> dict:
    """Extract a flat dict of property values from a Notion page object."""
    result = {"id": page.get("id", "")}
    props = page.get("properties", {})

    for prop_name, prop_data in props.items():
        prop_type = prop_data.get("type", "")
        value = _extract_property_value(prop_type, prop_data)
        result[prop_name] = value

    return result


def _extract_property_value(prop_type: str, prop_data: dict) -> Any:
    """Extract a human-readable value from a Notion property object."""
    if prop_type == "title":
        items = prop_data.get("title", [])
        return "".join(t.get("plain_text", "") for t in items)
    elif prop_type == "rich_text":
        items = prop_data.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in items)
    elif prop_type == "select":
        sel = prop_data.get("select")
        return sel.get("name", "") if sel else ""
    elif prop_type == "multi_select":
        items = prop_data.get("multi_select", [])
        return ", ".join(item.get("name", "") for item in items)
    elif prop_type == "date":
        d = prop_data.get("date")
        if not d:
            return ""
        start = d.get("start", "")
        end = d.get("end")
        return f"{start}/{end}" if end else start
    elif prop_type == "number":
        return prop_data.get("number")
    elif prop_type == "checkbox":
        return prop_data.get("checkbox", False)
    elif prop_type == "url":
        return prop_data.get("url", "")
    elif prop_type == "email":
        return prop_data.get("email", "")
    elif prop_type == "phone_number":
        return prop_data.get("phone_number", "")
    elif prop_type == "people":
        items = prop_data.get("people", [])
        return ", ".join(p.get("name", p.get("id", "")) for p in items)
    elif prop_type == "relation":
        items = prop_data.get("relation", [])
        return ", ".join(r.get("id", "") for r in items)
    elif prop_type == "status":
        s = prop_data.get("status")
        return s.get("name", "") if s else ""
    elif prop_type == "formula":
        formula = prop_data.get("formula", {})
        ftype = formula.get("type", "")
        return formula.get(ftype)
    elif prop_type == "rollup":
        rollup = prop_data.get("rollup", {})
        rtype = rollup.get("type", "")
        return rollup.get(rtype)
    elif prop_type == "created_time":
        return prop_data.get("created_time", "")
    elif prop_type == "last_edited_time":
        return prop_data.get("last_edited_time", "")
    elif prop_type == "created_by":
        u = prop_data.get("created_by", {})
        return u.get("name", u.get("id", ""))
    elif prop_type == "last_edited_by":
        u = prop_data.get("last_edited_by", {})
        return u.get("name", u.get("id", ""))
    else:
        return str(prop_data.get(prop_type, ""))
