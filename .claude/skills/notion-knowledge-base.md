---
name: notion-knowledge-base
description: Recipe — build and maintain a Notion knowledge base with notion-agent-cli
type: recipe
---

# Recipe: Build & Maintain a Knowledge Base in Notion

This recipe walks through creating a structured knowledge base database, populating it,
and keeping it up to date using `notion-agent-cli`.

## Step 1 — Create the database

```bash
# Create the database under a parent page
DB_ID=$(notion db create <parent-page-id> "Knowledge Base" --output id)
echo "Database ID: $DB_ID"
```

## Step 2 — Define the schema

```bash
notion db update-schema "$DB_ID" --data @kb-schema.json
```

Example `kb-schema.json`:
```json
{
  "Category": {
    "type": "select",
    "select": {
      "options": [
        {"name": "Architecture", "color": "blue"},
        {"name": "Process", "color": "green"},
        {"name": "Reference", "color": "yellow"},
        {"name": "Runbook", "color": "red"}
      ]
    }
  },
  "Tags": {"type": "multi_select", "multi_select": {"options": []}},
  "Status": {
    "type": "select",
    "select": {
      "options": [
        {"name": "Draft", "color": "gray"},
        {"name": "Review", "color": "orange"},
        {"name": "Published", "color": "green"},
        {"name": "Outdated", "color": "red"}
      ]
    }
  },
  "Owner": {"type": "people", "people": {}},
  "Last Reviewed": {"type": "date", "date": {}},
  "Source URL": {"type": "url", "url": {}}
}
```

## Step 3 — Batch import entries

```bash
# Validate first
notion db batch-add "$DB_ID" --data @kb-entries.json --dry-run

# Import
notion db batch-add "$DB_ID" --data @kb-entries.json --add-options
```

Example `kb-entries.json`:
```json
[
  {
    "Name": "System Architecture Overview",
    "Category": "Architecture",
    "Tags": "design,backend",
    "Status": "Published"
  },
  {
    "Name": "Deploy Runbook",
    "Category": "Runbook",
    "Tags": "ops,deploy",
    "Status": "Review"
  }
]
```

## Step 4 — Add rich content to an entry

```bash
# Get the page ID for a specific entry
PAGE_ID=$(notion db query "$DB_ID" --filter "Name:=:Deploy Runbook" --output ids | head -1)

# Append markdown content
notion page append "$PAGE_ID" --data @deploy-runbook.md
```

## Step 5 — Query entries

```bash
# All published entries
notion db query "$DB_ID" --filter "Status:=:Published" --output table

# Find by category
notion db query "$DB_ID" --filter "Category:=:Runbook" --output json

# Find outdated entries
notion db query "$DB_ID" --filter "Status:=:Outdated" --output ids

# Search by keyword
notion search "deploy" --type page --output json | jq '.[].id'
```

## Step 6 — Update entries (upsert pattern)

```bash
# Update status — creates if not found, updates if found
notion db upsert "$DB_ID" --match "Name:Deploy Runbook" \
  "Status=Published" "Last Reviewed=2024-03-15"
```

## Step 7 — Mark outdated entries

```bash
# Find entries not reviewed in 6+ months and mark outdated
# (Use a script to compute the date threshold)
THRESHOLD="2023-09-15"
notion db query "$DB_ID" \
  --filter "Last Reviewed:<:$THRESHOLD" \
  --filter "Status:!=:Outdated" \
  --output ids \
  | xargs -I{} notion page set {} "Status=Outdated"
```

## Automation: periodic freshness check

```python
#!/usr/bin/env python3
"""Weekly script: flag KB entries not reviewed in 90 days."""
import subprocess, json
from datetime import date, timedelta

DB_ID = "your-db-id"
THRESHOLD = (date.today() - timedelta(days=90)).isoformat()

# Query stale entries
result = subprocess.run(
    ["notion", "db", "query", DB_ID,
     "--filter", f"Last Reviewed:<:{THRESHOLD}",
     "--filter", "Status:=:Published",
     "--output", "ids"],
    capture_output=True, text=True, check=True
)
stale_ids = result.stdout.strip().split("\n") if result.stdout.strip() else []

for page_id in stale_ids:
    subprocess.run(
        ["notion", "page", "set", page_id, "Status=Outdated"],
        check=True
    )
    subprocess.run(
        ["notion", "comment", "add", page_id,
         "Automated: marked Outdated — not reviewed in 90+ days"],
        check=True
    )

print(f"Marked {len(stale_ids)} entries as Outdated.")
```
