---
name: notion-page
description: Page commands for notion-agent-cli — create, get, set properties, append content, delete
type: service
---

# notion-agent-cli — Page Commands

## page create

Create a new page under a parent (page or database):

```bash
# Under a page
notion page create <parent-page-id> --title "My New Page"
notion page create <parent-page-id> --title "My Page" --output id

# Under a database (creates a database row)
notion page create <db-id> --title "My Row" --data '{"Status": "Active"}'

# With full property data
notion page create <parent-id> --title "Meeting Notes" \
  --data '{"Date": "2024-01-15", "Attendees": "Alice,Bob"}'
```

## page get

```bash
notion page get <page-id>                    # full JSON
notion page get <page-id> --output properties  # key=value pairs
```

## page get-property

Get a single property value (useful for checking before updating):

```bash
notion page get-property <page-id> Status
notion page get-property <page-id> "Due Date"
```

## page set

Update one or more properties on a page:

```bash
notion page set <page-id> "Status=Done"
notion page set <page-id> "Status=Done" "Priority=Low"
notion page set <page-id> --data '{"Status": "Done", "Priority": "Low"}'
notion page set <page-id> --data @updates.json
```

## page append

Append content to a page. Accepts Markdown or raw Notion block JSON:

```bash
# Inline Markdown
notion page append <page-id> --data "## New Section\n\nSome content here."

# Markdown file
notion page append <page-id> --data @notes.md

# Notion block JSON
notion page append <page-id> --data @blocks.json

# Stdin
cat report.md | notion page append <page-id> --data -
```

Supported Markdown elements: headings (h1–h3), paragraphs, bullet lists, numbered lists,
to-do items (`- [ ]`/`- [x]`), code blocks (fenced), bold, italic, inline code.

## page delete

Moves to trash (recoverable with `page restore`):

```bash
notion page delete <page-id> --confirm     # interactive confirmation
notion page delete <page-id> --mode ci     # agent/script (no prompt)

# Bulk delete via query pipeline
notion db query <db-id> --filter "Status:=:Archived" --output ids \
  | xargs -I{} notion page delete {} --mode ci
```

## page restore

Restore a trashed page:

```bash
notion page restore <page-id>
```

## Common Patterns

### Read-modify-write

```python
import subprocess, json

# Get current state
result = subprocess.run(
    ["notion", "page", "get", page_id, "--output", "json"],
    capture_output=True, text=True
)
page = json.loads(result.stdout)
current_status = page["properties"]["Status"]["select"]["name"]

# Conditionally update
if current_status != "Done":
    subprocess.run(
        ["notion", "page", "set", page_id, "Status=Done"],
        check=True
    )
```

### Create page with rich content

```bash
# Create the page
page_id=$(notion page create <parent-id> --title "Sprint Notes" --output id)

# Append content
notion page append "$page_id" --data @sprint-notes.md
```

### Bulk property update

```bash
# Update all "In Progress" items to "Done"
notion db query <db-id> --filter "Status:=:In Progress" --output ids \
  | xargs -I{} notion page set {} "Status=Done"
```
