---
name: notion-backup-sync
description: Round-trip content between local files and Notion with the notion CLI — publish markdown docs to pages, back up databases and pages to disk, restore from backup. Use when syncing a docs folder, exporting Notion data, or restoring content.
license: MIT
---

# Recipe: Backup & Sync — Markdown ⇄ Notion

Three flows built on the CLI's full-page markdown commands
(`page get-markdown` / `page set-markdown`) and JSON queries.

## Flow 1 — Publish local markdown to Notion (idempotent)

Track published files in a small "Docs" database so re-publishing updates
instead of duplicating. One row per source file, matched by path.

```bash
DOCS_DB=<docs-db-id>          # needs: Name (title), Source Path (rich_text)
PARENT=<parent-page-id>

publish_doc() {
  local file="$1"
  local title
  title=$(head -1 "$file" | sed 's/^# //')

  # Find the existing page for this file, if any
  local page_id
  page_id=$(notion db query "$DOCS_DB" \
    --filter "Source Path:=:$file" --output ids | head -1)

  if [ -z "$page_id" ]; then
    # First publish: create the row, then fill content
    page_id=$(notion db add "$DOCS_DB" \
      "Name=$title" "Source Path=$file" --output id)
  fi

  # Replace page content with the current markdown
  notion page set-markdown "$page_id" --data @"$file"
  echo "published: $file -> $page_id"
}

for f in docs/*.md; do publish_doc "$f"; done
```

Alternative without a tracking database — `db upsert` keyed on the title:

```bash
notion db upsert "$DOCS_DB" --match "Name:Getting Started" "Source Path=docs/getting-started.md"
```

## Flow 2 — Back up Notion to disk

### Databases → JSON

```bash
mkdir -p backup/dbs
for db_id in $(notion db list --page-all --output ids); do
  notion db query "$db_id" --page-all --output json > "backup/dbs/$db_id.json"
done
```

### Pages → markdown

```bash
mkdir -p backup/pages
for page_id in $(notion page list <root-page-id> --output ids); do
  notion page get-markdown "$page_id" > "backup/pages/$page_id.md"
done
```

Schema snapshots too, so a restore can rebuild structure:

```bash
notion db schema <db-id> --output json > "backup/schema-<db-id>.json"
```

## Flow 3 — Restore

Rebuild rows from a backup with `batch-add`. Backups store full API objects,
so first flatten them to `{Property: value}` rows (properties → plain values),
then:

```bash
# Always dry-run first (validates, exits 7, writes nothing)
notion db batch-add <db-id> --data @restore-rows.json --dry-run

# Real run — recreate missing select options automatically
notion db batch-add <db-id> --data @restore-rows.json --add-options --continue-on-error
```

Restore page content from the markdown backups:

```bash
notion page create <parent-id> --title "Restored Doc" --output id
notion page set-markdown <new-page-id> --data @backup/pages/<page-id>.md
```

## Scheduling

Run the backup flow from cron/CI with env auth — no prompts, no config file:

```bash
export NOTION_API_KEY=ntn_xxx
export NOTION_MODE=ci
```

Note the markdown round-trip is faithful for headings, paragraphs, lists,
quotes, code blocks, and dividers; exotic blocks (embeds, synced blocks,
databases-in-page) don't survive markdown export — keep the JSON backups for
those.
