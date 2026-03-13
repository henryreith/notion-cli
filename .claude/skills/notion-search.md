---
name: notion-search
description: Search, block, comment, and user commands for notion-agent-cli
type: service
---

# notion-agent-cli — Search, Block, Comment & User Commands

## search

Full-text search across your workspace:

```bash
notion search "meeting notes"
notion search "sprint" --type page
notion search "tasks" --type database
notion search "q1 review" --sort last_edited --limit 5
notion search "project" --page-all --output ids
notion search --output json | jq '.[].id'
```

Options:
- `--type page|database` — filter by object type
- `--sort last_edited|relevance` — sort order (default: relevance)
- `--limit N` — max results
- `--page-all` — paginate through all results
- `--output json|ids` — output format

## block list / get

Blocks are the content units within a page:

```bash
# List all blocks in a page
notion block list <page-id>
notion block list <page-id> --output ids

# Get a specific block
notion block get <block-id>
```

## block append

Add a new block to a page:

```bash
notion block append <page-id> --type paragraph --text "New paragraph."
notion block append <page-id> --type heading_2 --text "Section Title"
notion block append <page-id> --type bulleted_list_item --text "Bullet point"
notion block append <page-id> --type to_do --text "Task to complete"
notion block append <page-id> --type code --text "print('hello')"
```

Common block types: `paragraph`, `heading_1`, `heading_2`, `heading_3`,
`bulleted_list_item`, `numbered_list_item`, `to_do`, `toggle`, `quote`,
`callout`, `code`, `divider`

## block update

Update an existing block's content:

```bash
notion block update <block-id> --data '{"paragraph": {"rich_text": [{"type": "text", "text": {"content": "Updated text"}}]}}'
notion block update <block-id> --data @block-update.json
```

## block delete

```bash
notion block delete <block-id>
```

## comment add / list

```bash
# Add a comment to a page
notion comment add <page-id> "Great work on this!"
notion comment add <page-id> "TODO: review before Friday"

# List comments on a page
notion comment list <page-id>
notion comment list <page-id> --output json
notion comment list <page-id> --output ids
```

## user list / get / me

```bash
notion user list
notion user list --output ids
notion user get <user-id>
notion user me   # get your own user info
```

User IDs are used when setting `people` type properties:
```bash
# Get your user ID
my_id=$(notion user me --output json | jq -r '.id')

# Assign yourself to a task
notion page set <page-id> "Assignee=$my_id"
```

## Common Patterns

### Find a database by name

```bash
notion search "My Database" --type database --output json \
  | jq -r '.[0].id'
```

### Search and update matching pages

```bash
notion search "draft" --type page --output ids \
  | xargs -I{} notion page set {} "Status=Review"
```

### Add progress comment

```python
import subprocess

def add_progress_comment(page_id: str, message: str):
    subprocess.run(
        ["notion", "comment", "add", page_id, message],
        check=True
    )

add_progress_comment(page_id, "Automated: processing complete")
```
