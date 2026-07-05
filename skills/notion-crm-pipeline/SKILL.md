---
name: notion-crm-pipeline
description: Run a lightweight sales CRM in Notion with the notion CLI — leads database with pipeline stages, dedup by email, stale-deal and next-action queries, activity logged as comments, pipeline value rollups. Use when tracking leads, deals, follow-ups, or client pipeline in Notion.
license: MIT
compatibility: Requires the notion CLI (npm i -g notion-agent-cli), a Notion integration token (NOTION_API_KEY), and jq for the rollup examples.
metadata:
  author: henryreith
  repository: https://github.com/henryreith/notion-cli
---

# Recipe: CRM & Sales Pipeline in Notion

A leads database, stage-driven queries, and an upsert-by-email pattern so the
same contact never gets duplicated. Property payload reference:
[notion-schema-design](../notion-schema-design/SKILL.md).

## Setup (once)

```bash
CRM=$(notion db create <parent-page-id> "Leads" --output id)
notion db update-schema "$CRM" --data '{
  "Stage": {"select": {"options": [
    {"name": "New", "color": "gray"},
    {"name": "Contacted", "color": "blue"},
    {"name": "Qualified", "color": "yellow"},
    {"name": "Proposal", "color": "orange"},
    {"name": "Won", "color": "green"},
    {"name": "Lost", "color": "red"}
  ]}},
  "Email": {"email": {}},
  "Company": {"rich_text": {}},
  "Value": {"number": {"format": "dollar"}},
  "Next Action": {"date": {}},
  "Source": {"select": {"options": []}}
}'
```

## Add / update a lead (dedup by email)

Always upsert on Email — new contact creates a row, known contact updates it:

```bash
notion db upsert "$CRM" --match "Email:jane@acme.com" \
  "Name=Jane Smith" "Email=jane@acme.com" "Company=Acme Co" \
  "Stage=Contacted" "Value=15000" "Next Action=$(date +%F)" \
  "Source=Referral" --add-options
```

Exit 6 means two rows share that email — deduplicate before continuing.

## Pipeline queries

```bash
TODAY=$(date +%F)

# Board view of a stage
notion db query "$CRM" --filter "Stage:=:Proposal" --output table

# Overdue follow-ups (next action in the past, deal still open)
notion db query "$CRM" \
  --filter "Next Action:<:$TODAY" \
  --filter "Stage:!=:Won" --filter "Stage:!=:Lost" \
  --output table

# Deals with no next action scheduled (about to go stale)
notion db query "$CRM" --filter "Next Action:is_empty:true" \
  --filter "Stage:!=:Won" --filter "Stage:!=:Lost" --output table
```

## Log activity on a deal

Comments make a timestamped activity trail; page content holds longer notes:

```bash
LEAD_ID=$(notion db query "$CRM" --filter "Email:=:jane@acme.com" --output ids | head -1)

notion comment add "$LEAD_ID" "Called — wants revised proposal by Friday. Bumping to Proposal."
notion db update-row "$LEAD_ID" "Stage=Proposal" "Next Action=$(date +%F)"

# Longer call notes as page content
notion page append "$LEAD_ID" --data "## Call $(date +%F)

Discussed scope. Decision maker is CFO. Budget confirmed at 15k."
```

## Pipeline value rollup

Value totals per stage — jq paths per property type are in
[notion-reporting's extract-values reference](../notion-reporting/references/extract-values.md):

```bash
notion db query "$CRM" --page-all --output json \
  | jq -r 'map(select(.properties.Stage.select.name as $s | $s != "Won" and $s != "Lost"))
           | group_by(.properties.Stage.select.name)
           | map("| \(.[0].properties.Stage.select.name) | \(length) | $\(map(.properties.Value.number // 0) | add) |")
           | ["| Stage | Deals | Value |", "|---|---|---|"] + . | join("\n")'
```

## Weekly pipeline review

Combine with [notion-reporting](../notion-reporting/SKILL.md): run the rollup
plus the overdue-follow-ups query on a schedule and publish to a review page
with `page create` + `page append`.
