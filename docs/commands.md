# Command Reference

Full reference for all `notion` CLI commands. See [getting-started.md](getting-started.md) for installation and auth setup.

## Global Flags

| Flag | Description |
|------|-------------|
| `--mode auto\|interactive\|ci` | Override prompt behaviour (default: auto when non-TTY, interactive when TTY) |
| `--version` | Print version |
| `--help` | Print help |

---

## auth

### `notion auth setup`
Interactive wizard — prompts for token, saves to config, tests connection.

### `notion auth set-token <token>`
Store a token directly without the wizard.

```bash
notion auth set-token secret_xxxx...
```

### `notion auth test`
Verify the stored token works. Exits 0 on success, 1 on failure.

### `notion auth status`
Show the current token (masked) and workspace name.

---

## db

### `notion db schema <db-id>`

Show the database schema (property names, types, options).

| Flag | Default | Description |
|------|---------|-------------|
| `--output json\|properties\|options` | `properties` | Output format |
| `--refresh` | false | Force re-fetch, ignore cache |
| `--no-cache` | false | Skip cache entirely |

```bash
notion db schema abc123...
notion db schema abc123... --output json
notion db schema abc123... --output options  # show select/multi-select options
```

### `notion db query <db-id>`

Query database rows.

| Flag | Default | Description |
|------|---------|-------------|
| `--filter PROP:OP:VALUE` | — | Filter (repeatable) |
| `--sort PROP` | — | Sort by property |
| `--limit N` | 100 | Max rows |
| `--page-all` | false | Fetch all pages |
| `--output json\|table\|ids` | `json` | Output format |

**Filter operators:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `starts_with`, `is_empty`, `is_not_empty`

```bash
notion db query abc123... --filter "Status:=:Active" --output table
notion db query abc123... --filter "Priority:=:High" --filter "Status:!=:Done" --output json
notion db query abc123... --sort "Created" --limit 10 --output ids
notion db query abc123... --page-all --output json > all-rows.json
```

### `notion db info <db-id>`

Show raw database metadata (title, parent, created/edited times).

### `notion db list-templates <db-id>`

List available templates for the database.

### `notion db add <db-id>`

Add a new row to the database.

| Flag | Default | Description |
|------|---------|-------------|
| `KEY=VALUE` | — | Property values as positional args |
| `--data JSON\|@file\|-` | — | Properties as JSON |
| `--add-options` | false | Auto-create missing select options |
| `--output json\|id` | `json` | Output format |

```bash
notion db add abc123... Name="My Item" Status="Active"
notion db add abc123... --data '{"Name": "My Item", "Priority": "High"}'
notion db add abc123... --data @row.json --output id
notion db add abc123... Name="New Tag" Status="Draft" --add-options
```

### `notion db upsert <db-id>`

Insert a row or update existing if match found.

| Flag | Description |
|------|-------------|
| `--match PROP:VALUE` | Match condition (required) |
| `KEY=VALUE` | Property values |
| `--data JSON` | Properties as JSON |
| `--add-options` | Auto-create missing select options |

```bash
notion db upsert abc123... --match Name:"My Item" Status="Done"
notion db upsert abc123... --match Email:user@example.com --data @update.json
```

### `notion db update-row <page-id>`

Update properties on an existing row.

```bash
notion db update-row page123... Status="Done" Priority="Low"
notion db update-row page123... --data '{"Status": "Done"}'
```

### `notion db add-option <db-id> <property>`

Add a new option to a select or multi-select property.

| Flag | Description |
|------|-------------|
| `--option NAME` | Option name (repeatable) |
| `--color COLOR` | Option colour |

```bash
notion db add-option abc123... Status --option "In Review"
notion db add-option abc123... Tags --option "backend" --option "api" --color blue
```

### `notion db batch-add <db-id>`

Bulk insert rows from a JSON array file.

| Flag | Default | Description |
|------|---------|-------------|
| `--data @file\|-` | — | JSON array of row objects (required) |
| `--dry-run` | false | Validate without writing |
| `--continue-on-error` | false | Skip failed rows, continue |

```bash
notion db batch-add abc123... --data @rows.json
notion db batch-add abc123... --data - < rows.json
notion db batch-add abc123... --data @rows.json --dry-run
```

The input file should be a JSON array:
```json
[
  {"Name": "Row 1", "Status": "Active"},
  {"Name": "Row 2", "Status": "Draft"}
]
```

### `notion db create <parent-id> <title>`

Create a new database.

| Flag | Description |
|------|-------------|
| `--data JSON\|@file` | Initial schema definition |
| `--output json\|id` | Output format |

```bash
notion db create page123... "My Database"
notion db create page123... "Tasks" --data @schema.json
```

### `notion db delete <db-id>`

Archive (soft-delete) a database.

| Flag | Description |
|------|-------------|
| `--confirm` | Skip confirmation prompt |

```bash
notion db delete abc123... --confirm
```

### `notion db update-schema <db-id>`

Update the database schema (add/modify properties).

```bash
notion db update-schema abc123... --data '{"Priority": {"type": "select"}}'
notion db update-schema abc123... --data @schema-patch.json
```

---

## page

### `notion page create <parent-id>`

Create a new page.

| Flag | Default | Description |
|------|---------|-------------|
| `--title TITLE` | — | Page title (required) |
| `--data JSON\|@file` | — | Additional properties |
| `--output json\|id` | `json` | Output format |

```bash
notion page create parent123... --title "My Page"
notion page create parent123... --title "Doc" --output id
notion page create db123... --title "Row" --data @props.json
```

### `notion page get <page-id>`

Get page metadata and properties.

| Flag | Default | Description |
|------|---------|-------------|
| `--output json\|properties` | `json` | Output format |

```bash
notion page get page123...
notion page get page123... --output properties
```

### `notion page get-property <page-id> <property-name>`

Get a single property value.

```bash
notion page get-property page123... Status
notion page get-property page123... "Due Date"
```

### `notion page set <page-id>`

Update page properties.

```bash
notion page set page123... Status="Done" Priority="Low"
notion page set page123... --data '{"Status": "Done"}'
```

### `notion page append <page-id>`

Append blocks (content) to a page.

```bash
notion page append page123... --data "# Heading\n\nSome content"
notion page append page123... --data @content.md
notion page append page123... --data - < content.md
```

Input can be Markdown (auto-converted to Notion blocks) or raw Notion block JSON.

### `notion page delete <page-id>`

Archive a page.

| Flag | Description |
|------|-------------|
| `--confirm` | Skip confirmation prompt |

```bash
notion page delete page123... --confirm
```

### `notion page restore <page-id>`

Restore an archived page.

```bash
notion page restore page123...
```

### `notion page move <page-id> <new-parent-id>`

Move a page to a different parent.

```bash
notion page move page123... newparent456...
```

---

## block

### `notion block list <block-id>`

List child blocks of a page or block.

| Flag | Default | Description |
|------|---------|-------------|
| `--output json\|ids` | `json` | Output format |

```bash
notion block list page123...
notion block list page123... --output ids
```

### `notion block get <block-id>`

Get a single block.

```bash
notion block get block123...
```

### `notion block append <block-id>`

Append a block.

| Flag | Description |
|------|-------------|
| `--type TYPE` | Block type (paragraph, heading_1, etc.) |
| `--text TEXT` | Block text content |

```bash
notion block append page123... --type paragraph --text "Hello world"
notion block append page123... --type heading_2 --text "Section Title"
```

### `notion block update <block-id>`

Update a block's content.

```bash
notion block update block123... --data '{"paragraph": {"rich_text": [{"text": {"content": "Updated"}}]}}'
notion block update block123... --data @block.json
```

### `notion block delete <block-id>`

Delete (archive) a block.

```bash
notion block delete block123...
```

---

## comment

### `notion comment add <page-id> <text>`

Add a comment to a page.

```bash
notion comment add page123... "This looks good!"
```

### `notion comment list <page-id>`

List comments on a page.

| Flag | Default | Description |
|------|---------|-------------|
| `--output json\|ids` | `json` | Output format |

```bash
notion comment list page123...
```

---

## search

### `notion search [QUERY]`

Search across all accessible pages and databases.

| Flag | Default | Description |
|------|---------|-------------|
| `--type page\|database` | — | Filter by type |
| `--sort last_edited\|relevance` | `relevance` | Sort order |
| `--limit N` | 10 | Max results |
| `--page-all` | false | Fetch all pages |
| `--output json\|ids` | `json` | Output format |

```bash
notion search "my query"
notion search "meeting notes" --type page --sort last_edited --output ids
notion search --type database --output json
```

---

## user

### `notion user list`

List all workspace members.

| Flag | Default | Description |
|------|---------|-------------|
| `--output json\|ids` | `json` | Output format |

```bash
notion user list
notion user list --output ids
```

### `notion user get <user-id>`

Get a specific user.

```bash
notion user get user123...
```

### `notion user me`

Get the current integration's bot user.

```bash
notion user me
```
