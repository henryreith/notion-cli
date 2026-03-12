"""Search command."""
from __future__ import annotations
import json

import click

from notion.client import NotionClient
from notion.errors import NotionCliError, handle_error
from notion.output import print_json, print_ids


@click.command("search")
@click.argument("query", default="")
@click.option("--type", "object_type", type=click.Choice(["page", "database"]), default=None, help="Filter by object type")
@click.option("--sort", type=click.Choice(["last_edited", "relevance"]), default="relevance", help="Sort order")
@click.option("--limit", type=int, default=10, help="Max results")
@click.option("--page-all", is_flag=True, help="Fetch all results")
@click.option("--output", type=click.Choice(["json", "ids"]), default="json")
def search(query, object_type, sort, limit, page_all, output):
    """Search pages and databases."""
    try:
        body = {}
        if query:
            body["query"] = query

        if object_type:
            body["filter"] = {"value": object_type, "property": "object"}

        if sort == "last_edited":
            body["sort"] = {"direction": "descending", "timestamp": "last_edited_time"}

        client = NotionClient()

        if page_all:
            results = list(client.paginate("POST", "/search", body=body))
            if limit:
                results = results[:limit]
        else:
            body["page_size"] = min(limit, 100)
            response = client.post("/search", body)
            results = response.get("results", [])[:limit]

        client.close()

        if output == "ids":
            print_ids(results)
        else:
            print_json(results)
    except NotionCliError as e:
        handle_error(e)
