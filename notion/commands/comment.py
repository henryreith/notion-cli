"""Comment commands."""
from __future__ import annotations
import json

import click

from notion.client import NotionClient, _normalise_id
from notion.errors import NotionCliError, handle_error
from notion.output import print_json, print_ids


@click.group()
def comment():
    """Comment commands."""
    pass


@comment.command("add")
@click.argument("page_id")
@click.argument("text")
def add(page_id, text):
    """Add a comment to a page."""
    try:
        pid = _normalise_id(page_id)
        client = NotionClient()
        result = client.post("/comments", {
            "parent": {"page_id": pid},
            "rich_text": [{"type": "text", "text": {"content": text}}]
        })
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)


@comment.command("list")
@click.argument("page_id")
@click.option("--output", type=click.Choice(["json", "ids"]), default="json")
def list_comments(page_id, output):
    """List comments on a page."""
    try:
        pid = _normalise_id(page_id)
        client = NotionClient()
        results = list(client.paginate("GET", "/comments", params={"block_id": pid}))
        client.close()

        if output == "ids":
            print_ids(results)
        else:
            print_json(results)
    except NotionCliError as e:
        handle_error(e)
