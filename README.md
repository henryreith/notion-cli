# notion-agent-cli

[![npm](https://img.shields.io/npm/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![Node.js](https://img.shields.io/node/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/henryreith/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/henryreith/notion-cli/actions)

Zero-overhead CLI for the Notion API — designed for AI agents, shell scripts, and automation.

## Why not Notion MCP?

The Notion MCP server is great for interactive use, but costs **3,000–6,000 tokens** per session
just to load its tool definitions. When an AI agent calls Notion dozens of times per session,
that overhead compounds. `notion-agent-cli` uses subprocess calls instead — zero token overhead,
same functionality, plus higher-level helpers not in the MCP server.

## Installation

```bash
npm install -g notion-agent-cli
notion auth setup
```

## Quick Start

```bash
# First-time setup (interactive wizard)
notion auth setup

# Or set token directly
notion auth set-token secret_xxxx...
notion auth test

# Query a database
notion db query <db-id> --filter "Status:=:Active" --output table

# Add a row
notion db add <db-id> Name="My Item" Status="Active"

# Search
notion search "my query" --type page --output ids
```

## Commands

### Auth
```
notion auth setup              # Interactive wizard
notion auth set-token <token>  # Store token directly
notion auth test               # Verify connection
notion auth status             # Show token + workspace
```

### Database
```
notion db schema <db-id>                              # Show schema
notion db query <db-id> [--filter P:OP:V]...         # Query rows
notion db info <db-id>                               # Raw metadata
notion db add <db-id> [KEY=VALUE]...                 # Add row
notion db upsert <db-id> --match P:V [KEY=VALUE]...  # Insert or update
notion db update-row <page-id> [KEY=VALUE]...        # Update row
notion db add-option <db-id> <prop> --option NAME    # Add select option
notion db batch-add <db-id> --data @file.json        # Bulk insert
notion db create <parent-id> <title>                 # Create database
notion db delete <db-id>                             # Archive database
notion db update-schema <db-id> --data JSON          # Update schema
```

### Page
```
notion page create <parent-id> --title TITLE   # Create page
notion page get <page-id>                      # Get page
notion page get-property <page-id> <prop>      # Get property
notion page set <page-id> [KEY=VALUE]...       # Update properties
notion page append <page-id> --data MARKDOWN   # Append blocks
notion page delete <page-id>                   # Archive page
notion page restore <page-id>                  # Restore page
notion page move <page-id> <new-parent-id>     # Move page
```

### Block
```
notion block list <block-id>                         # List children
notion block get <block-id>                          # Get block
notion block append <block-id> --type T --text TEXT  # Append block
notion block update <block-id> --data JSON           # Update block
notion block delete <block-id>                       # Delete block
```

### Comment / Search / User
```
notion comment add <page-id> <text>
notion comment list <page-id>
notion search [QUERY] [--type page|database] [--output json|ids]
notion user list
notion user get <user-id>
notion user me
```

## Output Formats

Most commands support `--output json|table|ids|id`:
- `json` — pretty-printed JSON (default)
- `table` — formatted ASCII table
- `ids` — one ID per line (good for scripting)
- `id` — single ID (for create commands)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Authentication failed |
| 2 | Resource not found |
| 3 | Validation error |
| 4 | API error |
| 5 | Resource already exists |
| 6 | Upsert matched multiple rows |
| 7 | Dry run completed |

## --data Input

Many commands accept `--data`:
- `--data '{"key": "value"}'` — inline JSON
- `--data @path/to/file.json` — read from file
- `--data -` — read from stdin

## For AI Agents

```bash
# Use NOTION_API_KEY env var + NOTION_MODE=auto to suppress prompts
export NOTION_API_KEY=secret_xxxx
export NOTION_MODE=auto

# All commands output JSON to stdout, errors to stderr
notion db query <db-id> --output json 2>/dev/null
```

## Development

```bash
git clone https://github.com/henryreith/notion-cli
cd notion-cli
npm install
npm run build
npm test
```

## License

MIT
