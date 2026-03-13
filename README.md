# notion-agent-cli

[![npm](https://img.shields.io/npm/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![Node.js >=18](https://img.shields.io/node/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![CI](https://github.com/henryreith/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/henryreith/notion-cli/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Zero-overhead Notion CLI for AI agents, shell scripts, and automation.
> Full parity with the Notion MCP server — without the token cost.

## Why not MCP?

The Notion MCP server loads **3,000–6,000 tokens** of tool definitions into your context window every session, whether you call Notion once or never. `notion-agent-cli` uses subprocess calls instead — the skill only loads when invoked (~1,000 tokens, once), and costs zero tokens the rest of the session.

**For an agent doing 10 Notion calls in a 50-step workflow:**

| | MCP | notion-agent-cli |
|---|---|---|
| Token overhead | ~4,500 tokens (always) | ~1,000 tokens (once) |
| Server process | Required | None |
| Extra helpers | — | upsert, batch-add, schema cache, `--add-options`, dry-run |

→ [Full comparison](docs/mcp-vs-cli.md)

## Install

```bash
npm install -g notion-agent-cli
notion auth setup
```

Requires Node.js ≥18.

## Quick Start

```bash
# Interactive auth setup
notion auth setup

# Query a database
notion db query <db-id> --filter "Status:=:Active" --output table

# Add a row
notion db add <db-id> Name="My Item" Status="Active" --add-options

# Upsert (insert or update)
notion db upsert <db-id> --match Name:"My Item" Status="Done"

# Search
notion search "meeting notes" --type page --output ids
```

## What's Included

All 22 Notion MCP tools as CLI commands, plus 10+ higher-level helpers:

### MCP Parity

| Operation | Command |
|-----------|---------|
| Query database | `notion db query` |
| Create page | `notion page create` |
| Update page | `notion page set` |
| Get page | `notion page get` |
| Append blocks | `notion page append` |
| Delete page | `notion page delete` |
| Search | `notion search` |
| List users | `notion user list` |
| Add comment | `notion comment add` |
| List comments | `notion comment list` |
| Get block | `notion block get` |
| Update block | `notion block update` |
| Delete block | `notion block delete` |

### CLI-Only Extras

| Feature | Command | Description |
|---------|---------|-------------|
| Upsert | `notion db upsert` | Insert or update based on match condition |
| Bulk insert | `notion db batch-add` | Load JSON array of rows in one shot |
| Schema cache | automatic | 15-min local cache, skip API round-trips |
| Auto-create options | `--add-options` | Create missing select options on the fly |
| Markdown I/O | `notion page append` | Write Markdown, auto-converted to Notion blocks |
| Dry run | `--dry-run` | Validate without writing (exits 7) |
| Pagination | `--page-all` | Fetch all pages automatically |
| IDs output | `--output ids` | One ID per line, perfect for xargs piping |

## Skills for Claude

Install the skill so Claude can call Notion with zero token overhead when idle:

```bash
# The .claude-plugin/ directory is already set up in this repo
# Claude will discover it automatically when working in this directory
```

The skill definition costs ~0 tokens when not in use. It only loads when Claude decides
to call Notion — unlike MCP, which loads unconditionally every session.

## Command Reference

### Auth
```
notion auth setup              # Interactive wizard
notion auth set-token <token>  # Store token directly
notion auth test               # Verify connection
notion auth status             # Show token + workspace
```

### Database
```
notion db schema <db-id> [--refresh] [--output json|properties|options]
notion db query <db-id> [--filter PROP:OP:VALUE]... [--sort PROP] [--limit N] [--page-all] [--output json|table|ids]
notion db info <db-id>
notion db add <db-id> [KEY=VALUE]... [--data JSON|@file|-] [--add-options] [--output json|id]
notion db upsert <db-id> --match PROP:VALUE [KEY=VALUE]... [--add-options]
notion db update-row <page-id> [KEY=VALUE]... [--data JSON]
notion db add-option <db-id> <prop> --option NAME [--color COLOR]
notion db batch-add <db-id> --data @file|- [--dry-run] [--continue-on-error]
notion db create <parent-id> <title> [--data schema-json]
notion db delete <db-id> [--confirm]
notion db update-schema <db-id> --data JSON|@file
```

### Page
```
notion page create <parent-id> --title TITLE [--output json|id]
notion page get <page-id> [--output json|properties]
notion page get-property <page-id> <property-name>
notion page set <page-id> [KEY=VALUE]... [--data JSON]
notion page append <page-id> --data MARKDOWN|JSON|@file|-
notion page delete <page-id> [--confirm]
notion page restore <page-id>
notion page move <page-id> <new-parent-id>
```

### Block / Comment / Search / User
```
notion block list <block-id> [--output json|ids]
notion block get <block-id>
notion block append <block-id> --type TYPE --text TEXT
notion block update <block-id> --data JSON|@file
notion block delete <block-id>

notion comment add <page-id> <text>
notion comment list <page-id> [--output json|ids]

notion search [QUERY] [--type page|database] [--sort last_edited|relevance] [--limit N] [--page-all] [--output json|ids]

notion user list [--output json|ids]
notion user get <user-id>
notion user me
```

→ [Full command reference with examples](docs/commands.md)

## For AI Agents

```bash
# Set env vars — no prompts, no config file needed
export NOTION_API_KEY=secret_xxxx...
export NOTION_MODE=auto

# All commands output JSON to stdout, errors as JSON to stderr
notion db query <db-id> --output json
notion db add <db-id> Name="Task" Status="Active" --output id

# Pipe IDs through xargs
notion db query <db-id> --filter "Status:=:Done" --output ids \
  | xargs -I{} notion page delete {} --confirm
```

**Exit codes** — machine-readable, always:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Auth failed |
| 2 | Not found |
| 3 | Validation error |
| 4 | API error |
| 5 | Already exists |
| 6 | Upsert ambiguous |
| 7 | Dry run |

→ [Agent patterns cookbook](docs/agent-patterns.md)

## `--data` Input

Many commands accept `--data` in three forms:
- `--data '{"key": "value"}'` — inline JSON
- `--data @path/to/file.json` — read from file
- `--data -` — read from stdin

## Contributing

```bash
git clone https://github.com/henryreith/notion-cli
cd notion-cli
npm install
npm run build
npm test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT
