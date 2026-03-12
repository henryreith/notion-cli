# notion-agent-cli

[![PyPI](https://img.shields.io/pypi/v/notion-agent-cli)](https://pypi.org/project/notion-agent-cli/)
[![Python](https://img.shields.io/pypi/pyversions/notion-agent-cli)](https://pypi.org/project/notion-agent-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/henryreith/notion-agent-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/henryreith/notion-agent-cli/actions)

Zero-overhead CLI for the Notion API — designed for AI agents and shell scripts.

## Why not Notion MCP?

Notion MCP loads **3,000–6,000 tokens** of tool definitions into your context window per session.
`notion-agent-cli` has **zero overhead** — call it from subprocess, no context cost.

```python
# In your AI agent:
result = subprocess.run(
    ["notion", "db", "query", DATABASE_ID, "--output", "json"],
    capture_output=True, text=True
)
pages = json.loads(result.stdout)
```

## Install

```bash
pip install notion-agent-cli
```

## Quick Start

```bash
export NOTION_API_KEY=secret_xxx

notion auth test
notion db schema <database-id>
notion db query <database-id> --filter "Status:=:Active" --output table
notion db add <database-id> "Name=My Page" "Status=Active"
notion search "meeting notes" --type page
```

## Authentication

```bash
# Via environment variable (preferred for agents)
export NOTION_API_KEY=secret_xxx

# Via config file (persists across sessions)
notion auth set-token secret_xxx
notion auth status
```

## Command Reference

### Database Commands

```bash
notion db schema <db-id>                    # Show schema
notion db schema <db-id> --output properties  # Show property types
notion db schema <db-id> --output options   # Show select options

notion db query <db-id>
notion db query <db-id> --filter "Status:=:Active"
notion db query <db-id> --filter "Name:contains:foo" --output table
notion db query <db-id> --page-all --output ids

notion db add <db-id> "Name=My Page" "Status=Active" "Tags=python,cli"
notion db add <db-id> --data '{"Name": "My Page"}' --output id
notion db add <db-id> --data @data.json --add-options

notion db upsert <db-id> --match "Name:My Page" "Status=Done"
notion db update-row <page-id> "Status=Done"

notion db add-option <db-id> Status --option "New Option" --color green
notion db batch-add <db-id> --data @batch.json --dry-run
notion db batch-add <db-id> --data - < batch.json

notion db create <parent-page-id> "My Database"
notion db delete <db-id> --confirm
notion db update-schema <db-id> --data @schema-patch.json
```

### Page Commands

```bash
notion page create <parent-id> --title "My Page"
notion page get <page-id>
notion page get <page-id> --output properties
notion page get-property <page-id> Status
notion page set <page-id> "Status=Done"
notion page append <page-id> --data "## New Section\n\nContent here."
notion page append <page-id> --data @content.md
notion page delete <page-id> --confirm
notion page restore <page-id>
```

### Block Commands

```bash
notion block list <page-id>
notion block get <block-id>
notion block append <page-id> --type heading_2 --text "New Section"
notion block update <block-id> --data @update.json
notion block delete <block-id>
```

### Other Commands

```bash
notion search "query" --type page --limit 10
notion comment add <page-id> "Great work!"
notion comment list <page-id>
notion user list
notion user me
```

## Output Formats

Most commands support `--output`:
- `json` (default) — full Notion API response
- `table` — human-readable table (db query)
- `ids` — one ID per line (for piping)

```bash
# Pipe IDs into another command
notion db query <db-id> --output ids | xargs -I{} notion page delete {} --confirm
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Authentication error |
| 2 | Not found |
| 3 | Validation error |
| 4 | API error |
| 5 | Already exists |
| 6 | Ambiguous match (upsert) |
| 7 | Dry run completed |

## Agent Integration Example

```python
import subprocess
import json

def notion_db_add(database_id: str, properties: dict) -> str:
    """Add a page to a Notion database, returns page ID."""
    result = subprocess.run(
        ["notion", "db", "add", database_id, "--data", json.dumps(properties), "--output", "id"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        error = json.loads(result.stderr)
        raise RuntimeError(f"Notion error: {error['error']}")
    return result.stdout.strip()

# Usage:
page_id = notion_db_add(DATABASE_ID, {
    "Name": "Meeting Notes 2024-01-15",
    "Status": "Draft",
    "Tags": "meeting,q1",
})
```

## Development

```bash
git clone https://github.com/henryreith/notion-agent-cli
cd notion-agent-cli
pip install -e ".[dev]"
pytest tests/ -v --ignore=tests/integration
```

## License

MIT
