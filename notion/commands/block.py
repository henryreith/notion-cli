"""Block commands."""
from __future__ import annotations
import json
import sys

import click

from notion.client import NotionClient, _normalise_id
from notion.errors import NotionCliError, handle_error
from notion.output import print_json, print_ids


@click.group()
def block():
    """Block commands."""
    pass


@block.command("list")
@click.argument("block_id")
@click.option("--output", type=click.Choice(["json", "ids"]), default="json")
def list_blocks(block_id, output):
    """List child blocks of a block or page."""
    try:
        bid = _normalise_id(block_id)
        client = NotionClient()
        results = list(client.paginate("GET", f"/blocks/{bid}/children"))
        client.close()

        if output == "ids":
            print_ids(results)
        else:
            print_json(results)
    except NotionCliError as e:
        handle_error(e)


@block.command("get")
@click.argument("block_id")
def get(block_id):
    """Get a block by ID."""
    try:
        bid = _normalise_id(block_id)
        client = NotionClient()
        result = client.get(f"/blocks/{bid}")
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)


@block.command("append")
@click.argument("block_id")
@click.option("--type", "block_type", default="paragraph", help="Block type")
@click.option("--text", required=True, help="Block text content")
def append(block_id, block_type, text):
    """Append a new block to a page or block."""
    try:
        bid = _normalise_id(block_id)

        rich_text = [{"type": "text", "text": {"content": text}}]

        # Build block based on type
        type_map = {
            "paragraph": {"paragraph": {"rich_text": rich_text}},
            "heading_1": {"heading_1": {"rich_text": rich_text}},
            "heading_2": {"heading_2": {"rich_text": rich_text}},
            "heading_3": {"heading_3": {"rich_text": rich_text}},
            "bulleted_list_item": {"bulleted_list_item": {"rich_text": rich_text}},
            "numbered_list_item": {"numbered_list_item": {"rich_text": rich_text}},
            "quote": {"quote": {"rich_text": rich_text}},
            "code": {"code": {"rich_text": rich_text, "language": "plain text"}},
            "callout": {"callout": {"rich_text": rich_text}},
        }

        block_content = type_map.get(block_type)
        if block_content is None:
            block_content = {"paragraph": {"rich_text": rich_text}}

        new_block = {"object": "block", "type": block_type, **block_content}

        client = NotionClient()
        result = client.patch(f"/blocks/{bid}/children", {"children": [new_block]})
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)


@block.command("update")
@click.argument("block_id")
@click.option("--data", required=True, help="Block update JSON or @file or -")
def update(block_id, data):
    """Update a block's content."""
    try:
        bid = _normalise_id(block_id)

        if data == "-":
            raw = sys.stdin.read()
        elif data.startswith("@"):
            raw = open(data[1:]).read()
        else:
            raw = data

        body = json.loads(raw)

        client = NotionClient()
        result = client.patch(f"/blocks/{bid}", body)
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)


@block.command("delete")
@click.argument("block_id")
def delete(block_id):
    """Delete (archive) a block."""
    try:
        bid = _normalise_id(block_id)
        client = NotionClient()
        result = client.delete(f"/blocks/{bid}")
        client.close()
        print_json({"status": "deleted", "id": result.get("id", bid)})
    except NotionCliError as e:
        handle_error(e)
