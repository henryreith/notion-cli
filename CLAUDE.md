# CLAUDE.md — notion-agent-cli

<!-- MAINTENANCE RULES (read before editing this file)
Target length: 400 lines. Hard maximum: 700 lines.
ADD to this file when: a new command group is completed, a non-obvious design
decision is made, a gotcha/edge case is discovered, or a stable pattern is
confirmed across multiple milestones.
DO NOT ADD: session-specific task status, temporary scaffolding notes, or
anything stale in 24 hours.
When adding content, remove/compress outdated entries to stay within 700 lines.
Every agent that modifies the codebase must check if CLAUDE.md needs updating.
-->

## Project Purpose

**notion-agent-cli** is a zero-overhead CLI for the Notion API, designed for:
- AI agents calling Notion from subprocess (no MCP context overhead: 3,000–6,000 tokens saved per session)
- Shell scripts and automation pipelines
- Human-readable output with machine-parseable JSON mode

PyPI package: `notion-agent-cli` | CLI binary: `notion`

## Architecture

```
notion/
  __init__.py          # version = "0.1.0"
  __main__.py          # entry point: python -m notion
  cli.py               # root Click group, --mode flag, subgroup registration
  client.py            # NotionClient: auth, HTTP verbs, pagination, retry
  schema.py            # SchemaCache (disk, 15-min TTL) + PropertyResolver
  coerce.py            # Per-type coerce functions + markdown_to_blocks()
  output.py            # print_json, print_table, print_ids
  modes.py             # get_mode(), confirm()
  errors.py            # ExitCode enum + error hierarchy
  models.py            # Pydantic stubs (extend as needed)
  commands/
    auth.py            # auth set-token, test, status
    db.py              # db schema, query, add, upsert, add-option, batch-add,
                       #   update-row, create, delete, update-schema
    page.py            # page create, get, get-property, set, append, delete, restore
    block.py           # block list, get, append, update, delete
    comment.py         # comment add, list
    search.py          # search (direct command, not group)
    user.py            # user list, get, me
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

```
notion auth set-token <token>
notion auth test
notion auth status

notion db schema <db-id> [--refresh] [--output json|properties|options] [--no-cache]
notion db query <db-id> [--filter PROP:OP:VALUE]... [--sort PROP] [--limit N] [--page-all] [--output json|table|ids]
notion db add <db-id> [KEY=VALUE]... [--data JSON|@file|-] [--add-options] [--output json|id]
notion db upsert <db-id> --match PROP:VALUE [KEY=VALUE]... [--data JSON] [--add-options]
notion db update-row <page-id> [KEY=VALUE]... [--data JSON]
notion db add-option <db-id> <property> --option NAME [--option NAME2] [--color COLOR]
notion db batch-add <db-id> --data @file|- [--dry-run] [--continue-on-error]
notion db create <parent-id> <title> [--data schema-json]
notion db delete <db-id> [--confirm]
notion db update-schema <db-id> --data JSON|@file

notion page create <parent-id> --title TITLE [--data JSON] [--output json|id]
notion page get <page-id> [--output json|properties]
notion page get-property <page-id> <property-name>
notion page set <page-id> [KEY=VALUE]... [--data JSON]
notion page append <page-id> --data MARKDOWN|JSON|@file
notion page delete <page-id> [--confirm]
notion page restore <page-id>

notion block list <block-id> [--output json|ids]
notion block get <block-id>
notion block append <block-id> --type TYPE --text TEXT
notion block update <block-id> --data JSON
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
- **Version header:** `Notion-Version: 2022-06-28` (required on every request)
- **Base URL:** `https://api.notion.com/v1`
- **Rate limit:** 3 req/sec → `time.sleep(0.34)` between requests in batch commands
- **409 Conflict:** retry once after 1 second

### ID Format
- Notion accepts both hyphenated (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) and non-hyphenated (32-char hex) formats
- Normalise to **no-hyphen 32-char hex** for all API calls
- Accept Notion page URLs as input — extract 32-char hex ID from URL path

### Token Priority
1. `NOTION_API_KEY` environment variable
2. Config file: `~/.config/notion-agent/config.json`

### Cache
- Location: `~/.cache/notion-agent/schemas/<db-id>.json`
- TTL: 15 minutes (900 seconds)
- Bypass with `--no-cache` flag (on read commands) or `--refresh` (on db schema)

### Error Output
All errors are printed as JSON to **stderr**:
```json
{"error": "message", "additional": "context"}
```

## Operating Modes

Controlled by `--mode` flag or `NOTION_MODE` env var:
- `auto` (default when non-TTY): never prompts, proceeds automatically
- `interactive` (default when TTY): prompts for destructive operations
- `ci`: alias for auto, never prompts

Mode detection priority: `--mode` flag → `NOTION_MODE` env → TTY detection

## `--data` Input Pattern

Many commands accept `--data` for property input:
- `--data '{"key": "value"}'` — inline JSON
- `--data @path/to/file.json` — read from file
- `--data -` — read from stdin

Key=value positional args are also accepted and merged with `--data`.

## Property Coercion Table

| Notion Type | Input | Coerced To |
|-------------|-------|-----------|
| title | `"My Title"` | `{"title": [{"type": "text", "text": {"content": "My Title"}}]}` |
| rich_text | `"Some text"` | `{"rich_text": [{"type": "text", "text": {"content": "Some text"}}]}` |
| select | `"Option"` | `{"select": {"name": "Option"}}` |
| multi_select | `"a,b,c"` or `["a","b","c"]` | `{"multi_select": [{"name": "a"}, ...]}` |
| date | `"2024-01-15"` | `{"date": {"start": "2024-01-15", "end": null}}` |
| number | `"42"` | `{"number": 42}` |
| url | `"https://..."` | `{"url": "https://..."}` |
| checkbox | `"true"/"false"` | `{"checkbox": true/false}` |
| relation | `"id"` or `["id1","id2"]` | `{"relation": [{"id": "id"}]}` |
| people | `"uid"` or `["uid1","uid2"]` | `{"people": [{"object": "user", "id": "uid"}]}` |

**Case sensitivity:** multi_select and select values are case-sensitive. Never lowercase option values.

## Pagination Pattern

```python
# POST /v1/databases/{id}/query
body = {"start_cursor": cursor}  # omit on first call
response = client.post(f"/databases/{db_id}/query", body)
results.extend(response["results"])
if response["has_more"]:
    cursor = response["next_cursor"]
    # repeat
```

## Design Decisions

See `DECISIONS.md` for full rationale. Key decisions:
- httpx (not requests) for async-compatible future and better timeout handling
- Rich for table output (not tabulate) — already in dep tree for progress bars
- Pydantic v2 for schema validation stubs — using model_validate() not parse_obj()
- Click not argparse — composable groups, built-in help, type coercion
- No async in v0.1 — sync httpx, simpler for subprocess callers

## Testing

```bash
# Unit tests (no API key needed)
pytest tests/ -v --ignore=tests/integration

# Integration tests (requires real key)
NOTION_API_KEY=<key> NOTION_TEST_PARENT_ID=<id> pytest tests/integration/ -v

# Scaffold check
pytest tests/test_scaffold.py -v
```

## Development Setup

```bash
pip install -e ".[dev]"
notion --version  # → 0.1.0
notion --help     # shows all command groups
```

## Build & Publish

```bash
python -m build          # creates dist/
pip install dist/*.whl   # verify wheel installs
# publish: see DEPLOY.md
```

## Milestone Status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1 — Scaffold | COMPLETE | CLI groups, errors, client, auth commands |
| M2 — Auth & HTTP Client | COMPLETE | NotionClient, _normalise_id, retry logic |
| M3 — Schema Module | COMPLETE | SchemaCache (TTL disk cache), PropertyResolver, coerce.py, markdown_to_blocks |
| M4 — db schema + query | COMPLETE | `notion db schema` (json/properties/options output, cache), `notion db query` (filters, sorts, limit, --page-all), output.py helpers |
| M5 — db add | COMPLETE | `notion db add` (KEY=VALUE args, --data JSON/@file/-, --add-options, --output json|id), _ensure_options helper |
| M6 — db add-option + update-schema | COMPLETE | `notion db add-option` (idempotent, multi-option, case-insensitive, exit 3 for wrong type), `notion db update-schema` (JSON/@file/- input, cache invalidation) |
| M7 — db upsert + update-row | COMPLETE | `notion db upsert` (--match AND logic, schema-aware filters, create/update/exit-6, --add-options), `notion db update-row` (parent DB lookup, PropertyResolver) |
| M8 — page commands | COMPLETE | `notion page create/get/get-property/set/append/delete/restore`, modes.py click import fix |
| M9+ | PENDING | block, comment, search, user commands |
