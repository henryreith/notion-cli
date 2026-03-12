"""User commands."""
from __future__ import annotations

import click

from notion.client import NotionClient, _normalise_id
from notion.errors import NotionCliError, handle_error
from notion.output import print_json, print_ids


@click.group()
def user():
    """User commands."""
    pass


@user.command("list")
@click.option("--output", type=click.Choice(["json", "ids"]), default="json")
def list_users(output):
    """List workspace users."""
    try:
        client = NotionClient()
        results = list(client.paginate("GET", "/users"))
        client.close()

        if output == "ids":
            print_ids(results)
        else:
            print_json(results)
    except NotionCliError as e:
        handle_error(e)


@user.command("get")
@click.argument("user_id")
def get(user_id):
    """Get a user by ID."""
    try:
        uid = _normalise_id(user_id)
        client = NotionClient()
        result = client.get(f"/users/{uid}")
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)


@user.command("me")
def me():
    """Get the bot user for the current token."""
    try:
        client = NotionClient()
        result = client.get("/users/me")
        client.close()
        print_json(result)
    except NotionCliError as e:
        handle_error(e)
