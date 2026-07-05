---
name: notion-capture
description: Quick-capture anything into Notion with the notion CLI — thoughts and tasks into an inbox database, links with dedup, timestamped daily journal entries. Use when the user says "capture this", "remember this link", "add to my inbox", "log this to my journal", or any fast fire-and-forget note into Notion.
license: MIT
compatibility: Requires the notion CLI (npm i -g notion-agent-cli) and a Notion integration token (NOTION_API_KEY).
metadata:
  author: henryreith
  repository: https://github.com/henryreith/notion-cli
---

# Recipe: Quick Capture — Inbox, Links & Daily Journal

Fast, fire-and-forget writes for personal and home agents. One-time setup of
an Inbox database, then every capture is a single command.

## Setup (once)

```bash
INBOX=$(notion db create <parent-page-id> "Inbox" --output id)
notion db update-schema "$INBOX" --data '{
  "Type": {"select": {"options": [
    {"name": "Thought", "color": "gray"},
    {"name": "Task", "color": "blue"},
    {"name": "Link", "color": "purple"},
    {"name": "Idea", "color": "yellow"}
  ]}},
  "Source": {"rich_text": {}},
  "URL": {"url": {}},
  "Captured": {"date": {}}
}'
```

## Capture a thought / task / idea

One line — new `Type` values are created on the fly with `--add-options`:

```bash
notion db add "$INBOX" \
  "Name=Call the accountant about Q3 invoices" \
  "Type=Task" "Source=voice note" "Captured=$(date +%F)" \
  --add-options --output id
```

## Capture a link (dedup by URL)

`upsert` keyed on the URL, so re-capturing the same link updates the existing
row instead of duplicating it:

```bash
notion db upsert "$INBOX" --match "URL:https://example.com/article" \
  "Name=Great article on agent design" \
  "Type=Link" "URL=https://example.com/article" "Captured=$(date +%F)"
```

## Daily journal

A Journal database with one page per day, titled `YYYY-MM-DD`. Find-or-create
today's page, then append timestamped entries:

```bash
JOURNAL=<journal-db-id>
TODAY=$(date +%F)

# Find-or-create today's page (upsert with no other properties = get-or-create)
notion db upsert "$JOURNAL" --match "Name:$TODAY" "Name=$TODAY"
PAGE_ID=$(notion db query "$JOURNAL" --filter "Name:=:$TODAY" --output ids | head -1)

# Append a timestamped entry
notion page append "$PAGE_ID" --data "## $(date +%H:%M)

Shipped the reporting skill. Energy good. Tomorrow: CRM recipe."
```

## Triage the inbox later

```bash
# Everything captured, oldest thinking first
notion db query "$INBOX" --sort "Captured" --output table

# Just the unprocessed tasks
notion db query "$INBOX" --filter "Type:=:Task" --output table

# Promote a captured task into a real tracker, then archive the inbox row
notion db add <tasks-db-id> "Name=Call the accountant about Q3 invoices" "Status=Todo"
notion db query "$INBOX" --filter "Name:contains:accountant" --output ids \
  | xargs -I{} notion page delete {} --confirm
```

## Agent phrasing map

| User says | Do |
|-----------|----|
| "capture this / note this down" | `db add` to Inbox, `Type=Thought` |
| "remember this link" | `db upsert --match "URL:<url>"` |
| "add X to my todo / inbox" | `db add` with `Type=Task` |
| "journal: …" / "log my day" | daily journal append |
