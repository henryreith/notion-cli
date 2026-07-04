# Property schema payloads — the exact JSON for every type

Shapes verified against `@notionhq/client` v5 request types. All payloads go
inside `{"Property Name": <payload>}` for `notion db create --data` /
`notion db update-schema --data`. A `"type"` key is accepted but never
required — omit it.

## Contents

- [Basic types (empty config)](#basic-types-empty-config)
- [title](#title)
- [number](#number)
- [select / multi_select](#select--multi_select)
- [status](#status)
- [relation](#relation)
- [rollup](#rollup)
- [formula](#formula)
- [unique_id](#unique_id)
- [Renaming and removing properties](#renaming-and-removing-properties)
- [What the API cannot do](#what-the-api-cannot-do)

## Basic types (empty config)

These take an empty object — nothing to configure:

```json
{
  "Notes":     {"rich_text": {}},
  "Due":       {"date": {}},
  "Done":      {"checkbox": {}},
  "Link":      {"url": {}},
  "Email":     {"email": {}},
  "Phone":     {"phone_number": {}},
  "Owner":     {"people": {}},
  "Files":     {"files": {}},
  "Created":   {"created_time": {}},
  "Creator":   {"created_by": {}},
  "Edited":    {"last_edited_time": {}},
  "Editor":    {"last_edited_by": {}}
}
```

## title

Every database has exactly one title property (created as `Name` by
`notion db create`). To rename it, update by its current name:

```json
{"Name": {"name": "Task", "title": {}}}
```

## number

`format` is optional (plain number when omitted). Common formats: `number`,
`number_with_commas`, `percent`, `dollar`, `euro`, `pound`, `yen`, plus most
currency codes.

```json
{"Estimate": {"number": {}}}
{"Cost": {"number": {"format": "dollar"}}}
{"Progress": {"number": {"format": "percent"}}}
```

## select / multi_select

Options are optional at creation; each option takes `name` + optional `color`
and `description`. Colors: `default`, `gray`, `brown`, `orange`, `yellow`,
`green`, `blue`, `purple`, `pink`, `red`.

```json
{
  "Stage": {"select": {"options": [
    {"name": "Idea", "color": "gray"},
    {"name": "Building", "color": "yellow"},
    {"name": "Live", "color": "green", "description": "Shipped to prod"}
  ]}},
  "Tags": {"multi_select": {"options": []}}
}
```

To add options to an existing property, prefer `notion db add-option` over
re-sending the whole list.

## status

The property can be created, but **options and groups cannot be set via the
API** — only in the Notion UI. Use `select` if you need scripted options.

```json
{"Status": {"status": {}}}
```

## relation

v5: relations target a **data source ID** (what `notion db schema` operates
on). Choose `single_property` (one-way) or `dual_property` (two-way, creates
a backlink property in the target).

```json
{"Project": {"relation": {
  "data_source_id": "<target-data-source-id>",
  "single_property": {}
}}}
```

```json
{"Tasks": {"relation": {
  "data_source_id": "<target-data-source-id>",
  "dual_property": {}
}}}
```

## rollup

Needs an existing relation property, the property to aggregate in the target,
and a function. Functions: `count`, `count_values`, `unique`, `show_unique`,
`show_original`, `empty`, `not_empty`, `percent_empty`, `percent_not_empty`,
`sum`, `average`, `median`, `min`, `max`, `range`, `earliest_date`,
`latest_date`, `date_range`, `checked`, `unchecked`, `percent_checked`,
`percent_unchecked`, `count_per_group`, `percent_per_group`.

```json
{"Total Cost": {"rollup": {
  "relation_property_name": "Line Items",
  "rollup_property_name": "Cost",
  "function": "sum"
}}}
```

## formula

Notion formula syntax, referencing properties with `prop("Name")`:

```json
{"Overdue": {"formula": {
  "expression": "and(not(prop(\"Done\")), prop(\"Due\") < now())"
}}}
```

## unique_id

Auto-incrementing ID, optional prefix (`TASK-1`, `TASK-2`, …):

```json
{"ID": {"unique_id": {"prefix": "TASK"}}}
```

## Renaming and removing properties

```json
{"Old Name": {"name": "New Name"}}
{"Unwanted Property": null}
```

Both via `notion db update-schema <db-id> --data '...'`.

## What the API cannot do

- Configure **status** options/groups (UI only)
- Create **button**, **location**, **place**, or **verification** properties
  meaningfully (accepted in types, UI-managed in practice)
- Change a property's type in place when data would be lost — Notion may
  reject or coerce; verify with `notion db schema` after any type change
