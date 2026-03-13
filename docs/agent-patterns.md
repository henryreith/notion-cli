# Agent Patterns

Cookbook for AI agents and automation scripts using `notion-agent-cli`.

## Basic Setup for Agents

Always set these environment variables to ensure non-interactive operation:

```bash
export NOTION_API_KEY=secret_xxxx...
export NOTION_MODE=auto   # never prompts for confirmation
```

Or use `--mode auto` per command.

## Subprocess Pattern

### Node.js / TypeScript

```typescript
import { execSync } from 'child_process'

function notionQuery(dbId: string, filter?: string): object[] {
  const filterArg = filter ? `--filter "${filter}"` : ''
  const output = execSync(
    `notion db query ${dbId} ${filterArg} --output json`,
    { env: { ...process.env, NOTION_MODE: 'auto' } }
  )
  return JSON.parse(output.toString())
}

function notionAdd(dbId: string, props: Record<string, string>): string {
  const kvArgs = Object.entries(props).map(([k, v]) => `"${k}=${v}"`).join(' ')
  const id = execSync(
    `notion db add ${dbId} ${kvArgs} --output id`,
    { env: { ...process.env, NOTION_MODE: 'auto' } }
  ).toString().trim()
  return id
}
```

### Python

```python
import subprocess
import json
import os

def notion_query(db_id, filter=None):
    cmd = ['notion', 'db', 'query', db_id, '--output', 'json']
    if filter:
        cmd += ['--filter', filter]
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        env={**os.environ, 'NOTION_MODE': 'auto'}
    )
    result.check_returncode()
    return json.loads(result.stdout)

def notion_add(db_id, **props):
    kv_args = [f'{k}={v}' for k, v in props.items()]
    result = subprocess.run(
        ['notion', 'db', 'add', db_id, *kv_args, '--output', 'id'],
        capture_output=True, text=True,
        env={**os.environ, 'NOTION_MODE': 'auto'}
    )
    result.check_returncode()
    return result.stdout.strip()
```

### Bash

```bash
#!/usr/bin/env bash
set -euo pipefail
export NOTION_API_KEY="${NOTION_API_KEY:?NOTION_API_KEY required}"
export NOTION_MODE=auto

DB_ID="abc123..."

# Query and process
notion db query "$DB_ID" --filter "Status:=:Active" --output ids | while read -r page_id; do
  echo "Processing: $page_id"
  notion page set "$page_id" Status="In Progress"
done
```

## Piping and Chaining

### Bulk status update

```bash
# Get all active items, mark as Done
notion db query <db-id> --filter "Status:=:Active" --output ids \
  | xargs -I{} notion page set {} "Status=Done"
```

### Move pages matching a query

```bash
notion search "old project" --type page --output ids \
  | xargs -I{} notion page move {} <new-parent-id>
```

### Export to CSV via jq

```bash
notion db query <db-id> --output json \
  | jq -r '.[] | [.Name, .Status, .Priority] | @csv'
```

## Dynamic Option Creation

When adding rows with values not yet in your select options, use `--add-options`:

```bash
# If "In Review" doesn't exist as a Status option yet, create it automatically
notion db add <db-id> Name="PR #42" Status="In Review" --add-options

# Works with batch-add too — options created as encountered
notion db batch-add <db-id> --data @rows.json
# (batch-add always auto-creates options)
```

## Knowledge Base Batch Ingestion

Load a set of articles into a Notion database in one shot:

```bash
# articles.json
cat articles.json
# [
#   {"Title": "Getting Started", "Category": "docs", "URL": "https://..."},
#   {"Title": "API Reference",   "Category": "docs", "URL": "https://..."},
#   ...25 entries...
# ]

notion db batch-add <kb-db-id> --data @articles.json --continue-on-error
```

With `--continue-on-error`, rows that fail (e.g. duplicate constraints) are skipped and a
summary is printed at the end.

**Dry-run first to validate:**

```bash
notion db batch-add <kb-db-id> --data @articles.json --dry-run
# → validates all rows, prints what would be created, exits 7 (DRY_RUN)
```

## Upsert Pattern

Upsert is insert-or-update — ideal for syncing external data to Notion:

```bash
# Sync a task: create if new, update if exists (match on Name)
notion db upsert <db-id> \
  --match Name:"JIRA-123" \
  Status="In Progress" \
  Assignee="alice@example.com"
```

In scripts, check the exit code to know what happened:
- Exit 0 → success (created or updated)
- Exit 6 → multiple rows matched (ambiguous) — narrow your `--match`

## Error Handling

All errors are JSON on **stderr**, nothing on **stdout**:

```bash
if ! result=$(notion db query "$DB_ID" --output json 2>/tmp/err); then
  echo "Query failed:"
  cat /tmp/err  # {"error": "Not authorized", "code": 403}
  exit 1
fi
```

### Exit codes

| Code | Meaning | Common cause |
|------|---------|--------------|
| 0 | Success | — |
| 1 | Auth failed | Bad or missing token |
| 2 | Not found | Wrong ID |
| 3 | Validation | Unknown property name |
| 4 | API error | Rate limit, Notion outage |
| 5 | Already exists | Duplicate create |
| 6 | Ambiguous | Upsert matched >1 row |
| 7 | Dry run | `--dry-run` flag used |

```bash
notion db add <db-id> Name="Test" Status="Bogus"
# exits 3 if "Bogus" is not a valid Status option and --add-options not set
```

## Schema Caching

The CLI caches database schemas for 15 minutes in `~/.cache/notion-agent/schemas/`.
This means repeated `db add` or `db query` calls in a loop don't hit the API for schema
lookups — only for the actual data operations.

To force a fresh schema (e.g. after adding a new property):

```bash
notion db schema <db-id> --refresh
# or bypass cache entirely:
notion db add <db-id> Name="Test" --no-cache
```

## Agent Skill Integration

When used as a Claude skill, the CLI is invoked directly as shell commands. A minimal skill
definition:

```json
{
  "name": "notion",
  "description": "Query and update Notion databases, pages, and blocks",
  "invocation": "notion"
}
```

The skill only loads when the agent needs Notion — zero tokens otherwise. See the
`.claude-plugin/` directory for the full skill definition.
