import click
from notion.commands.auth import auth
from notion.commands.db import db
from notion.commands.page import page
from notion.commands.block import block
from notion.commands.comment import comment
from notion.commands.search import search
from notion.commands.user import user


@click.group()
@click.version_option(package_name="notion-agent-cli")
@click.option(
    "--mode",
    type=click.Choice(["auto", "interactive", "ci"]),
    default=None,
    envvar="NOTION_MODE",
    help="Operating mode: auto (default), interactive (confirm prompts), ci (never prompt)",
)
@click.pass_context
def cli(ctx: click.Context, mode: str | None) -> None:
    """notion-agent-cli: Notion API for AI agents and shell scripts."""
    ctx.ensure_object(dict)
    if mode:
        ctx.obj["mode"] = mode


cli.add_command(auth)
cli.add_command(db)
cli.add_command(page)
cli.add_command(block)
cli.add_command(comment)
cli.add_command(search)
cli.add_command(user)
