---
name: notion-shared
description: Prerequisites and common patterns for notion-agent-cli — auth, IDs, exit codes, --data, --output
type: service
---

# notion-agent-cli — Shared Patterns

## Install

```bash
pip install notion-agent-cli
```

## Authentication

```bash
# Option 1: environment variable (preferred for agents/scripts)
export NOTION_API_KEY=secret_xxx

# Option 2: persisted config (for interactive use)
notion auth set-token secret_xxx
notion auth status   # shows token prefix + test result
notion auth test     # quick connectivity check
```

## Finding IDs

Notion IDs appear in page/database URLs:
```
https://www.notion.so/My-Page-<32-char-hex-id>
https://www.notion.so/<workspace>/<32-char-hex-id>?v=<view-id>
```

Both hyphenated UUID and 32-char hex are accepted:
```bash
notion db schema xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
notion db schema xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | proceed |
| 1 | Auth error | check `NOTION_API_KEY` |
| 2 | Not found | resource doesn't exist |
| 3 | Validation error | check schema — unknown property or wrong type |
| 4 | API error | Notion API error, inspect stderr |
| 5 | Already exists | resource exists |
| 6 | Ambiguous match | upsert matched >1 row, narrow `--match` |
| 7 | Dry run | completed without writing |

Always check `$?` / `result.returncode`:
```bash
notion db add <id> "Name=Test" || echo "Failed: $?"
```

## The `--data` Input Pattern

```bash
# Inline JSON
notion db add <db-id> --data '{"Name": "Page Title", "Status": "Active"}'

# From file
notion db add <db-id> --data @properties.json

# From stdin
echo '{"Name": "x"}' | notion db add <db-id> --data -
cat batch.json | notion db batch-add <db-id> --data -
```

Key=value positional args merge with `--data`:
```bash
notion db add <db-id> "Name=My Page" "Status=Active" "Tags=python,cli"
```

## Output Modes

| Flag | Output | Use case |
|------|--------|---------|
| `--output json` | Full Notion API object | default, parse in code |
| `--output table` | Human-readable table | `db query` only |
| `--output ids` | One ID per line | pipeline chaining |
| `--output id` | Single ID | `db add`, `page create` |
| `--output properties` | Key=value pairs | `page get` |

```bash
# Pipeline: get IDs → delete
notion db query <db-id> --filter "Status:=:Archived" --output ids \
  | xargs -I{} notion page delete {} --mode ci

# Get schema as JSON
notion db schema <db-id> --output json | jq '.properties | keys'
```

## Agent Mode (suppress prompts)

```bash
# Via flag
notion page delete <page-id> --mode ci
notion db delete <db-id> --mode ci --confirm

# Via env (sets for all commands)
export NOTION_MODE=ci
```

## Error Parsing

Errors always go to stderr as JSON:
```bash
notion db add <db-id> "Status=InvalidOption" 2>err.json
cat err.json  # {"error": "unknown option ...", "property": "Status"}
```

```python
import json, subprocess

result = subprocess.run(["notion", "db", "add", db_id, "--data", json.dumps(props)],
                        capture_output=True, text=True)
if result.returncode != 0:
    err = json.loads(result.stderr)
    print(f"Error: {err['error']}")
```
