---
name: notion-schema-design
description: Design and evolve Notion database schemas with the notion CLI — create databases, add or change properties, and get the exact JSON shape for every property type. Use when creating a new database or when db update-schema needs a property payload.
license: MIT
---

# notion-agent-cli — Schema Design

Creating and changing database schemas is the most error-prone part of the
Notion API: every property type has its own JSON shape. This skill gives the
workflow; the exact per-type payloads live in
[references/property-shapes.md](references/property-shapes.md) — read that file
whenever you write a `--data` schema payload.

## Workflow

```bash
# 1. Create the database (gets a Name title property automatically)
DB_ID=$(notion db create <parent-page-id> "My Database" --output id)

# 2. Add the rest of the schema in one patch
notion db update-schema "$DB_ID" --data @schema.json

# 3. Verify what Notion actually created
notion db schema "$DB_ID" --output properties
```

`db create --data` and `db update-schema --data` take the same
`{"Property Name": {<type payload>}}` object — see the reference for each
type's payload.

## Quick examples

```bash
# Add a select with options
notion db update-schema <db-id> --data '{
  "Stage": {"select": {"options": [
    {"name": "Idea", "color": "gray"},
    {"name": "Live", "color": "green"}
  ]}}
}'

# Add plain columns
notion db update-schema <db-id> --data '{
  "Notes": {"rich_text": {}},
  "Due": {"date": {}},
  "Done": {"checkbox": {}}
}'
```

## Rules that save you a retry

1. **Verify after writing** — `notion db schema <db-id> --output properties`.
   The API silently ignores malformed property payloads in some cases.
2. **Options need a schema entry OR `--add-options`** — when inserting rows
   with new select values, prefer `--add-options` on `db add`/`db batch-add`
   over hand-patching the schema.
3. **Relations are v5-style** — they point at a `data_source_id`, not a
   database ID in the old sense (see the reference).
4. **Status properties**: you can create the property, but its options and
   groups can only be configured in the Notion UI — plan select instead if
   you need scripted options.
5. **Renaming**: pass `{"Old Name": {"name": "New Name"}}` to update-schema.
   Removing: `{"Prop": null}`.

## Changing an existing select's options

Use `db add-option` (idempotent, cache-aware) instead of update-schema:

```bash
notion db add-option <db-id> Stage --option "Paused" --color yellow
```
