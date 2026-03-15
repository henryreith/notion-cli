# CLAUDE.md — notion-agent-cli (Node.js/TypeScript)

## Project Purpose

**notion-agent-cli** is a zero-overhead CLI for the Notion API, designed for:
- AI agents calling Notion from subprocess (no MCP context overhead: 3,000–6,000 tokens saved per session)
- Shell scripts and automation pipelines
- Human-readable output with machine-parseable JSON mode

npm package: `notion-agent-cli` | CLI binaries: `notion` + `notion-agent`

## Architecture

```
src/
  index.ts          # exports version + createClient
  cli.ts            # Commander root program, --mode flag, registers subcommands
  client.ts         # createNotionClient() — wraps @notionhq/client, reads token
  errors.ts         # ExitCode enum (0–7), handleError(), die()
  output.ts         # printJSON / printTable / printIds / printId
  coerce.ts         # buildFilter(), coerceProperties(), parseKV(), markdownToBlocks()
  schema.ts         # SchemaCache (disk JSON, 15-min TTL) + PropertyResolver
  modes.ts          # getMode(), confirm() — auto/interactive/ci
  config.ts         # readToken(), writeToken() — ~/.config/notion-agent/config.json
  commands/
    auth.ts         # auth setup, set-token, test, status
    db.ts           # all db subcommands
    page.ts         # all page subcommands
    block.ts        # all block subcommands
    comment.ts      # comment add, list
    search.ts       # search
    user.ts         # user list, get, me
tests/
  unit/             # unit tests (vitest)
  integration/      # live API tests (skipped unless env vars set)
  fixtures/         # test data JSON files
```

## Exit Codes

| Code | Constant | Meaning |
|------|----------|---------|
| 0 | SUCCESS | OK |
| 1 | AUTH | Authentication failed |
| 2 | NOT_FOUND | Resource not found |
| 3 | VALIDATION | Invalid input / unknown property |
| 4 | API | Notion API error |
| 5 | EXISTS | Resource already exists |
| 6 | AMBIGUOUS | Upsert matched >1 result |
| 7 | DRY_RUN | Dry run completed (no writes) |

## Command Reference

Global flags (apply before any subcommand):
```
notion --profile <name> <command>    # use a named profile for this command
notion --mode <auto|interactive|ci>  # operating mode override
```

```
notion auth setup [--name <profile>]
notion auth set-token <token>
notion auth test
notion auth status [--output json|text]
notion auth profile list [--output json|text]
notion auth profile add <name> [--token TOKEN]
notion auth profile remove <name>
notion auth profile rename <old-name> <new-name>
notion auth profile use <name>
notion auth profile update <name>

notion db list [--output json|ids] [--limit N] [--page-all]
notion db schema <db-id> [--refresh] [--output json|properties|options] [--no-cache]
notion db query <db-id> [--filter PROP:OP:VALUE]... [--filter-logic and|or] [--sort PROP] [--limit N] [--page-all] [--output json|table|ids]
notion db info <db-id>
notion db list-templates <db-id>
notion db add <db-id> [KEY=VALUE]... [--data JSON|@file|-] [--add-options] [--output json|id]
notion db upsert <db-id> --match PROP:VALUE [KEY=VALUE]... [--data JSON] [--add-options]
notion db update-row <page-id> [KEY=VALUE]... [--data JSON]
notion db add-option <db-id> <property> --option NAME [--option NAME2] [--color COLOR]
notion db batch-add <db-id> --data @file|- [--dry-run] [--continue-on-error]
notion db create <parent-id> <title> [--data schema-json]
notion db delete <db-id> [--confirm]
notion db update-schema <db-id> --data JSON|@file

notion page list <parent-id> [--output json|ids]
notion page create <parent-id> --title TITLE [--data JSON] [--output json|id]
notion page get <page-id> [--output json|properties]
notion page get-property <page-id> <property-name>
notion page set <page-id> [KEY=VALUE]... [--data JSON]
notion page append <page-id> --data MARKDOWN|JSON|@file|-
notion page delete <page-id> [--confirm]
notion page restore <page-id>
notion page move <page-id> <new-parent-id>

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

## Key Implementation Details

### API
- **SDK:** `@notionhq/client` v5.x — wraps API automatically
- **Version header:** `Notion-Version: 2022-06-28`
- **Base URL:** `https://api.notion.com/v1`
- **Rate limit:** 3 req/sec → 350ms between requests in batch commands

### ID Format
- Normalise to no-hyphen 32-char hex via `normaliseId()` in client.ts
- Accept Notion page URLs as input — extract 32-char hex ID from URL path

### Token Priority
1. `NOTION_API_KEY` environment variable
2. `NOTION_PROFILE` environment variable → look up named profile
3. `--profile <name>` CLI flag → look up named profile (sets `NOTION_PROFILE` env)
4. `default_profile` from config file (`~/.config/notion-agent/config.json`)
5. Legacy v1 format `{ token }` — auto-migrated to `profiles.default` on first read

### Cache
- Location: `~/.cache/notion-agent/schemas/<db-id>.json`
- TTL: 15 minutes (900 seconds)
- Bypass with `--no-cache` or `--refresh`

### Error Output
All errors printed as JSON to **stderr**:
```json
{"error": "message", "additional": "context"}
```

## Operating Modes

- `auto` (default when non-TTY): never prompts
- `interactive` (default when TTY): prompts for destructive operations
- `ci`: alias for auto

Mode detection: `--mode` flag → `NOTION_MODE` env → TTY detection

## `--data` Input Pattern

- `--data '{"key": "value"}'` — inline JSON
- `--data @path/to/file.json` — read from file
- `--data -` — read from stdin

## Milestone Status

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Research & planning | COMPLETE |
| M1 | Scaffold: package.json, tsconfig, CLI skeleton, auth commands | COMPLETE |
| M2 | Core infrastructure: client.ts, errors.ts, output.ts, coerce.ts, modes.ts | COMPLETE |
| M3 | Schema module: SchemaCache, PropertyResolver | COMPLETE |
| M4 | db read commands: schema, query, info, list-templates | COMPLETE |
| M5 | db write commands: add, upsert, update-row, add-option, batch-add, create, delete, update-schema | COMPLETE |
| M6 | page commands: create, get, get-property, set, append, delete, restore, move | COMPLETE |
| M7 | block commands: list, get, append, update, delete | COMPLETE |
| M8 | comment, search, user commands | COMPLETE |
| M9 | Integration tests + CI/CD (GitHub Actions for Node.js) | COMPLETE |
| M10 | Polish: skills, AGENTS.md, README, npm publish setup | COMPLETE |

## Skills and Plugin Manifest Sync

Skills live in `.claude/skills/*.md`. The plugin manifest is at `.claude-plugin/plugin.json`.

**Rule:** Every `.claude/skills/<name>.md` file must have a matching entry in `.claude-plugin/plugin.json`, and vice versa. Keep them in sync.

When adding a skill:
1. Create `.claude/skills/<name>.md`
2. Add entry to `.claude-plugin/plugin.json` under `"skills"`:
   ```json
   { "name": "<name>", "path": "../.claude/skills/<name>.md", "description": "<one-liner>" }
   ```
3. Update the Command Reference in `CLAUDE.md` if new commands are introduced.

When removing a skill: delete the `.md` file and remove the plugin.json entry.

## Testing

```bash
npm test                    # unit tests
npm run build               # compile TypeScript
./dist/cli.js --version     # → 0.1.0
```
