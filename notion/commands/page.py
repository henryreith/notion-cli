"""Page commands."""
from __future__ import annotations
import json
import sys

import click

from notion.client import NotionClient, _normalise_id
from notion.errors import NotionCliError, handle_error
from notion.output import print_json, extract_page_properties


def _parse_page_data(data: str | None, properties: tuple[str, ...]) -> dict:
    """Parse --data and KEY=VALUE args into a dict."""
    result = {}
    if data:
        if data == "-":
            raw = sys.stdin.read()
        elif data.startswith("@"):
            raw = open(data[1:]).read()
        else:
            raw = data
        result.update(json.loads(raw))
    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Expected KEY=VALUE, got: {prop!r}")
        key, _, value = prop.partition("=")
        result[key] = value
    return result


@click.group()
def page():
    """Page commands."""
    pass


@page.command("create")
@click.argument("parent_id")
@click.option("--title", required=True, help="Page title")
@click.option("--data", default=None, help="Additional properties JSON or @file or -")
@click.option("--output", type=click.Choice(["json", "id"]), default="json")
def create(parent_id, title, data, output):
    """Create a new page under a parent page or database."""
    try:
        pid = _normalise_id(parent_id)
        client = NotionClient()

        # Build properties
        extra_props = {}
        if data:
            extra_props = _parse_page_data(data, ())

        # Determine parent type — try as database first, fall back to page
        # Notion API requires specifying parent type
        body = {
            "parent": {"page_id": pid},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            }
        }

        if extra_props:
            for key, value in extra_props.items():
                body["properties"][key] = value

        result = client.post("/pages", body)
        client.close()

        if output == "id":
            print(result.get("id", ""))
        else:
            print_json(result)

    except NotionCliError as e:
        handle_error(e)


@page.command("get")
@click.argument("page_id")
@click.option("--output", type=click.Choice(["json", "properties"]), default="json")
def get(page_id, output):
    """Get a page by ID."""
    try:
        pid = _normalise_id(page_id)
        client = NotionClient()
        result = client.get(f"/pages/{pid}")
        client.close()

        if output == "properties":
            print_json(extract_page_properties(result))
        else:
            print_json(result)

    except NotionCliError as e:
        handle_error(e)


@page.command("get-property")
@click.argument("page_id")
@click.argument("property_name")
def get_property(page_id, property_name):
    """Get a specific property value from a page."""
    try:
        pid = _normalise_id(page_id)
        client = NotionClient()
        result = client.get(f"/pages/{pid}")
        client.close()

        props = result.get("properties", {})

        # Case-insensitive search
        found = None
        for name, value in props.items():
            if name == property_name or name.lower() == property_name.lower():
                found = value
                break

        if found is None:
            from notion.errors import NotFoundError
            raise NotFoundError(
                f"Property {property_name!r} not found on page",
                {"available": list(props.keys())}
            )

        print_json(found)

    except NotionCliError as e:
        handle_error(e)


@page.command("set")
@click.argument("page_id")
@click.argument("properties", nargs=-1, metavar="KEY=VALUE")
@click.option("--data", default=None, help="JSON data or @file or -")
def set(page_id, properties, data):
    """Update page properties."""
    try:
        pid = _normalise_id(page_id)
        user_data = _parse_page_data(data, properties)

        if not user_data:
            raise click.UsageError("No properties provided. Use KEY=VALUE args or --data")

        client = NotionClient()

        # Get the page to find parent database (for schema resolution)
        current_page = client.get(f"/pages/{pid}")
        parent = current_page.get("parent", {})

        if parent.get("type") == "database_id":
            from notion.schema import SchemaCache, PropertyResolver
            db_id = parent["database_id"].replace("-", "")
            cache = SchemaCache()
            db_schema = cache.get(db_id)
            if db_schema is None:
                db_result = client.get(f"/databases/{db_id}")
                db_schema = db_result.get("properties", {})
                cache.set(db_id, db_schema)

            resolver = PropertyResolver()
            resolved = resolver.resolve_all(db_schema, user_data)
        else:
            # Standalone page — use raw properties
            resolved = user_data

        result = client.patch(f"/pages/{pid}", {"properties": resolved})
        client.close()
        print_json(result)

    except (click.UsageError,):
        raise
    except NotionCliError as e:
        handle_error(e)


@page.command("append")
@click.argument("page_id")
@click.option("--data", required=True, help="Markdown text, JSON blocks, @file, or -")
def append(page_id, data):
    """Append blocks to a page."""
    try:
        pid = _normalise_id(page_id)

        if data == "-":
            raw = sys.stdin.read()
        elif data.startswith("@"):
            raw = open(data[1:]).read()
        else:
            raw = data

        # Try parsing as JSON first; fall back to markdown
        blocks = None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                blocks = parsed
            elif isinstance(parsed, dict) and "children" in parsed:
                blocks = parsed["children"]
        except json.JSONDecodeError:
            pass

        if blocks is None:
            from notion.coerce import markdown_to_blocks
            blocks = markdown_to_blocks(raw)

        client = NotionClient()
        result = client.patch(f"/blocks/{pid}/children", {"children": blocks})
        client.close()
        print_json(result)

    except NotionCliError as e:
        handle_error(e)


@page.command("delete")
@click.argument("page_id")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
def delete(page_id, confirmed):
    """Archive (delete) a page."""
    try:
        pid = _normalise_id(page_id)

        if not confirmed:
            from notion.modes import get_mode
            mode = get_mode()
            if mode == "interactive":
                if not click.confirm(f"Archive page {pid}?"):
                    click.echo("Cancelled.")
                    return

        client = NotionClient()
        result = client.patch(f"/pages/{pid}", {"archived": True})
        client.close()
        print_json({"status": "archived", "id": result.get("id")})

    except NotionCliError as e:
        handle_error(e)


@page.command("restore")
@click.argument("page_id")
def restore(page_id):
    """Restore an archived page."""
    try:
        pid = _normalise_id(page_id)
        client = NotionClient()
        result = client.patch(f"/pages/{pid}", {"archived": False})
        client.close()
        print_json({"status": "restored", "id": result.get("id")})

    except NotionCliError as e:
        handle_error(e)
