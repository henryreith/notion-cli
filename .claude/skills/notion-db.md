---
name: notion-db
description: Database commands for notion-agent-cli — schema, query, add, upsert, batch, update-schema
type: service
---

# notion-agent-cli — Database Commands

## Workflow: Schema → Query → Write

Always check the schema before writing to understand property types and option values:

```bash
notion db schema <db-id> --output properties  # see property names + types
notion db schema <db-id> --output options     # see select/multi-select options
```

## db schema

```bash
notion db schema <db-id>                       # full JSON schema
notion db schema <db-id> --output properties   # name: type table
notion db schema <db-id> --output options      # select options per property
notion db schema <db-id> --refresh             # force refresh (bypass 15-min cache)
notion db schema <db-id> --no-cache            # read-through, don't cache
```

## db query

```bash
notion db query <db-id>
notion db query <db-id> --filter "Status:=:Active"
notion db query <db-id> --filter "Name:contains:meeting" --filter "Status:!=:Done"
notion db query <db-id> --sort "Created" --limit 10
notion db query <db-id> --page-all --output ids   # all pages, IDs only
notion db query <db-id> --output table             # human-readable
```

### Filter operators

| Operator | Applies to |
|----------|-----------|
| `=` | text, select, checkbox, date, number |
| `!=` | text, select |
| `contains` | text, multi_select |
| `not_contains` | text, multi_select |
| `starts_with` | text |
| `>` `<` `>=` `<=` | number, date |
| `is_empty` | any |
| `is_not_empty` | any |

Filter syntax: `PROPERTY_NAME:OPERATOR:VALUE`
```bash
--filter "Due Date:>=:2024-01-01"
--filter "Tags:contains:python"
--filter "Completed:=:true"
```

## db add

```bash
# Key=value args
notion db add <db-id> "Name=My Page" "Status=Active" "Priority=High"

# JSON data
notion db add <db-id> --data '{"Name": "My Page", "Status": "Active"}'

# From file, get back the page ID
notion db add <db-id> --data @props.json --output id

# Auto-create missing select options (otherwise exits 3)
notion db add <db-id> "Status=New Option" --add-options
```

### Property coercion examples

```bash
# text / title
notion db add <db-id> "Name=My Title"

# select (case-sensitive)
notion db add <db-id> "Status=In Progress"

# multi_select (comma-separated)
notion db add <db-id> "Tags=python,cli,automation"

# date
notion db add <db-id> "Due=2024-03-15"

# number
notion db add <db-id> "Priority=5"

# checkbox
notion db add <db-id> "Done=true"

# url
notion db add <db-id> "Link=https://example.com"

# relation (page IDs)
notion db add <db-id> "Related=<page-id>"
```

## db upsert

Find-or-create: match on one or more properties, update if found (exit 0), create if not found (exit 0), error if multiple found (exit 6).

```bash
# Upsert by Name
notion db upsert <db-id> --match "Name:My Page" "Status=Done"

# Multi-field match (AND logic)
notion db upsert <db-id> --match "Name:My Page" --match "Owner:Alice" "Status=Done"

# With JSON data
notion db upsert <db-id> --match "Name:x" --data '{"Status": "Active"}'
```

If exit code is 6 (ambiguous), narrow your `--match` to uniquely identify one row.

## db update-row

Update a page you already have the ID for (faster than upsert — no search step):

```bash
notion db update-row <page-id> "Status=Done" "Priority=Low"
notion db update-row <page-id> --data @updates.json
```

## db add-option

Add a new option to a select or multi_select property (idempotent — safe to run twice):

```bash
notion db add-option <db-id> Status --option "New Status"
notion db add-option <db-id> Tags --option "python" --option "cli" --color blue
```

Colors: `default`, `gray`, `brown`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink`, `red`

## db batch-add

Add multiple rows from a JSON array. Use `--dry-run` to validate first:

```bash
# Validate first
notion db batch-add <db-id> --data @batch.json --dry-run

# Then execute
notion db batch-add <db-id> --data @batch.json

# From stdin, continue despite per-row errors
notion db batch-add <db-id> --data - --continue-on-error < batch.json
```

`batch.json` format: array of property objects:
```json
[
  {"Name": "Row 1", "Status": "Active", "Tags": "python,cli"},
  {"Name": "Row 2", "Status": "Done"}
]
```

## db create

Create a new database as a child of a page:

```bash
notion db create <parent-page-id> "My Database"
notion db create <parent-page-id> "My Database" --data @schema.json
```

## db delete

```bash
notion db delete <db-id> --confirm       # interactive
notion db delete <db-id> --mode ci       # agent/script (no prompt)
```

## db update-schema

Add or modify properties on an existing database:

```bash
notion db update-schema <db-id> --data @schema-patch.json
notion db update-schema <db-id> --data '{"new_prop": {"type": "rich_text"}}'
```
