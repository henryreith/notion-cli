import json
import sys

import click

from notion.client import NotionClient, _load_token, _save_token, CONFIG_FILE
from notion.errors import NotionCliError, handle_error


@click.group()
def auth():
    """Authentication commands."""
    pass


@auth.command("set-token")
@click.argument("token")
def set_token(token: str):
    """Save API token to config file."""
    _save_token(token)
    click.echo(json.dumps({"status": "ok", "config": str(CONFIG_FILE)}))


@auth.command("test")
@click.option("--token", envvar="NOTION_API_KEY", default=None)
def test(token: str | None):
    """Test authentication with Notion API."""
    try:
        client = NotionClient(token=token)
        result = client.get("/users/me")
        click.echo(json.dumps({
            "status": "ok",
            "user": result.get("name", "unknown"),
            "type": result.get("type", "unknown"),
        }))
    except NotionCliError as e:
        handle_error(e)


@auth.command("status")
def status():
    """Show current authentication status."""
    try:
        token = _load_token()
        source = "env" if __import__("os").environ.get("NOTION_API_KEY") else "config_file"
        # Mask token
        masked = token[:8] + "..." + token[-4:] if len(token) > 12 else "***"
        click.echo(json.dumps({
            "status": "configured",
            "token": masked,
            "source": source,
            "config_file": str(CONFIG_FILE),
        }))
    except NotionCliError as e:
        handle_error(e)
