---
name: notion-reporting
description: Generate reports, digests, and metrics from Notion databases with the notion CLI — status rollups, weekly digests, standup summaries, number aggregation — and write them back as Notion pages or comments. Use when summarising database contents, building recurring reports, or answering "how many / how much / what changed" questions about Notion data.
license: MIT
compatibility: Requires the notion CLI (npm i -g notion-agent-cli), a Notion integration token (NOTION_API_KEY), and jq for the aggregation examples.
metadata:
  author: henryreith
  repository: https://github.com/henryreith/notion-cli
---

# Recipe: Reporting & Digests from Notion Data

Query with `--page-all --output json`, aggregate with jq (or any language),
write results back as a page or comment. Extracting values from Notion's
property JSON is the fiddly part — the exact jq path for every property type
is in [references/extract-values.md](references/extract-values.md); read it
before writing new jq.

## Status rollup (counts per select value)

```bash
DB_ID=<db-id>

notion db query "$DB_ID" --page-all --output json \
  | jq -r 'group_by(.properties.Status.select.name)
           | map({status: .[0].properties.Status.select.name, count: length})
           | .[] | "| \(.status // "None") | \(.count) |"'
```

Render as a markdown report page:

```bash
REPORT=$(notion db query "$DB_ID" --page-all --output json \
  | jq -r 'group_by(.properties.Status.select.name)
           | "## Status Rollup\n\n| Status | Count |\n|---|---|\n"
             + (map("| \(.[0].properties.Status.select.name // "None") | \(length) |") | join("\n"))')

PAGE_ID=$(notion page create <reports-parent-id> --title "Report $(date +%F)" --output id)
echo "$REPORT" | notion page append "$PAGE_ID" --data -
```

## Weekly digest

Date-windowed queries against a date property, one section per question:

```bash
WEEK_AGO=$(date -v-7d +%F 2>/dev/null || date -d '7 days ago' +%F)   # macOS || GNU

# What was completed this week
notion db query "$DB_ID" \
  --filter "Status:=:Done" --filter "Done Date:>=:$WEEK_AGO" \
  --page-all --output json \
  | jq -r '.[] | "- " + (.properties.Name.title[0].plain_text // "Untitled")'

# What is currently blocked
notion db query "$DB_ID" --filter "Status:=:Blocked" --output json \
  | jq -r '.[] | "- " + (.properties.Name.title[0].plain_text // "Untitled")'
```

Assemble the sections into one markdown string and publish it as a page
(`page create` + `page append`) — same pattern as the rollup above.

## Standup summary as a comment

Post to a team page instead of creating report pages:

```bash
DONE=$(notion db query "$DB_ID" --filter "Status:=:Done" --filter "Done Date:>=:$WEEK_AGO" \
  --output json | jq -r '[.[] | .properties.Name.title[0].plain_text] | join(", ")')
ACTIVE=$(notion db query "$DB_ID" --filter "Status:=:In Progress" \
  --output json | jq -r '[.[] | .properties.Name.title[0].plain_text] | join(", ")')

notion comment add <team-page-id> "Standup — done: ${DONE:-none}; active: ${ACTIVE:-none}"
```

## Number metrics (sum / average)

```bash
# Total pipeline value of open deals
notion db query "$DB_ID" --filter "Stage:!=:Closed" --page-all --output json \
  | jq '[.[] | .properties.Value.number // 0] | {total: add, average: (add / length), count: length}'
```

## Scheduling

Recurring reports run from cron/CI with env auth — no prompts:

```bash
export NOTION_API_KEY=ntn_xxx
export NOTION_MODE=ci
```

Rate limits: for report loops touching many pages, space write calls ~350ms
apart (the Notion API allows ~3 req/sec; queries with `--page-all` handle
their own pagination).
