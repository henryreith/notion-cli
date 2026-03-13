---
name: notion-task-tracker
description: Recipe — task tracking workflow with notion-agent-cli
type: recipe
---

# Recipe: Task Tracker in Notion

Build and operate a task tracking database using `notion-agent-cli`.

## Step 1 — Create the task database

```bash
DB_ID=$(notion db create <parent-page-id> "Task Tracker" --output id)
echo "DB_ID=$DB_ID"
```

## Step 2 — Define schema

```bash
notion db update-schema "$DB_ID" --data @task-schema.json
```

`task-schema.json`:
```json
{
  "Status": {
    "type": "select",
    "select": {
      "options": [
        {"name": "Backlog", "color": "gray"},
        {"name": "Todo", "color": "blue"},
        {"name": "In Progress", "color": "yellow"},
        {"name": "Review", "color": "orange"},
        {"name": "Done", "color": "green"},
        {"name": "Blocked", "color": "red"}
      ]
    }
  },
  "Priority": {
    "type": "select",
    "select": {
      "options": [
        {"name": "Critical", "color": "red"},
        {"name": "High", "color": "orange"},
        {"name": "Medium", "color": "yellow"},
        {"name": "Low", "color": "gray"}
      ]
    }
  },
  "Assignee": {"type": "people", "people": {}},
  "Due Date": {"type": "date", "date": {}},
  "Estimate": {"type": "number", "number": {"format": "number"}},
  "Tags": {"type": "multi_select", "multi_select": {"options": []}}
}
```

## Step 3 — Add tasks

```bash
# Single task
notion db add "$DB_ID" \
  "Name=Implement login page" \
  "Status=Todo" \
  "Priority=High" \
  "Due Date=2024-03-15"

# From JSON
notion db add "$DB_ID" --data @task.json --output id

# Batch import from backlog
notion db batch-add "$DB_ID" --data @backlog.json
```

`backlog.json`:
```json
[
  {"Name": "Fix auth bug", "Status": "Todo", "Priority": "Critical", "Tags": "bug,auth"},
  {"Name": "Write API docs", "Status": "Backlog", "Priority": "Medium", "Tags": "docs"},
  {"Name": "Add dark mode", "Status": "Backlog", "Priority": "Low", "Tags": "ui"}
]
```

## Step 4 — Query active work

```bash
# Active tasks (any in-progress status)
notion db query "$DB_ID" --filter "Status:=:In Progress" --output table

# My tasks (using user ID)
MY_ID=$(notion user me --output json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
notion db query "$DB_ID" --filter "Status:!=:Done" --output json | \
  python3 -c "
import sys, json
tasks = json.load(sys.stdin)
my_tasks = [t for t in tasks if any(
    u['id'] == '$MY_ID'
    for u in t['properties'].get('Assignee', {}).get('people', [])
)]
for t in my_tasks:
    print(t['properties']['Name']['title'][0]['plain_text'])
"

# Overdue tasks
TODAY=$(date +%Y-%m-%d)
notion db query "$DB_ID" \
  --filter "Due Date:<:$TODAY" \
  --filter "Status:!=:Done" \
  --output table

# Blocked tasks
notion db query "$DB_ID" --filter "Status:=:Blocked" --output table

# High priority todo
notion db query "$DB_ID" \
  --filter "Priority:=:Critical" \
  --filter "Status:!=:Done" \
  --output table
```

## Step 5 — Update task status (upsert)

```bash
# Move a task to In Progress by name
notion db upsert "$DB_ID" --match "Name:Fix auth bug" "Status=In Progress"

# Update by page ID (faster — no search)
notion db update-row <page-id> "Status=Done"

# Bulk close all Review tasks
notion db query "$DB_ID" --filter "Status:=:Review" --output ids \
  | xargs -I{} notion db update-row {} "Status=Done"
```

## Step 6 — Add notes to a task

```bash
# Get page ID for a task
TASK_ID=$(notion db query "$DB_ID" \
  --filter "Name:=:Fix auth bug" \
  --output ids | head -1)

# Append progress notes
notion page append "$TASK_ID" --data "## Update 2024-03-15\n\nRoot cause identified: JWT expiry not handled. Fix in PR #42."

# Add comment
notion comment add "$TASK_ID" "Blocked on code review from @alice"
```

## Automation: daily standup report

```python
#!/usr/bin/env python3
"""Print yesterday's completed tasks and today's active tasks."""
import subprocess, json
from datetime import date, timedelta

DB_ID = "your-db-id"
yesterday = (date.today() - timedelta(days=1)).isoformat()

def query(filters: list[str]) -> list:
    args = ["notion", "db", "query", DB_ID, "--output", "json"]
    for f in filters:
        args += ["--filter", f]
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)

def task_name(task: dict) -> str:
    return task["properties"]["Name"]["title"][0]["plain_text"]

done_today = query([f"Status:=:Done", f"Last Edited:>=:{yesterday}"])
in_progress = query(["Status:=:In Progress"])
blocked = query(["Status:=:Blocked"])

print("## Yesterday")
for t in done_today:
    print(f"  ✓ {task_name(t)}")

print("\n## Today")
for t in in_progress:
    print(f"  → {task_name(t)}")

print("\n## Blocked")
for t in blocked:
    print(f"  ✗ {task_name(t)}")
```
