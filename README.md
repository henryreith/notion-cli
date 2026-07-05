# notion-agent-cli

[![npm version](https://img.shields.io/npm/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![npm downloads](https://img.shields.io/npm/dm/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![unpacked size](https://img.shields.io/npm/unpacked-size/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![types](https://img.shields.io/npm/types/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![Node.js >=18](https://img.shields.io/node/v/notion-agent-cli)](https://www.npmjs.com/package/notion-agent-cli)
[![provenance](https://img.shields.io/badge/provenance-OIDC_signed-blue)](https://www.npmjs.com/package/notion-agent-cli#provenance)
[![CI](https://github.com/henryreith/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/henryreith/notion-cli/actions/workflows/ci.yml)
[![Release](https://github.com/henryreith/notion-cli/actions/workflows/release.yml/badge.svg)](https://github.com/henryreith/notion-cli/actions/workflows/release.yml)
[![Publish](https://github.com/henryreith/notion-cli/actions/workflows/publish.yml/badge.svg)](https://github.com/henryreith/notion-cli/actions/workflows/publish.yml)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-11_skills-8A2BE2)](skills/README.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757)](#claude-code-plugin)
[![license](https://img.shields.io/github/license/henryreith/notion-cli)](LICENSE)
[![last commit](https://img.shields.io/github/last-commit/henryreith/notion-cli)](https://github.com/henryreith/notion-cli/commits/main)
[![stars](https://img.shields.io/github/stars/henryreith/notion-cli)](https://github.com/henryreith/notion-cli/stargazers)

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

## Agent Skills (Claude, and any other agent)

Eleven ready-made skills live in [`skills/`](skills/) ([index](skills/README.md)),
following the [Agent Skills](https://agentskills.io) open standard
(`skills/<name>/SKILL.md`, validated with the official `skills-ref` tool). They
cost ~0 tokens when idle and only load when the agent decides to call Notion —
unlike MCP, which loads unconditionally every session. Every documented command
and flag is CI-validated against the actual CLI, so the skills can't drift from
the implementation. Want a workflow we don't ship? See
[Build your own skill](skills/README.md#build-your-own-skill).

### Claude Code (plugin)

```
/plugin marketplace add henryreith/notion-cli
/plugin install notion-agent@notion-cli
```

That's it — the skills (`notion-shared`, `notion-db`, `notion-page`, `notion-search`,
`notion-schema-design`, `notion-reporting`, `notion-capture`, plus the
`backup-sync`, `crm-pipeline`, `knowledge-base`, and `task-tracker` recipes)
become available in every session.

### Any other agent

The skills are plain markdown with spec-standard frontmatter (`name`,
`description`, `compatibility`) — no Claude-specific features. Any agent that
can run shell commands can use them: Codex, Cursor, or a personal/home agent
like Hermes. To wire one up:

1. `npm install -g notion-agent-cli` and set `NOTION_API_KEY`
2. Point your agent at the skills, whichever way it ingests context:
   - copy `skills/` into your agent's skill directory (Agent Skills-compatible tools pick them up as-is)
   - or drop the SKILL.md contents into its system prompt / knowledge base
   - the npm package also ships the skills: `node_modules/notion-agent-cli/skills/`
3. Start with `notion-shared` (auth, IDs, exit codes), add command-group skills as needed

Since the CLI is just a subprocess with JSON output and stable exit codes, any agent
framework that can execute shell commands gets full Notion access from these docs alone.

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
notion db upsert <db-id> --match PROP:VALUE [--match PROP:VALUE]... [KEY=VALUE]... [--add-options]
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
notion block delete <block-id> [--confirm]

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
export NOTION_API_KEY=ntn_xxxx...
export NOTION_MODE=auto

# All commands output JSON to stdout, errors as JSON to stderr
notion db query <db-id> --output json
notion db add <db-id> Name="Task" Status="Active" --output id

# Pipe IDs through xargs
notion db query <db-id> --filter "Status:=:Done" --output ids \
  | xargs -I{} notion page delete {} --confirm
```

**Delete safety:** in non-interactive mode, `page delete`, `db delete`, and
`block delete` refuse with exit 3 unless `--confirm` is passed — so a script or
agent can never delete by accident. Set `NOTION_AUTO_CONFIRM=1` to skip the gate
in trusted pipelines.

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
