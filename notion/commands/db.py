"""Database commands."""
from __future__ import annotations
import json
import sys
import time

import click

from notion.client import NotionClient, _normalise_id
from notion.errors import NotionCliError, handle_error
from notion.schema import SchemaCache, PropertyResolver
from notion.output import print_json, print_table, print_ids, extract_page_properties


def _parse_data_input(data_str: str | None, properties: tuple[str, ...]) -> dict:
    """Parse --data and KEY=VALUE args into a single dict."""
    result = {}

    if data_str:
        if data_str == "-":
            raw = sys.stdin.read()
        elif data_str.startswith("@"):
            raw = open(data_str[1:]).read()
        else:
            raw = data_str
        result.update(json.loads(raw))

    for prop in properties:
        if "=" not in prop:
            raise click.BadParameter(f"Expected KEY=VALUE, got: {prop!r}")
        key, _, value = prop.partition("=")
        result[key] = value

    return result


def _ensure_options(client: NotionClient, cache: SchemaCache, db_id: str, db_schema: dict, user_data: dict) -> None:
    """Ensure all select/multi_select values exist as options in the schema."""
    for key, value in user_data.items():
        # Find the property in schema (case-insensitive)
        prop_def = None
        prop_name = None
        for name, pdef in db_schema.items():
            if name == key or name.lower() == key.lower():
                prop_def = pdef
                prop_name = name
                break

        if prop_def is None:
            continue  # Let PropertyResolver handle the error

        prop_type = prop_def.get("type")
        if prop_type not in ("select", "multi_select"):
            continue

        # Get existing option names
        existing = {opt["name"] for opt in prop_def.get(prop_type, {}).get("options", [])}

        # Get the new option names
        if prop_type == "select":
            new_names = [str(value)]
        else:
            if isinstance(value, list):
                new_names = value
            else:
                new_names = [v.strip() for v in str(value).split(",") if v.strip()]

        # Add missing options
        for name in new_names:
            if name not in existing:
                # PATCH the database to add the option
                client.patch(f"/databases/{db_id}", {
                    "properties": {
                        prop_name: {
                            prop_type: {
                                "options": list(prop_def.get(prop_type, {}).get("options", [])) + [{"name": name, "color": "default"}]
                            }
                        }
                    }
                })
                cache.invalidate(db_id)
                existing.add(name)


def _build_filter(filter_str: str) -> dict:
    """Parse 'PROP:OP:VALUE' into a Notion filter object."""
    parts = filter_str.split(":", 2)
    if len(parts) != 3:
        raise click.BadParameter(f"Filter must be PROP:OP:VALUE, got: {filter_str!r}")

    prop, op, value = parts

    op_map = {
        "=": "equals",
        "!=": "does_not_equal",
        ">": "greater_than",
        "<": "less_than",
        ">=": "greater_than_or_equal_to",
        "<=": "less_than_or_equal_to",
        "contains": "contains",
        "starts_with": "starts_with",
        "is_empty": "is_empty",
        "is_not_empty": "is_not_empty",
    }

    notion_op = op_map.get(op, op)

    if notion_op in ("is_empty", "is_not_empty"):
        return {"property": prop, "rich_text": {notion_op: True}}

    # Determine condition type — default to rich_text for string ops, number for numeric
    if notion_op in ("greater_than", "less_than", "greater_than_or_equal_to", "less_than_or_equal_to"):
        try:
            num_val = float(value) if "." in value else int(value)
            return {"property": prop, "number": {notion_op: num_val}}
        except ValueError:
            pass

    # Default: try rich_text filter (works for most text-based properties)
    # The caller can override by using property-specific filter syntax
    # For select, we need "select" condition type
    return {"property": prop, "rich_text": {notion_op: value}}


@click.group()
def db():
    """Database commands."""
    pass


@db.command("schema")
@click.argument("database_id")
@click.option("--refresh", is_flag=True, help="Bypass cache and fetch fresh schema")
@click.option("--output", type=click.Choice(["json", "properties", "options"]), default="json")
@click.option("--no-cache", is_flag=True, help="Do not use or write cache")
def schema(database_id, refresh, output, no_cache):
    """Fetch and display database schema."""
    try:
        db_id = _normalise_id(database_id)
        cache = SchemaCache()

        cached = None
        if not refresh and not no_cache:
            cached = cache.get(db_id)

        if cached is None:
            client = NotionClient()
            result = client.get(f"/databases/{db_id}")
            client.close()
            db_schema = result.get("properties", {})
            if not no_cache:
                cache.set(db_id, db_schema)
        else:
            db_schema = cached

        if output == "json":
            print_json(db_schema)
        elif output == "properties":
            props = {name: prop.get("type") for name, prop in db_schema.items()}
            print_json(props)
        elif output == "options":
            options = {}
            for name, prop in db_schema.items():
                prop_type = prop.get("type")
                if prop_type in ("select", "multi_select", "status"):
                    opts = prop.get(prop_type, {}).get("options", [])
                    options[name] = [o.get("name") for o in opts]
            print_json(options)
    except NotionCliError as e:
        handle_error(e)


@db.command("query")
@click.argument("database_id")
@click.option("--filter", "filters", multiple=True, metavar="PROP:OP:VALUE", help="Filter: PROP:OP:VALUE")
@click.option("--sort", multiple=True, metavar="PROP[:asc|desc]", help="Sort by property")
@click.option("--limit", type=int, default=None, help="Max results to return")
@click.option("--page-all", is_flag=True, help="Fetch all pages (paginate through)")
@click.option("--output", type=click.Choice(["json", "table", "ids"]), default="json")
@click.option("--no-cache", is_flag=True, help="Do not use schema cache")
def query(database_id, filters, sort, limit, page_all, output, no_cache):
    """Query a database with optional filters and sorting."""
    try:
        db_id = _normalise_id(database_id)
        client = NotionClient()

        body = {}

        # Build filters
        if filters:
            if len(filters) == 1:
                body["filter"] = _build_filter(filters[0])
            else:
                body["filter"] = {
                    "and": [_build_filter(f) for f in filters]
                }

        # Build sorts
        if sort:
            sorts = []
            for s in sort:
                if ":" in s:
                    prop, direction = s.rsplit(":", 1)
                    sorts.append({"property": prop, "direction": direction})
                else:
                    sorts.append({"property": s, "direction": "ascending"})
            body["sorts"] = sorts

        # Paginate or single page
        results = []
        if page_all:
            for item in client.paginate("POST", f"/databases/{db_id}/query", body=body):
                results.append(item)
                if limit and len(results) >= limit:
                    results = results[:limit]
                    break
        else:
            if limit:
                body["page_size"] = min(limit, 100)
            response = client.post(f"/databases/{db_id}/query", body)
            results = response.get("results", [])
            if limit:
                results = results[:limit]

        client.close()

        if output == "json":
            print_json(results)
        elif output == "table":
            rows = [extract_page_properties(p) for p in results]
            print_table(rows)
        elif output == "ids":
            print_ids(results)

    except NotionCliError as e:
        handle_error(e)


@db.command("add")
@click.argument("database_id")
@click.argument("properties", nargs=-1, metavar="KEY=VALUE")
@click.option("--data", default=None, help="JSON data or @file or -")
@click.option("--add-options", is_flag=True, help="Auto-create missing select options before adding")
@click.option("--output", type=click.Choice(["json", "id"]), default="json")
@click.option("--no-cache", is_flag=True, help="Bypass schema cache")
def add(database_id, properties, data, add_options, output, no_cache):
    """Add a new page to a database."""
    try:
        db_id = _normalise_id(database_id)
        user_data = _parse_data_input(data, properties)

        if not user_data:
            raise click.UsageError("No properties provided. Use KEY=VALUE args or --data")

        client = NotionClient()
        cache = SchemaCache()

        # Fetch schema
        db_schema = None
        if not no_cache:
            db_schema = cache.get(db_id)
        if db_schema is None:
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            if not no_cache:
                cache.set(db_id, db_schema)

        # Auto-add missing select/multi_select options if requested
        if add_options:
            _ensure_options(client, cache, db_id, db_schema, user_data)
            # Refresh schema after potentially adding options
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            cache.set(db_id, db_schema)

        # Resolve properties
        resolver = PropertyResolver()
        resolved = resolver.resolve_all(db_schema, user_data)

        # Create the page
        page = client.post("/pages", {
            "parent": {"database_id": db_id},
            "properties": resolved,
        })
        client.close()

        if output == "id":
            print(page.get("id", ""))
        else:
            print_json(page)

    except click.UsageError:
        raise
    except NotionCliError as e:
        handle_error(e)


@db.command("upsert")
@click.argument("database_id")
@click.option("--match", multiple=True, metavar="PROP:VALUE", help="Match criteria (AND logic)")
@click.argument("properties", nargs=-1, metavar="KEY=VALUE")
@click.option("--data", default=None, help="JSON data or @file or -")
@click.option("--add-options", is_flag=True)
@click.option("--no-cache", is_flag=True, help="Bypass schema cache")
def upsert(database_id, match, properties, data, add_options, no_cache):
    """Create or update a page matching criteria. Exit 6 if multiple matches."""
    try:
        if not match:
            raise click.UsageError("At least one --match PROP:VALUE is required")

        db_id = _normalise_id(database_id)
        user_data = _parse_data_input(data, properties)

        client = NotionClient()
        cache = SchemaCache()

        # Fetch schema
        db_schema = None
        if not no_cache:
            db_schema = cache.get(db_id)
        if db_schema is None:
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            if not no_cache:
                cache.set(db_id, db_schema)

        # Build filter from --match flags (AND logic)
        match_filters = []
        for m in match:
            prop, _, value = m.partition(":")
            if not prop or not value:
                raise click.BadParameter(f"--match must be PROP:VALUE, got: {m!r}")

            # Determine filter type from schema
            prop_def = None
            for name, pdef in db_schema.items():
                if name == prop or name.lower() == prop.lower():
                    prop_def = pdef
                    break

            if prop_def:
                ptype = prop_def.get("type", "rich_text")
                if ptype == "title":
                    match_filters.append({"property": prop, "title": {"equals": value}})
                elif ptype == "select":
                    match_filters.append({"property": prop, "select": {"equals": value}})
                elif ptype == "number":
                    match_filters.append({"property": prop, "number": {"equals": float(value) if "." in value else int(value)}})
                elif ptype == "checkbox":
                    match_filters.append({"property": prop, "checkbox": {"equals": value.lower() in ("true", "yes", "1")}})
                else:
                    match_filters.append({"property": prop, "rich_text": {"equals": value}})
            else:
                match_filters.append({"property": prop, "rich_text": {"equals": value}})

        query_body = {}
        if len(match_filters) == 1:
            query_body["filter"] = match_filters[0]
        else:
            query_body["filter"] = {"and": match_filters}

        response = client.post(f"/databases/{db_id}/query", query_body)
        results = response.get("results", [])

        if len(results) > 1:
            from notion.errors import AmbiguousError
            raise AmbiguousError(
                f"Upsert matched {len(results)} pages — expected 0 or 1",
                {"match_count": len(results), "ids": [r["id"] for r in results]}
            )

        # Auto-add missing options if requested
        if add_options and user_data:
            _ensure_options(client, cache, db_id, db_schema, user_data)
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            cache.set(db_id, db_schema)

        # Resolve properties
        resolver = PropertyResolver()
        resolved = resolver.resolve_all(db_schema, user_data) if user_data else {}

        if len(results) == 0:
            # CREATE
            page = client.post("/pages", {
                "parent": {"database_id": db_id},
                "properties": resolved,
            })
            print_json({"action": "created", "id": page.get("id"), "page": page})
        else:
            # UPDATE
            existing_page = results[0]
            page = client.patch(f"/pages/{existing_page['id']}", {"properties": resolved})
            print_json({"action": "updated", "id": page.get("id"), "page": page})

        client.close()

    except (click.BadParameter, click.UsageError):
        raise
    except NotionCliError as e:
        handle_error(e)


@db.command("update-row")
@click.argument("page_id")
@click.argument("properties", nargs=-1, metavar="KEY=VALUE")
@click.option("--data", default=None, help="JSON data or @file or -")
def update_row(page_id, properties, data):
    """Update properties of an existing database row."""
    try:
        pid = _normalise_id(page_id)
        user_data = _parse_data_input(data, properties)

        if not user_data:
            raise click.UsageError("No properties provided. Use KEY=VALUE args or --data")

        client = NotionClient()

        # Get the current page to find its parent database
        current_page = client.get(f"/pages/{pid}")
        parent = current_page.get("parent", {})

        if parent.get("type") == "database_id":
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
            # Not a database page — send raw (may fail for complex types)
            resolved = user_data

        page = client.patch(f"/pages/{pid}", {"properties": resolved})
        client.close()
        print_json(page)

    except (click.UsageError,):
        raise
    except NotionCliError as e:
        handle_error(e)


@db.command("add-option")
@click.argument("database_id")
@click.argument("property_name")
@click.option("--option", multiple=True, required=True, help="Option name to add")
@click.option("--color", default="default", help="Option color")
def add_option(database_id, property_name, option, color):
    """Add select/multi_select options to a database property. Idempotent."""
    try:
        db_id = _normalise_id(database_id)
        client = NotionClient()
        cache = SchemaCache()

        # Get current schema (cache or API)
        db_schema = cache.get(db_id)
        if db_schema is None:
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            cache.set(db_id, db_schema)

        # Find the property (case-insensitive)
        prop_def = None
        actual_prop_name = None
        for name, pdef in db_schema.items():
            if name == property_name or name.lower() == property_name.lower():
                prop_def = pdef
                actual_prop_name = name
                break

        if prop_def is None:
            from notion.errors import ValidationError
            raise ValidationError(
                f"Property {property_name!r} not found",
                {"available": list(db_schema.keys())}
            )

        prop_type = prop_def.get("type")
        if prop_type not in ("select", "multi_select", "status"):
            from notion.errors import ValidationError
            raise ValidationError(
                f"Property {property_name!r} is type {prop_type!r}, not select/multi_select"
            )

        # Get existing options
        existing_names = {opt["name"] for opt in prop_def.get(prop_type, {}).get("options", [])}
        existing_options = list(prop_def.get(prop_type, {}).get("options", []))

        results = {}
        new_options = list(existing_options)

        for opt_name in option:
            if opt_name in existing_names:
                results[opt_name] = "already_exists"
            else:
                new_options.append({"name": opt_name, "color": color})
                existing_names.add(opt_name)
                results[opt_name] = "added"

        # Only PATCH if there are new options to add
        if any(v == "added" for v in results.values()):
            client.patch(f"/databases/{db_id}", {
                "properties": {
                    actual_prop_name: {
                        prop_type: {"options": new_options}
                    }
                }
            })
            cache.invalidate(db_id)

        client.close()
        print_json({"status": "ok", "results": results})

    except NotionCliError as e:
        handle_error(e)


@db.command("batch-add")
@click.argument("database_id")
@click.option("--data", required=True, help="JSON array or @file or -")
@click.option("--dry-run", is_flag=True, help="Validate only, exit 7 (no writes)")
@click.option("--continue-on-error", is_flag=True, help="Continue on individual row errors")
def batch_add(database_id, data, dry_run, continue_on_error):
    """Add multiple pages from a JSON array."""
    try:
        db_id = _normalise_id(database_id)

        # Parse input
        if data == "-":
            raw = sys.stdin.read()
        elif data.startswith("@"):
            raw = open(data[1:]).read()
        else:
            raw = data

        rows = json.loads(raw)
        if not isinstance(rows, list):
            raise click.BadParameter("--data must be a JSON array")

        client = NotionClient()
        cache = SchemaCache()

        # Fetch schema once
        db_schema = cache.get(db_id)
        if db_schema is None:
            result = client.get(f"/databases/{db_id}")
            db_schema = result.get("properties", {})
            cache.set(db_id, db_schema)

        resolver = PropertyResolver()

        # Validate all rows first
        validation_errors = []
        for i, row in enumerate(rows):
            try:
                resolver.resolve_all(db_schema, row)
            except Exception as e:
                validation_errors.append({"index": i, "error": str(e), "row": row})

        if dry_run:
            if validation_errors:
                print_json({
                    "dry_run": True,
                    "total": len(rows),
                    "valid": len(rows) - len(validation_errors),
                    "errors": validation_errors,
                })
                from notion.errors import DryRunError
                raise DryRunError("Dry run completed with validation errors", {"errors": len(validation_errors)})
            else:
                print_json({
                    "dry_run": True,
                    "total": len(rows),
                    "valid": len(rows),
                    "errors": [],
                })
                from notion.errors import DryRunError
                raise DryRunError("Dry run completed successfully")

        if validation_errors and not continue_on_error:
            from notion.errors import ValidationError as VE
            raise VE(
                f"Validation failed for {len(validation_errors)} rows",
                {"errors": validation_errors}
            )

        # Add pages with rate limiting
        results = []
        errors = []

        for i, row in enumerate(rows):
            try:
                resolved = resolver.resolve_all(db_schema, row)
                page = client.post("/pages", {
                    "parent": {"database_id": db_id},
                    "properties": resolved,
                })
                results.append({"index": i, "id": page.get("id"), "status": "created"})
                import sys as _sys
                print(f"[{i+1}/{len(rows)}] Created: {page.get('id')}", file=_sys.stderr)
            except Exception as e:
                error_entry = {"index": i, "error": str(e), "row": row}
                errors.append(error_entry)
                print(f"[{i+1}/{len(rows)}] Error: {e}", file=_sys.stderr)
                if not continue_on_error:
                    client.close()
                    print_json({"created": results, "errors": errors})
                    sys.exit(4)

            # Rate limit: 3 req/sec
            if i < len(rows) - 1:
                time.sleep(0.34)

        client.close()
        print_json({"created": results, "errors": errors, "total": len(rows)})

    except (click.BadParameter, click.UsageError):
        raise
    except NotionCliError as e:
        handle_error(e)


@db.command("create")
@click.argument("parent_id")
@click.argument("title")
@click.option("--data", default=None, help="Schema JSON or @file or -")
@click.option("--output", type=click.Choice(["json", "id"]), default="json")
def create(parent_id, title, data, output):
    """Create a new database."""
    try:
        pid = _normalise_id(parent_id)

        extra_props = {}
        if data:
            if data == "-":
                raw = sys.stdin.read()
            elif data.startswith("@"):
                raw = open(data[1:]).read()
            else:
                raw = data
            extra_props = json.loads(raw)

        body = {
            "parent": {"page_id": pid},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": {
                "Name": {"title": {}},
                **extra_props,
            }
        }

        client = NotionClient()
        result = client.post("/databases", body)
        client.close()

        if output == "id":
            print(result.get("id", ""))
        else:
            print_json(result)
    except NotionCliError as e:
        handle_error(e)


@db.command("delete")
@click.argument("database_id")
@click.option("--confirm", "confirmed", is_flag=True, help="Skip confirmation prompt")
def delete(database_id, confirmed):
    """Archive (delete) a database."""
    try:
        db_id = _normalise_id(database_id)

        if not confirmed:
            from notion.modes import get_mode
            mode = get_mode()
            if mode == "interactive":
                if not click.confirm(f"Archive database {db_id}?"):
                    click.echo("Cancelled.")
                    return

        client = NotionClient()
        result = client.patch(f"/databases/{db_id}", {"archived": True})
        client.close()
        print_json({"status": "archived", "id": result.get("id")})
    except NotionCliError as e:
        handle_error(e)


@db.command("update-schema")
@click.argument("database_id")
@click.option("--data", required=True, help="Schema changes JSON or @file or -")
def update_schema(database_id, data):
    """Update database schema properties."""
    try:
        db_id = _normalise_id(database_id)

        if data == "-":
            import sys
            raw = sys.stdin.read()
        elif data.startswith("@"):
            raw = open(data[1:]).read()
        else:
            raw = data

        schema_changes = json.loads(raw)

        client = NotionClient()
        result = client.patch(f"/databases/{db_id}", {"properties": schema_changes})

        # Invalidate cache
        cache = SchemaCache()
        cache.invalidate(db_id)

        client.close()
        print_json(result.get("properties", result))

    except NotionCliError as e:
        handle_error(e)
