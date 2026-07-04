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
  modes.ts          # getMode(), confirmDestructive() — auto/interactive/ci + delete gate
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
notion db upsert <db-id> --match PROP:VALUE [--match PROP:VALUE]... [KEY=VALUE]... [--data JSON] [--add-options]
notion db update-row <page-id> [KEY=VALUE]... [--data JSON]
notion db add-option <db-id> <property> --option NAME [--option NAME2] [--color COLOR]
notion db batch-add <db-id> --data @file|- [--add-options] [--dry-run] [--continue-on-error]
notion db create <parent-id> <title> [--data schema-json]
notion db delete <db-id> [--confirm]
notion db update-schema <db-id> --data JSON|@file

notion page list <parent-id> [--output json|ids]
notion page create <parent-id> --title TITLE [--data JSON] [--output json|id]
notion page get <page-id> [--output json|properties]
notion page get-property <page-id> <property-name>
notion page set <page-id> [KEY=VALUE]... [--data JSON]
notion page append <page-id> --data MARKDOWN|JSON|@file|-
notion page get-markdown <page-id>
notion page set-markdown <page-id> --data MARKDOWN|@file|-
notion page delete <page-id> [--confirm]
notion page restore <page-id>
notion page move <page-id> <new-parent-id>

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

- `auto` (default when non-TTY): never prompts; destructive commands (`page delete`, `db delete`, `block delete`) refuse with exit 3 unless `--confirm` is passed or `NOTION_AUTO_CONFIRM=1` is set
- `interactive` (default when TTY): prompts y/N for destructive operations (`--confirm` skips the prompt)
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

## Skills and Plugin

Skills live in `skills/<name>/SKILL.md` (repo root), following the
[Agent Skills](https://agentskills.io) open standard: frontmatter is just
`name`, `description`, `license` — no Claude-specific fields, so the skills
stay portable to other agents. The npm package ships them (`files` includes
`skills`).

The repo is also a Claude Code plugin: `.claude-plugin/plugin.json` (manifest)
+ `.claude-plugin/marketplace.json` (so `/plugin marketplace add
henryreith/notion-cli` works). Skills are auto-discovered from `skills/` —
there is NO per-skill list to keep in sync.

When adding a skill: create `skills/<name>/SKILL.md` and update the Command
Reference here if new commands are introduced. When removing: delete the
directory. Skill descriptions are trigger-oriented ("what it does + when to
use it"); heavy detail goes in `references/*.md` files linked one level deep
from SKILL.md.

Docs drift is enforced: `tests/unit/skills-docs.test.ts` validates every
`notion` command and flag in skills/ and docs/ bash blocks against the actual
commander program. If it fails, the docs are wrong (or the CLI changed) — fix
whichever is lying.

## Testing

```bash
npm test                    # unit tests
npm run build               # compile TypeScript
./dist/cli.js --version     # → 0.1.0
```
